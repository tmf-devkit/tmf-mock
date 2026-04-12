"""TMF641 Service Ordering API — Pydantic models."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from .common import Characteristic, EntityRef, RelatedParty, SpecificationRef, Note
from .tmf638 import ServiceCreate, SupportingResource


class ServiceOrderState(str, Enum):
    acknowledged = "acknowledged"
    rejected = "rejected"
    pending = "pending"
    held = "held"
    in_progress = "inProgress"
    cancelled = "cancelled"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class OrderItemAction(str, Enum):
    add = "add"
    modify = "modify"
    delete = "delete"
    no_change = "noChange"


class OrderItemState(str, Enum):
    acknowledged = "acknowledged"
    rejected = "rejected"
    pending = "pending"
    held = "held"
    in_progress = "inProgress"
    cancelled = "cancelled"
    completed = "completed"
    failed = "failed"


class ServiceRefOrValue(BaseModel):
    id: Optional[str] = None
    href: Optional[str] = None
    name: Optional[str] = None
    service_type: Optional[str] = Field(None, alias="serviceType")
    state: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    service_characteristic: Optional[list[Characteristic]] = Field(None, alias="serviceCharacteristic")
    service_specification: Optional[SpecificationRef] = Field(None, alias="serviceSpecification")
    supporting_resource: Optional[list[SupportingResource]] = Field(None, alias="supportingResource")
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    at_type: Optional[str] = Field("Service", alias="@type")
    at_referred_type: Optional[str] = Field(None, alias="@referredType")
    model_config = {"populate_by_name": True}


class ServiceOrderItemRelationship(BaseModel):
    id: str
    relationship_type: str = Field(..., alias="relationshipType")
    model_config = {"populate_by_name": True}


class ServiceOrderItem(BaseModel):
    id: str
    action: OrderItemAction
    state: Optional[OrderItemState] = OrderItemState.acknowledged
    quantity: Optional[int] = 1
    service: ServiceRefOrValue
    order_item_relationship: Optional[list[ServiceOrderItemRelationship]] = Field(None, alias="orderItemRelationship")
    appointment: Optional[EntityRef] = None
    model_config = {"populate_by_name": True}


class ServiceOrderCreate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    requested_start_date: Optional[datetime] = Field(None, alias="requestedStartDate")
    requested_completion_date: Optional[datetime] = Field(None, alias="requestedCompletionDate")
    external_id: Optional[str] = Field(None, alias="externalId")
    note: Optional[list[Note]] = None
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    order_item: list[ServiceOrderItem] = Field(..., alias="orderItem")
    model_config = {"populate_by_name": True}


class ServiceOrderUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    state: Optional[ServiceOrderState] = None
    requested_completion_date: Optional[datetime] = Field(None, alias="requestedCompletionDate")
    note: Optional[list[Note]] = None
    order_item: Optional[list[ServiceOrderItem]] = Field(None, alias="orderItem")
    model_config = {"populate_by_name": True}


class ServiceOrder(ServiceOrderCreate):
    id: str
    href: str
    state: ServiceOrderState = ServiceOrderState.acknowledged
    order_date: datetime = Field(..., alias="orderDate")
    completion_date: Optional[datetime] = Field(None, alias="completionDate")
    expected_completion_date: Optional[datetime] = Field(None, alias="expectedCompletionDate")
    at_type: Optional[str] = Field("ServiceOrder", alias="@type")
    at_schema_location: Optional[str] = Field(None, alias="@schemaLocation")
    at_base_type: Optional[str] = Field("ServiceOrder", alias="@baseType")
    model_config = {"populate_by_name": True}
