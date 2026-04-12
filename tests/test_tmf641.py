"""Tests for TMF641 Service Ordering endpoints."""
from datetime import datetime, timedelta, timezone

BASE = "/tmf-api/serviceOrdering/v4"
SVC_BASE = "/tmf-api/serviceInventoryManagement/v4"


def _now_plus(days=3):
    return (datetime.now(tz=timezone.utc) + timedelta(days=days)).isoformat()


def _new_order(action="add", service_id=None, service_name="New-BB-Svc"):
    svc = {"name": service_name, "serviceType": "Broadband"}
    if service_id:
        svc["id"] = service_id
    return {"description": "Test order", "category": "Fixed", "priority": "2",
            "requestedCompletionDate": _now_plus(3),
            "orderItem": [{"id": "1", "action": action, "service": svc}]}


def _create_service(client, name="Base-Svc"):
    r = client.post(f"{SVC_BASE}/service", json={"name": name, "serviceType": "Broadband", "state": "active"})
    assert r.status_code == 201
    return r.json()


def _advance_to_completed(client, order_id):
    """Drive an order through the valid path to completed: acknowledged → inProgress → completed."""
    client.patch(f"{BASE}/serviceOrder/{order_id}", json={"state": "inProgress"})
    client.patch(f"{BASE}/serviceOrder/{order_id}", json={"state": "completed"})


def test_list_orders_empty(client):
    r = client.get(f"{BASE}/serviceOrder")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["X-Total-Count"] == "0"


def test_create_order_add_new_service(client):
    r = client.post(f"{BASE}/serviceOrder", json=_new_order(action="add"))
    assert r.status_code == 201
    body = r.json()
    assert body["id"] and body["href"]
    assert body["state"] == "acknowledged"
    assert body["orderDate"]
    assert "Location" in r.headers


def test_create_order_always_sets_acknowledged(client):
    payload = _new_order()
    payload["state"] = "completed"  # server must ignore and set acknowledged
    r = client.post(f"{BASE}/serviceOrder", json=payload)
    assert r.json()["state"] == "acknowledged"


def test_get_order(client):
    order = client.post(f"{BASE}/serviceOrder", json=_new_order()).json()
    r = client.get(f"{BASE}/serviceOrder/{order['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == order["id"]


def test_get_order_not_found(client):
    assert client.get(f"{BASE}/serviceOrder/ghost-id").status_code == 404


def test_patch_order_state(client):
    order = client.post(f"{BASE}/serviceOrder", json=_new_order()).json()
    r = client.patch(f"{BASE}/serviceOrder/{order['id']}", json={"state": "inProgress"})
    assert r.status_code == 200
    assert r.json()["state"] == "inProgress"


def test_delete_order(client):
    order = client.post(f"{BASE}/serviceOrder", json=_new_order()).json()
    assert client.delete(f"{BASE}/serviceOrder/{order['id']}").status_code == 204
    assert client.get(f"{BASE}/serviceOrder/{order['id']}").status_code == 404


def test_order_item_modify_requires_existing_service(client):
    r = client.post(f"{BASE}/serviceOrder", json=_new_order(action="modify", service_id="nonexistent-id"))
    assert r.status_code == 422
    assert "nonexistent-id" in r.json()["detail"]


def test_order_item_modify_with_real_service(client):
    svc = _create_service(client)
    r = client.post(f"{BASE}/serviceOrder", json=_new_order(action="modify", service_id=svc["id"]))
    assert r.status_code == 201


def test_order_item_delete_requires_existing_service(client):
    r = client.post(f"{BASE}/serviceOrder", json=_new_order(action="delete", service_id="ghost-svc"))
    assert r.status_code == 422


def test_multi_item_order(client):
    svc = _create_service(client)
    payload = {"description": "Bundle", "orderItem": [
        {"id": "1", "action": "add", "service": {"name": "New-BB", "serviceType": "Broadband"}},
        {"id": "2", "action": "modify", "service": {"id": svc["id"], "name": svc["name"]}},
    ]}
    r = client.post(f"{BASE}/serviceOrder", json=payload)
    assert r.status_code == 201
    assert len(r.json()["orderItem"]) == 2


def test_filter_by_state(client):
    """Filter works correctly — use valid state path: acknowledged → inProgress → completed."""
    o1 = client.post(f"{BASE}/serviceOrder", json=_new_order()).json()
    o2 = client.post(f"{BASE}/serviceOrder", json=_new_order()).json()

    _advance_to_completed(client, o1["id"])

    r = client.get(f"{BASE}/serviceOrder?state=completed")
    assert r.status_code == 200
    completed_ids = {o["id"] for o in r.json()}
    assert all(o["state"] == "completed" for o in r.json())
    assert o1["id"] in completed_ids
    assert o2["id"] not in completed_ids  # o2 still acknowledged


def test_pagination(client):
    for i in range(5):
        client.post(f"{BASE}/serviceOrder", json=_new_order(service_name=f"Svc-{i}"))
    r = client.get(f"{BASE}/serviceOrder?limit=2&offset=0")
    assert len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "5"


def test_x_total_count_header(client):
    for i in range(3):
        client.post(f"{BASE}/serviceOrder", json=_new_order())
    r = client.get(f"{BASE}/serviceOrder")
    assert r.headers["X-Total-Count"] == "3"


def test_seed_orders_loaded(seeded_client):
    orders = seeded_client.get(f"{BASE}/serviceOrder").json()
    assert len(orders) >= 3
    assert "completed" in {o["state"] for o in orders}


def test_seed_completed_orders_reference_real_services(seeded_client):
    orders = seeded_client.get(f"{BASE}/serviceOrder").json()
    for order in [o for o in orders if o.get("state") == "completed"]:
        for item in order.get("orderItem", []):
            svc_id = (item.get("service") or {}).get("id")
            if svc_id:
                assert seeded_client.get(f"{SVC_BASE}/service/{svc_id}").status_code == 200
