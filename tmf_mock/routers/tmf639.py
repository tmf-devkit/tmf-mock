"""TMF639 Resource Inventory Management API — v4"""
from __future__ import annotations
import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from ..store import Store, get_store
from ..models.tmf639 import ResourceCreate, ResourceUpdate

router = APIRouter(prefix="/tmf-api/resourceInventoryManagement/v4", tags=["TMF639 Resource Inventory"])
BASE_URL = "http://localhost:8000"


def _store() -> Store:
    return get_store()


StoreD = Annotated[Store, Depends(_store)]


def _make_href(resource_id: str) -> str:
    return f"{BASE_URL}/tmf-api/resourceInventoryManagement/v4/resource/{resource_id}"


@router.get("/resource", response_model=list[dict])
def list_resources(
    store: StoreD, response: Response,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    fields: Optional[str] = Query(None),
    resource_status: Optional[str] = Query(None, alias="resourceStatus"),
    category: Optional[str] = None,
):
    all_items = store.list_resources(offset=0, limit=10000, resource_status=resource_status, category=category)
    response.headers["X-Total-Count"] = str(len(all_items))
    response.headers["X-Result-Count"] = str(min(limit, max(0, len(all_items) - offset)))
    return store.list_resources(offset=offset, limit=limit, fields=fields, resource_status=resource_status, category=category)


@router.get("/resource/{resource_id}", response_model=dict)
def get_resource(resource_id: str, store: StoreD, fields: Optional[str] = Query(None)):
    resource = store.get_resource(resource_id)
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        return {k: v for k, v in resource.items() if k in field_list or k == "id"}
    return resource


@router.post("/resource", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_resource(body: ResourceCreate, store: StoreD, response: Response):
    rid = str(uuid.uuid4())
    data = body.model_dump(by_alias=True, exclude_none=True)
    data["id"] = rid
    data["href"] = _make_href(rid)
    data.setdefault("@type", "Resource")
    data.setdefault("@baseType", "Resource")
    result = store.create_resource(data)
    response.headers["Location"] = result["href"]
    return result


@router.patch("/resource/{resource_id}", response_model=dict)
def update_resource(resource_id: str, body: ResourceUpdate, store: StoreD):
    patch = body.model_dump(by_alias=True, exclude_none=True)
    return store.update_resource(resource_id, patch)


@router.delete("/resource/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(resource_id: str, store: StoreD):
    store.delete_resource(resource_id)
