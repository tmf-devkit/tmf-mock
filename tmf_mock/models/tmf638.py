"""TMF638 Service Inventory API — Pydantic models."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from .common import Characteristic, EntityRef, RelatedParty, SpecificationRef, Note


class ServiceState(str, Enum):
    feasibility_checked = "feasibilityChecked"
    designed = "designed"
    reserved = "reserved"
    inactive = "inactive"
    active = "active"
    terminated = "terminated"


class ServiceRelationship(BaseModel):
    relationship_type: str = Field(..., alias="relationshipType")
    service: EntityRef
    model_config = {"populate_by_name": True}


class SupportingResource(BaseModel):
    id: str
    href: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    referred_type: Optional[str] = Field("Resource", alias="@referredType")
    model_config = {"populate_by_name": True}


class ServiceCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    service_type: Optional[str] = Field(None, alias="serviceType")
    state: Optional[ServiceState] = ServiceState.inactive
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    has_started: Optional[bool] = Field(None, alias="hasStarted")
    is_stateful: Optional[bool] = Field(None, alias="isStateful")
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    service_characteristic: Optional[list[Characteristic]] = Field(None, alias="serviceCharacteristic")
    service_specification: Optional[SpecificationRef] = Field(None, alias="serviceSpecification")
    service_relationship: Optional[list[ServiceRelationship]] = Field(None, alias="serviceRelationship")
    supporting_resource: Optional[list[SupportingResource]] = Field(None, alias="supportingResource")
    supporting_service: Optional[list[EntityRef]] = Field(None, alias="supportingService")
    note: Optional[list[Note]] = None
    model_config = {"populate_by_name": True}


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    service_type: Optional[str] = Field(None, alias="serviceType")
    state: Optional[ServiceState] = None
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    service_characteristic: Optional[list[Characteristic]] = Field(None, alias="serviceCharacteristic")
    supporting_resource: Optional[list[SupportingResource]] = Field(None, alias="supportingResource")
    note: Optional[list[Note]] = None
    model_config = {"populate_by_name": True}


class Service(ServiceCreate):
    id: str
    href: str
    at_type: Optional[str] = Field("Service", alias="@type")
    at_schema_location: Optional[str] = Field(None, alias="@schemaLocation")
    at_base_type: Optional[str] = Field("Service", alias="@baseType")
    model_config = {"populate_by_name": True}
