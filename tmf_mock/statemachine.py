"""
TMF Open API — Lifecycle state machine enforcement.

Sources:
  TMF638 v4.0.0  §5  Service Lifecycle States
  TMF639 v4.0.0  §5  Resource Lifecycle States
  TMF641 v4.0.0  §5  ServiceOrder / OrderItem Lifecycle States

Each dict maps:  current_state → {set of legal next states}

Terminal states have an empty set — no further transitions are permitted.
None as a key represents "newly created" (i.e. the entity has no prior state).
"""
from __future__ import annotations
from fastapi import HTTPException


# ── TMF638 Service states ────────────────────────────────────────────────────
#
#  feasibilityChecked → designed → reserved → inactive ↔ active → terminated
#
#  Rules per spec §5.1:
#  • feasibilityChecked: initial design state; can move to designed or be abandoned
#  • designed: resources identified; can be reserved or abandoned
#  • reserved: resources held; can become inactive (provisioned but not started)
#  • inactive: provisioned; can become active or be terminated
#  • active: in service; can become inactive (suspended) or terminated
#  • terminated: terminal; no further transitions

SERVICE_TRANSITIONS: dict[str | None, set[str]] = {
    None:                   {"feasibilityChecked", "designed", "reserved", "inactive", "active"},
    "feasibilityChecked":   {"designed", "terminated"},
    "designed":             {"reserved", "inactive", "terminated"},
    "reserved":             {"inactive", "terminated"},
    "inactive":             {"active", "terminated"},
    "active":               {"inactive", "terminated"},
    "terminated":           set(),   # terminal
}


# ── TMF639 Resource states ───────────────────────────────────────────────────
#
#  Rules per spec §5.1:
#  • available: normal operating state; can be reserved, suspended, or alarmed
#  • reserved: held for a specific purpose; can become available or suspended
#  • standby: present but not in active use; can become available or suspended
#  • alarm: fault condition; can recover to available or be suspended
#  • suspended: administratively out of service; can return to available
#  • unknown: transient discovery state; should resolve to a known state

RESOURCE_STATUS_TRANSITIONS: dict[str | None, set[str]] = {
    None:           {"available", "standby", "unknown"},
    "available":    {"reserved", "standby", "alarm", "suspended"},
    "reserved":     {"available", "suspended"},
    "standby":      {"available", "suspended"},
    "alarm":        {"available", "suspended"},
    "suspended":    {"available"},
    "unknown":      {"available", "standby", "alarm", "suspended"},
}

# Administrative state transitions (TMF639 §5.2)
RESOURCE_ADMIN_TRANSITIONS: dict[str | None, set[str]] = {
    None:       {"locked", "unlocked", "shutdown"},
    "unlocked": {"locked", "shutdown"},
    "locked":   {"unlocked", "shutdown"},
    "shutdown": {"unlocked"},   # must unlock before relocking
}

# Operational state is set by the network, not the operator — we allow any
# transition here but validate it's a known value (enum covers that).


# ── TMF641 ServiceOrder states ───────────────────────────────────────────────
#
#  acknowledged → rejected  (validation failed)
#  acknowledged → pending   (held for approval)
#  acknowledged → held      (manual hold)
#  acknowledged → inProgress
#  pending      → inProgress | cancelled
#  held         → inProgress | cancelled
#  inProgress   → completed | failed | partial | cancelled
#  partial      → inProgress (retry remaining items)
#  completed / failed / rejected / cancelled → terminal

SERVICE_ORDER_TRANSITIONS: dict[str | None, set[str]] = {
    None:           {"acknowledged"},   # server always sets acknowledged on create
    "acknowledged": {"rejected", "pending", "held", "inProgress", "cancelled"},
    "pending":      {"inProgress", "cancelled"},
    "held":         {"inProgress", "cancelled"},
    "inProgress":   {"completed", "failed", "partial", "cancelled"},
    "partial":      {"inProgress", "cancelled"},
    "completed":    set(),
    "failed":       set(),
    "rejected":     set(),
    "cancelled":    set(),
}

# OrderItem state follows the same lifecycle as the order itself
ORDER_ITEM_TRANSITIONS: dict[str | None, set[str]] = {
    None:           {"acknowledged"},
    "acknowledged": {"rejected", "pending", "held", "inProgress", "cancelled"},
    "pending":      {"inProgress", "cancelled"},
    "held":         {"inProgress", "cancelled"},
    "inProgress":   {"completed", "failed", "cancelled"},
    "completed":    set(),
    "failed":       set(),
    "rejected":     set(),
    "cancelled":    set(),
}


# ── Validation helpers ───────────────────────────────────────────────────────

def _check(
    entity_type: str,
    entity_id: str,
    field: str,
    transitions: dict[str | None, set[str]],
    current: str | None,
    requested: str,
) -> None:
    """Raise HTTP 422 if the requested state transition is not permitted."""
    if current == requested:
        return  # no-op, always fine
    allowed = transitions.get(current, set())
    if requested not in allowed:
        current_label = current or "(none)"
        raise HTTPException(
            status_code=422,
            detail=(
                f"{entity_type} '{entity_id}': illegal {field} transition "
                f"'{current_label}' → '{requested}'. "
                f"Allowed from '{current_label}': {sorted(allowed) or ['none — terminal state']}."
            ),
        )


def validate_service_state(service_id: str, current: str | None, requested: str) -> None:
    _check("Service", service_id, "state", SERVICE_TRANSITIONS, current, requested)


def validate_resource_status(resource_id: str, current: str | None, requested: str) -> None:
    _check("Resource", resource_id, "resourceStatus", RESOURCE_STATUS_TRANSITIONS, current, requested)


def validate_resource_admin_state(resource_id: str, current: str | None, requested: str) -> None:
    _check("Resource", resource_id, "administrativeState", RESOURCE_ADMIN_TRANSITIONS, current, requested)


def validate_service_order_state(order_id: str, current: str | None, requested: str) -> None:
    _check("ServiceOrder", order_id, "state", SERVICE_ORDER_TRANSITIONS, current, requested)


def validate_order_item_state(order_id: str, item_id: str, current: str | None, requested: str) -> None:
    _check(f"ServiceOrder '{order_id}' / orderItem", item_id, "state", ORDER_ITEM_TRANSITIONS, current, requested)
