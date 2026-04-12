"""Tests for TMF639 Resource Inventory endpoints."""
BASE = "/tmf-api/resourceInventoryManagement/v4"


def test_list_resources_empty(client):
    r = client.get(f"{BASE}/resource")
    assert r.status_code == 200
    assert r.json() == []
    assert r.headers["X-Total-Count"] == "0"


def test_create_resource(client):
    payload = {"name": "DSLAM-Test-01", "category": "Physical", "description": "Test DSLAM",
               "resourceStatus": "available",
               "resourceCharacteristic": [{"name": "vendor", "value": "Huawei", "valueType": "string"}]}
    r = client.post(f"{BASE}/resource", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] and body["href"]
    assert body["name"] == "DSLAM-Test-01"
    assert body["resourceStatus"] == "available"
    assert "Location" in r.headers


def test_get_resource(client):
    r = client.post(f"{BASE}/resource", json={"name": "Router-01", "category": "Physical"})
    rid = r.json()["id"]
    r2 = client.get(f"{BASE}/resource/{rid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == rid


def test_get_resource_not_found(client):
    assert client.get(f"{BASE}/resource/nonexistent-id").status_code == 404


def test_patch_resource(client):
    r = client.post(f"{BASE}/resource", json={"name": "Switch-01", "category": "Physical"})
    rid = r.json()["id"]
    r2 = client.patch(f"{BASE}/resource/{rid}", json={"resourceStatus": "reserved", "description": "Updated"})
    assert r2.status_code == 200
    assert r2.json()["resourceStatus"] == "reserved"
    assert r2.json()["description"] == "Updated"


def test_delete_resource(client):
    r = client.post(f"{BASE}/resource", json={"name": "OLT-01", "category": "Physical"})
    rid = r.json()["id"]
    assert client.delete(f"{BASE}/resource/{rid}").status_code == 204
    assert client.get(f"{BASE}/resource/{rid}").status_code == 404


def test_delete_resource_blocked_if_referenced_by_service(client):
    res = client.post(f"{BASE}/resource", json={"name": "Port-01", "category": "Logical"})
    rid = res.json()["id"]
    client.post("/tmf-api/serviceInventoryManagement/v4/service",
                json={"name": "BB-Svc-01", "serviceType": "Broadband",
                      "supportingResource": [{"id": rid, "name": "Port-01"}]})
    r = client.delete(f"{BASE}/resource/{rid}")
    assert r.status_code == 409
    assert "referenced" in r.json()["detail"].lower()


def test_filter_by_resource_status(client):
    client.post(f"{BASE}/resource", json={"name": "R1", "resourceStatus": "available"})
    client.post(f"{BASE}/resource", json={"name": "R2", "resourceStatus": "reserved"})
    r = client.get(f"{BASE}/resource?resourceStatus=available")
    assert all(res["resourceStatus"] == "available" for res in r.json())


def test_filter_by_category(client):
    client.post(f"{BASE}/resource", json={"name": "Phys-01", "category": "Physical"})
    client.post(f"{BASE}/resource", json={"name": "Log-01", "category": "Logical"})
    r = client.get(f"{BASE}/resource?category=Physical")
    assert all(res["category"] == "Physical" for res in r.json())


def test_pagination(client):
    for i in range(5):
        client.post(f"{BASE}/resource", json={"name": f"R{i}", "category": "Physical"})
    r = client.get(f"{BASE}/resource?offset=0&limit=2")
    assert len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "5"


def test_seed_data_loaded(seeded_client):
    resources = seeded_client.get(f"{BASE}/resource").json()
    assert len(resources) > 10
    categories = {r.get("category") for r in resources}
    assert "Physical" in categories
    assert "Logical" in categories
