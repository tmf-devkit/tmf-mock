"""
Tests for lifecycle state machine enforcement.

Covers TMF638 (Service), TMF639 (Resource), TMF641 (ServiceOrder).
Each test verifies that:
  - valid transitions succeed (HTTP 200)
  - invalid / backward transitions are rejected (HTTP 422)
  - terminal states cannot be exited (HTTP 422)
"""
SVC_BASE = "/tmf-api/serviceInventoryManagement/v4"
RES_BASE = "/tmf-api/resourceInventoryManagement/v4"
ORD_BASE = "/tmf-api/serviceOrdering/v4"


# ── helpers ──────────────────────────────────────────────────────────────────

def _mk_resource(client, name="R-SM", status="available"):
    r = client.post(f"{RES_BASE}/resource", json={"name": name, "resourceStatus": status})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_service(client, name="S-SM", state="inactive"):
    r = client.post(f"{SVC_BASE}/service", json={"name": name, "state": state})
    assert r.status_code == 201, r.text
    return r.json()


def _mk_order(client, action="add", service_id=None):
    svc = {"name": "New-Svc", "serviceType": "Broadband"}
    if service_id:
        svc["id"] = service_id
    r = client.post(f"{ORD_BASE}/serviceOrder",
                    json={"orderItem": [{"id": "1", "action": action, "service": svc}]})
    assert r.status_code == 201, r.text
    return r.json()


def _patch_resource(client, rid, **fields):
    return client.patch(f"{RES_BASE}/resource/{rid}", json=fields)


def _patch_service(client, sid, **fields):
    return client.patch(f"{SVC_BASE}/service/{sid}", json=fields)


def _patch_order(client, oid, **fields):
    return client.patch(f"{ORD_BASE}/serviceOrder/{oid}", json=fields)


# ── TMF639 Resource: resourceStatus transitions ───────────────────────────────

class TestResourceStatusTransitions:

    def test_available_to_reserved(self, client):
        r = _mk_resource(client, status="available")
        assert _patch_resource(client, r["id"], resourceStatus="reserved").status_code == 200

    def test_available_to_standby(self, client):
        r = _mk_resource(client, status="available")
        assert _patch_resource(client, r["id"], resourceStatus="standby").status_code == 200

    def test_available_to_suspended(self, client):
        r = _mk_resource(client, status="available")
        assert _patch_resource(client, r["id"], resourceStatus="suspended").status_code == 200

    def test_reserved_back_to_available(self, client):
        r = _mk_resource(client, status="available")
        _patch_resource(client, r["id"], resourceStatus="reserved")
        assert _patch_resource(client, r["id"], resourceStatus="available").status_code == 200

    def test_suspended_to_available(self, client):
        r = _mk_resource(client, status="available")
        _patch_resource(client, r["id"], resourceStatus="suspended")
        assert _patch_resource(client, r["id"], resourceStatus="available").status_code == 200

    def test_invalid_reserved_to_alarm(self, client):
        """reserved → alarm is not a legal transition."""
        r = _mk_resource(client, status="available")
        _patch_resource(client, r["id"], resourceStatus="reserved")
        resp = _patch_resource(client, r["id"], resourceStatus="alarm")
        assert resp.status_code == 422
        assert "illegal" in resp.json()["detail"].lower()

    def test_no_op_same_state(self, client):
        """Patching to the current state is always allowed."""
        r = _mk_resource(client, status="available")
        assert _patch_resource(client, r["id"], resourceStatus="available").status_code == 200


class TestResourceAdminStateTransitions:

    def test_unlocked_to_locked(self, client):
        r = _mk_resource(client)
        assert _patch_resource(client, r["id"], administrativeState="locked").status_code == 200

    def test_locked_to_unlocked(self, client):
        r = _mk_resource(client)
        _patch_resource(client, r["id"], administrativeState="locked")
        assert _patch_resource(client, r["id"], administrativeState="unlocked").status_code == 200

    def test_locked_to_shutdown(self, client):
        r = _mk_resource(client)
        _patch_resource(client, r["id"], administrativeState="locked")
        assert _patch_resource(client, r["id"], administrativeState="shutdown").status_code == 200

    def test_shutdown_to_locked_invalid(self, client):
        """shutdown → locked is not permitted; must go through unlocked first."""
        r = _mk_resource(client)
        _patch_resource(client, r["id"], administrativeState="shutdown")
        resp = _patch_resource(client, r["id"], administrativeState="locked")
        assert resp.status_code == 422

    def test_shutdown_to_unlocked_valid(self, client):
        r = _mk_resource(client)
        _patch_resource(client, r["id"], administrativeState="shutdown")
        assert _patch_resource(client, r["id"], administrativeState="unlocked").status_code == 200


# ── TMF638 Service: state transitions ────────────────────────────────────────

class TestServiceStateTransitions:

    def test_inactive_to_active(self, client):
        s = _mk_service(client, state="inactive")
        assert _patch_service(client, s["id"], state="active").status_code == 200

    def test_active_to_inactive(self, client):
        """active → inactive (suspension) is valid."""
        s = _mk_service(client, state="inactive")
        _patch_service(client, s["id"], state="active")
        assert _patch_service(client, s["id"], state="inactive").status_code == 200

    def test_active_to_terminated(self, client):
        s = _mk_service(client, state="inactive")
        _patch_service(client, s["id"], state="active")
        assert _patch_service(client, s["id"], state="terminated").status_code == 200

    def test_terminated_is_terminal(self, client):
        """No transition out of terminated."""
        s = _mk_service(client, state="inactive")
        _patch_service(client, s["id"], state="active")
        _patch_service(client, s["id"], state="terminated")
        resp = _patch_service(client, s["id"], state="inactive")
        assert resp.status_code == 422
        assert "terminal" in resp.json()["detail"].lower()

    def test_backward_active_to_designed_invalid(self, client):
        """active → designed is not a valid backward transition."""
        s = _mk_service(client, state="inactive")
        _patch_service(client, s["id"], state="active")
        resp = _patch_service(client, s["id"], state="designed")
        assert resp.status_code == 422

    def test_feasibility_to_designed(self, client):
        s = _mk_service(client, state="feasibilityChecked")
        assert _patch_service(client, s["id"], state="designed").status_code == 200

    def test_designed_to_inactive(self, client):
        s = _mk_service(client, state="designed")
        assert _patch_service(client, s["id"], state="inactive").status_code == 200

    def test_no_op_same_state(self, client):
        s = _mk_service(client, state="active")
        assert _patch_service(client, s["id"], state="active").status_code == 200


# ── TMF641 ServiceOrder: state transitions ───────────────────────────────────

class TestServiceOrderStateTransitions:

    def test_acknowledged_to_in_progress(self, client):
        o = _mk_order(client)
        assert _patch_order(client, o["id"], state="inProgress").status_code == 200

    def test_acknowledged_to_cancelled(self, client):
        o = _mk_order(client)
        assert _patch_order(client, o["id"], state="cancelled").status_code == 200

    def test_in_progress_to_completed(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        assert _patch_order(client, o["id"], state="completed").status_code == 200

    def test_in_progress_to_failed(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        assert _patch_order(client, o["id"], state="failed").status_code == 200

    def test_completed_is_terminal(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        _patch_order(client, o["id"], state="completed")
        resp = _patch_order(client, o["id"], state="inProgress")
        assert resp.status_code == 422
        assert "terminal" in resp.json()["detail"].lower()

    def test_cancelled_is_terminal(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="cancelled")
        resp = _patch_order(client, o["id"], state="inProgress")
        assert resp.status_code == 422

    def test_backward_completed_to_acknowledged_invalid(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        _patch_order(client, o["id"], state="completed")
        resp = _patch_order(client, o["id"], state="acknowledged")
        assert resp.status_code == 422

    def test_partial_can_retry_in_progress(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        _patch_order(client, o["id"], state="partial")
        assert _patch_order(client, o["id"], state="inProgress").status_code == 200

    def test_pending_to_in_progress(self, client):
        o = _mk_order(client)
        _patch_order(client, o["id"], state="pending")
        assert _patch_order(client, o["id"], state="inProgress").status_code == 200

    def test_error_message_contains_allowed_transitions(self, client):
        """Error detail should list what IS allowed, helping the developer."""
        o = _mk_order(client)
        _patch_order(client, o["id"], state="inProgress")
        _patch_order(client, o["id"], state="completed")
        resp = _patch_order(client, o["id"], state="inProgress")
        assert "none — terminal state" in resp.json()["detail"]

    def test_no_op_same_state(self, client):
        o = _mk_order(client)
        assert _patch_order(client, o["id"], state="acknowledged").status_code == 200
