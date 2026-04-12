"""TMF638 Service Inventory Management API — v4"""
from __future__ import annotations
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from ..store import Store, get_store
from ..models.tmf638 import ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/tmf-api/serviceInventoryManagement/v4", tags=["TMF638 Service Inventory"])
BASE_URL = "http://localhost:8000"


def _store() -> Store:
    return get_store()


StoreD = Annotated[Store, Depends(_store)]


def _make_href(service_id: str) -> str:
    return f"{BASE_URL}/tmf-api/serviceInventoryManagement/v4/service/{service_id}"


@router.get("/service", response_model=list[dict])
def list_services(
    store: StoreD, response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fields: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    service_type: Optional[str] = Query(None, alias="serviceType"),
    category: Optional[str] = Query(None),
):
    all_items = store.list_services(state=state, service_type=service_type, category=category)
    response.headers["X-Total-Count"] = str(len(all_items))
    return store.list_services(offset=offset, limit=limit, fields=fields, state=state, service_type=service_type, category=category)


@router.get("/service/{service_id}", response_model=dict)
def get_service(service_id: str, store: StoreD, fields: Optional[str] = Query(None)):
    service = store.get_service(service_id)
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        return {k: v for k, v in service.items() if k in field_list or k == "id"}
    return service


@router.post("/service", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_service(body: ServiceCreate, store: StoreD, response: Response):
    sid = str(uuid.uuid4())
    data = body.model_dump(by_alias=True, exclude_none=True)
    data["id"] = sid
    data["href"] = _make_href(sid)
    data.setdefault("@type", "Service")
    data.setdefault("@baseType", "Service")
    result = store.create_service(data)
    response.headers["Location"] = result["href"]
    return result


@router.patch("/service/{service_id}", response_model=dict)
def update_service(service_id: str, body: ServiceUpdate, store: StoreD):
    patch = body.model_dump(by_alias=True, exclude_none=True)
    return store.update_service(service_id, patch)


@router.delete("/service/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(service_id: str, store: StoreD):
    store.delete_service(service_id)
