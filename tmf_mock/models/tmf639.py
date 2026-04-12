"""TMF639 Resource Inventory API — Pydantic models."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from .common import Characteristic, EntityRef, RelatedParty, SpecificationRef, Note


class ResourceStatus(str, Enum):
    standby = "standby"
    alarm = "alarm"
    available = "available"
    reserved = "reserved"
    suspended = "suspended"
    unknown = "unknown"


class ResourceOperationalState(str, Enum):
    enable = "enable"
    disable = "disable"


class ResourceAdministrativeState(str, Enum):
    locked = "locked"
    unlocked = "unlocked"
    shutdown = "shutdown"


class ResourceUsageState(str, Enum):
    idle = "idle"
    active = "active"
    busy = "busy"


class Feature(BaseModel):
    id: Optional[str] = None
    name: str
    is_enabled: Optional[bool] = Field(True, alias="isEnabled")
    feature_characteristic: Optional[list[Characteristic]] = Field(None, alias="featureCharacteristic")
    model_config = {"populate_by_name": True}


class Place(BaseModel):
    id: str
    href: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    referred_type: Optional[str] = Field(None, alias="@referredType")
    model_config = {"populate_by_name": True}


class ResourceCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    end_operating_date: Optional[datetime] = Field(None, alias="endOperatingDate")
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    start_operating_date: Optional[datetime] = Field(None, alias="startOperatingDate")
    administrative_state: Optional[ResourceAdministrativeState] = Field(ResourceAdministrativeState.unlocked, alias="administrativeState")
    operational_state: Optional[ResourceOperationalState] = Field(ResourceOperationalState.enable, alias="operationalState")
    resource_status: Optional[ResourceStatus] = Field(ResourceStatus.available, alias="resourceStatus")
    usage_state: Optional[ResourceUsageState] = Field(ResourceUsageState.idle, alias="usageState")
    place: Optional[list[Place]] = None
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    resource_characteristic: Optional[list[Characteristic]] = Field(None, alias="resourceCharacteristic")
    resource_specification: Optional[SpecificationRef] = Field(None, alias="resourceSpecification")
    resource_relationship: Optional[list[EntityRef]] = Field(None, alias="resourceRelationship")
    activation_feature: Optional[list[Feature]] = Field(None, alias="activationFeature")
    note: Optional[list[Note]] = None
    model_config = {"populate_by_name": True}


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    resource_version: Optional[str] = Field(None, alias="resourceVersion")
    administrative_state: Optional[ResourceAdministrativeState] = Field(None, alias="administrativeState")
    operational_state: Optional[ResourceOperationalState] = Field(None, alias="operationalState")
    resource_status: Optional[ResourceStatus] = Field(None, alias="resourceStatus")
    usage_state: Optional[ResourceUsageState] = Field(None, alias="usageState")
    place: Optional[list[Place]] = None
    related_party: Optional[list[RelatedParty]] = Field(None, alias="relatedParty")
    resource_characteristic: Optional[list[Characteristic]] = Field(None, alias="resourceCharacteristic")
    note: Optional[list[Note]] = None
    model_config = {"populate_by_name": True}


class Resource(ResourceCreate):
    id: str
    href: str
    at_type: Optional[str] = Field("Resource", alias="@type")
    at_schema_location: Optional[str] = Field(None, alias="@schemaLocation")
    at_base_type: Optional[str] = Field("Resource", alias="@baseType")
    model_config = {"populate_by_name": True}
