"""
In-memory store for all TMF entities.

Cross-API referential integrity AND lifecycle state machine enforcement
are both handled here, keeping routers thin.
"""
from __future__ import annotations

from typing import Optional
from fastapi import HTTPException

from .models.tmf639 import Resource
from .models.tmf638 import Service
from .models.tmf641 import ServiceOrder
from .statemachine import (
    validate_service_state,
    validate_resource_status,
    validate_resource_admin_state,
    validate_service_order_state,
    validate_order_item_state,
)


class Store:
    def __init__(self) -> None:
        self._resources: dict[str, dict] = {}
        self._services: dict[str, dict] = {}
        self._service_orders: dict[str, dict] = {}

    # ── TMF639 — Resource ────────────────────────────────────────────────────

    def list_resources(self, offset=0, limit=20, fields=None, resource_status=None, category=None):
        items = list(self._resources.values())
        if resource_status:
            items = [r for r in items if r.get("resourceStatus") == resource_status]
        if category:
            items = [r for r in items if r.get("category") == category]
        results = items[offset: offset + limit]
        if fields:
            field_list = [f.strip() for f in fields.split(",")]
            results = [{k: v for k, v in r.items() if k in field_list or k == "id"} for r in results]
        return results

    def get_resource(self, resource_id: str) -> dict:
        r = self._resources.get(resource_id)
        if not r:
            raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
        return r

    def create_resource(self, data: dict) -> dict:
        self._resources[data["id"]] = data
        return data

    def update_resource(self, resource_id: str, patch: dict) -> dict:
        existing = self.get_resource(resource_id)

        # State machine: resourceStatus
        if "resourceStatus" in patch and patch["resourceStatus"] is not None:
            validate_resource_status(
                resource_id,
                existing.get("resourceStatus"),
                patch["resourceStatus"],
            )

        # State machine: administrativeState
        if "administrativeState" in patch and patch["administrativeState"] is not None:
            validate_resource_admin_state(
                resource_id,
                existing.get("administrativeState"),
                patch["administrativeState"],
            )

        for k, v in patch.items():
            if v is not None:
                existing[k] = v
        self._resources[resource_id] = existing
        return existing

    def delete_resource(self, resource_id: str) -> None:
        self.get_resource(resource_id)
        for svc in self._services.values():
            for ref in svc.get("supportingResource") or []:
                if ref.get("id") == resource_id:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Resource {resource_id} is referenced by Service {svc['id']}. "
                            "Remove the reference before deleting."
                        ),
                    )
        del self._resources[resource_id]

    def resource_exists(self, resource_id: str) -> bool:
        return resource_id in self._resources

    # ── TMF638 — Service ─────────────────────────────────────────────────────

    def list_services(self, offset=0, limit=20, fields=None, state=None, service_type=None, category=None):
        items = list(self._services.values())
        if state:
            items = [s for s in items if s.get("state") == state]
        if service_type:
            items = [s for s in items if s.get("serviceType") == service_type]
        if category:
            items = [s for s in items if s.get("category") == category]
        return items[offset: offset + limit]

    def get_service(self, service_id: str) -> dict:
        s = self._services.get(service_id)
        if not s:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        return s

    def create_service(self, data: dict) -> dict:
        # Referential integrity: all supportingResource refs must exist in TMF639
        for ref in data.get("supportingResource") or []:
            if not self.resource_exists(ref["id"]):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"supportingResource ref '{ref['id']}' does not exist in "
                        "Resource Inventory (TMF639). Create the Resource first."
                    ),
                )
        self._services[data["id"]] = data
        return data

    def update_service(self, service_id: str, patch: dict) -> dict:
        existing = self.get_service(service_id)

        # State machine: service lifecycle
        if "state" in patch and patch["state"] is not None:
            validate_service_state(
                service_id,
                existing.get("state"),
                patch["state"],
            )

        # Referential integrity: validate any new supportingResource refs
        for ref in patch.get("supportingResource") or []:
            if not self.resource_exists(ref["id"]):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"supportingResource ref '{ref['id']}' does not exist in "
                        "Resource Inventory (TMF639)."
                    ),
                )

        for k, v in patch.items():
            if v is not None:
                existing[k] = v
        self._services[service_id] = existing
        return existing

    def delete_service(self, service_id: str) -> None:
        self.get_service(service_id)
        for order in self._service_orders.values():
            for item in order.get("orderItem") or []:
                svc = item.get("service") or {}
                if svc.get("id") == service_id:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Service {service_id} is referenced by ServiceOrder {order['id']}.",
                    )
        del self._services[service_id]

    def service_exists(self, service_id: str) -> bool:
        return service_id in self._services

    # ── TMF641 — ServiceOrder ────────────────────────────────────────────────

    def list_service_orders(self, offset=0, limit=20, fields=None, state=None, category=None):
        items = list(self._service_orders.values())
        if state:
            items = [o for o in items if o.get("state") == state]
        if category:
            items = [o for o in items if o.get("category") == category]
        results = items[offset: offset + limit]
        if fields:
            field_list = [f.strip() for f in fields.split(",")]
            results = [{k: v for k, v in o.items() if k in field_list or k == "id"} for o in results]
        return results

    def get_service_order(self, order_id: str) -> dict:
        o = self._service_orders.get(order_id)
        if not o:
            raise HTTPException(status_code=404, detail=f"ServiceOrder {order_id} not found")
        return o

    def create_service_order(self, data: dict) -> dict:
        # Referential integrity: modify/delete/noChange must reference an existing service
        for item in data.get("orderItem") or []:
            svc = item.get("service") or {}
            svc_id = svc.get("id")
            if svc_id and item.get("action") in ("modify", "delete", "noChange"):
                if not self.service_exists(svc_id):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"ServiceOrderItem references Service '{svc_id}' which does not exist. "
                            "Use action='add' to create a new service."
                        ),
                    )
        self._service_orders[data["id"]] = data
        return data

    def update_service_order(self, order_id: str, patch: dict) -> dict:
        existing = self.get_service_order(order_id)

        # State machine: order-level state
        if "state" in patch and patch["state"] is not None:
            validate_service_order_state(
                order_id,
                existing.get("state"),
                patch["state"],
            )

        # State machine: per-item state transitions
        for item_patch in patch.get("orderItem") or []:
            item_id = item_patch.get("id")
            if item_id and "state" in item_patch and item_patch["state"] is not None:
                # Find the existing item to get its current state
                current_item = next(
                    (i for i in (existing.get("orderItem") or []) if i.get("id") == item_id),
                    None,
                )
                current_item_state = current_item.get("state") if current_item else None
                validate_order_item_state(
                    order_id,
                    item_id,
                    current_item_state,
                    item_patch["state"],
                )

        for k, v in patch.items():
            if v is not None:
                existing[k] = v
        self._service_orders[order_id] = existing
        return existing

    def delete_service_order(self, order_id: str) -> None:
        self.get_service_order(order_id)
        del self._service_orders[order_id]

    # ── Utility ──────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "resources": len(self._resources),
            "services": len(self._services),
            "serviceOrders": len(self._service_orders),
        }

    def reset(self) -> None:
        self._resources.clear()
        self._services.clear()
        self._service_orders.clear()


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def set_store(store: Store) -> None:
    global _store
    _store = store
