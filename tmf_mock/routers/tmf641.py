"""TMF641 Service Ordering API — v4"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from ..store import Store, get_store
from ..models.tmf641 import ServiceOrderCreate, ServiceOrderUpdate

router = APIRouter(prefix="/tmf-api/serviceOrdering/v4", tags=["TMF641 Service Ordering"])
BASE_URL = "http://localhost:8000"


def _store() -> Store:
    return get_store()


StoreD = Annotated[Store, Depends(_store)]


def _make_href(order_id: str) -> str:
    return f"{BASE_URL}/tmf-api/serviceOrdering/v4/serviceOrder/{order_id}"


@router.get("/serviceOrder", response_model=list[dict])
def list_service_orders(
    store: StoreD, response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fields: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    all_items = store.list_service_orders(state=state, category=category)
    response.headers["X-Total-Count"] = str(len(all_items))
    return store.list_service_orders(offset=offset, limit=limit, fields=fields, state=state, category=category)


@router.get("/serviceOrder/{order_id}", response_model=dict)
def get_service_order(order_id: str, store: StoreD, fields: Optional[str] = Query(None)):
    order = store.get_service_order(order_id)
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        return {k: v for k, v in order.items() if k in field_list or k == "id"}
    return order


@router.post("/serviceOrder", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_service_order(body: ServiceOrderCreate, store: StoreD, response: Response):
    oid = str(uuid.uuid4())
    data = body.model_dump(by_alias=True, exclude_none=True)
    data["id"] = oid
    data["href"] = _make_href(oid)
    data["state"] = "acknowledged"
    data["orderDate"] = datetime.now(tz=timezone.utc).isoformat()
    data.setdefault("@type", "ServiceOrder")
    data.setdefault("@baseType", "ServiceOrder")
    result = store.create_service_order(data)
    response.headers["Location"] = result["href"]
    return result


@router.patch("/serviceOrder/{order_id}", response_model=dict)
def update_service_order(order_id: str, body: ServiceOrderUpdate, store: StoreD):
    patch = body.model_dump(by_alias=True, exclude_none=True)
    return store.update_service_order(order_id, patch)


@router.delete("/serviceOrder/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_order(order_id: str, store: StoreD):
    store.delete_service_order(order_id)
