"""
Common TMForum data types used across multiple APIs.
Based on TMForum Open API Common Schema v4.x
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class EntityRef(BaseModel):
    id: str
    href: Optional[str] = None
    name: Optional[str] = None
    referred_type: Optional[str] = Field(None, alias="@referredType")
    model_config = {"populate_by_name": True}


class RelatedParty(BaseModel):
    id: str
    href: Optional[str] = None
    name: Optional[str] = None
    role: str
    referred_type: Optional[str] = Field("Individual", alias="@referredType")
    model_config = {"populate_by_name": True}


class Characteristic(BaseModel):
    name: str
    value: Any
    value_type: Optional[str] = Field(None, alias="valueType")
    model_config = {"populate_by_name": True}


class SpecificationRef(BaseModel):
    id: str
    href: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    referred_type: Optional[str] = Field(None, alias="@referredType")
    model_config = {"populate_by_name": True}


class Note(BaseModel):
    id: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    text: str


class TimePeriod(BaseModel):
    start_date_time: Optional[datetime] = Field(None, alias="startDateTime")
    end_date_time: Optional[datetime] = Field(None, alias="endDateTime")
    model_config = {"populate_by_name": True}
