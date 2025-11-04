# shared/db_models.py
"""
MongoDB Document Models (Pydantic v2 Compatible)
"""

from __future__ import annotations

from pydantic import BaseModel, Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


# --------------------------------------------------------------------
# Custom ObjectId Type for Pydantic v2
# --------------------------------------------------------------------
class PyObjectId(ObjectId):
    """Custom BSON ObjectId for Pydantic v2."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: JsonSchemaValue, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Define schema for OpenAPI/JSON output."""
        schema = handler(schema)
        schema.update(type="string", examples=["64a4b7f3d2e3b3e2d6c9a2f1"])
        return schema


# --------------------------------------------------------------------
# Base MongoDB Document Models
# --------------------------------------------------------------------
class TaxReturnDocument(BaseModel):
    """Tax Return MongoDB Document"""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    tax_year: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Tax data
    personal_info: Dict[str, Any]
    income: Dict[str, Any]
    deductions: Optional[Dict[str, Any]] = None
    credits: Optional[Dict[str, Any]] = None
    dependents: Optional[List[Dict[str, Any]]] = None

    # Metadata
    source: str = "web_form"  # web_form, pdf_upload, api
    status: str = "draft"  # draft, submitted, processed

    class Config:
        populate_by_name = True  # ✅ renamed for Pydantic v2
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TaxAnalysisDocument(BaseModel):
    """Tax Analysis MongoDB Document"""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    tax_year: int
    analysis_date: datetime = Field(default_factory=datetime.utcnow)

    summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    scenarios: List[Dict[str, Any]]
    ai_insights: Dict[str, Any]
    quarterly_estimates: Dict[str, Any]
    processing_metadata: Dict[str, Any]
    tax_return_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserDocument(BaseModel):
    """User MongoDB Document"""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    last_analysis: Optional[datetime] = None

    total_returns: int = 0
    total_analyses: int = 0
    settings: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# --------------------------------------------------------------------
# Helper Conversion Functions
# --------------------------------------------------------------------
def model_to_dict(model: BaseModel, exclude_none: bool = True) -> dict:
    """Convert Pydantic model to dict for MongoDB insertion"""
    return model.model_dump(by_alias=True, exclude_none=exclude_none)


def dict_to_model(data: dict, model_class: type[BaseModel]):
    """Convert MongoDB dict to Pydantic model"""
    return model_class(**data)
