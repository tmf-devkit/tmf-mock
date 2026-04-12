"""Tests for TMF638 Service Inventory endpoints."""
BASE = "/tmf-api/serviceInventoryManagement/v4"
RES_BASE = "/tmf-api/resourceInventoryManagement/v4"


def _create_resource(client, name="Port-01"):
    r = client.post(f"{RES_BASE}/resource", json={"name": name, "category": "Logical"})
    assert r.status_code == 201
    return r.json()


def _create_service(client, name="BB-Svc-01", resource_ids=None):
    payload = {"name": name, "serviceType": "Broadband", "state": "active"}
    if resource_ids:
        payload["supportingResource"] = [{"id": rid, "name": f"res-{rid[:6]}"} for rid in resource_ids]
    r = client.post(f"{BASE}/service", json=payload)
    assert r.status_code == 201
    return r.json()


def test_list_services_empty(client):
    r = client.get(f"{BASE}/service")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["X-Total-Count"] == "0"


def test_create_service_minimal(client):
    r = client.post(f"{BASE}/service", json={"name": "VoIP-001", "serviceType": "VoIP"})
    assert r.status_code == 201
    body = r.json()
    assert body["id"] and body["href"]
    assert body["name"] == "VoIP-001"
    assert body["@type"] == "Service"
    assert "Location" in r.headers


def test_get_service(client):
    svc = _create_service(client, "GetMe-Svc")
    r = client.get(f"{BASE}/service/{svc['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == svc["id"]


def test_get_service_not_found(client):
    assert client.get(f"{BASE}/service/does-not-exist").status_code == 404


def test_patch_service_state(client):
    svc = _create_service(client)
    r = client.patch(f"{BASE}/service/{svc['id']}", json={"state": "terminated"})
    assert r.status_code == 200
    assert r.json()["state"] == "terminated"


def test_delete_service(client):
    svc = _create_service(client)
    assert client.delete(f"{BASE}/service/{svc['id']}").status_code == 204
    assert client.get(f"{BASE}/service/{svc['id']}").status_code == 404


def test_create_service_with_valid_resource_ref(client):
    res = _create_resource(client, "DSL-Port-01")
    svc = _create_service(client, resource_ids=[res["id"]])
    refs = svc.get("supportingResource", [])
    assert any(r["id"] == res["id"] for r in refs)


def test_create_service_with_invalid_resource_ref(client):
    payload = {"name": "Bad-Svc", "serviceType": "Broadband",
               "supportingResource": [{"id": "ghost-resource-id", "name": "Ghost"}]}
    r = client.post(f"{BASE}/service", json=payload)
    assert r.status_code == 422
    assert "ghost-resource-id" in r.json()["detail"]


def test_delete_service_blocked_if_referenced_by_order(client):
    svc = _create_service(client, "ToDelete-Svc")
    order_payload = {"description": "Modify existing service",
                     "orderItem": [{"id": "1", "action": "modify",
                                    "service": {"id": svc["id"], "name": svc["name"]}}]}
    client.post("/tmf-api/serviceOrdering/v4/serviceOrder", json=order_payload)
    assert client.delete(f"{BASE}/service/{svc['id']}").status_code == 409


def test_filter_by_state(client):
    client.post(f"{BASE}/service", json={"name": "S1", "state": "active"})
    client.post(f"{BASE}/service", json={"name": "S2", "state": "inactive"})
    r = client.get(f"{BASE}/service?state=active")
    assert all(s["state"] == "active" for s in r.json())


def test_filter_by_service_type(client):
    client.post(f"{BASE}/service", json={"name": "BB-01", "serviceType": "Broadband"})
    client.post(f"{BASE}/service", json={"name": "VoIP-01", "serviceType": "VoIP"})
    r = client.get(f"{BASE}/service?serviceType=Broadband")
    assert all(s.get("serviceType") == "Broadband" for s in r.json())


def test_pagination(client):
    for i in range(6):
        client.post(f"{BASE}/service", json={"name": f"Svc-{i}"})
    r = client.get(f"{BASE}/service?offset=0&limit=3")
    assert len(r.json()) == 3
    assert r.headers["X-Total-Count"] == "6"


def test_seed_services_reference_real_resources(seeded_client):
    services = seeded_client.get(f"{BASE}/service").json()
    for svc in services:
        for ref in svc.get("supportingResource") or []:
            res_r = seeded_client.get(f"{RES_BASE}/resource/{ref['id']}")
            assert res_r.status_code == 200, f"Service {svc['id']} refs missing Resource {ref['id']}"
