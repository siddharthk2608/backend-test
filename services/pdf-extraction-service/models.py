# models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class TaxReturnAnswers(BaseModel):
    """Model for tax return answers"""
    your_first_name: Optional[str] = Field(None, description="First name")
    your_last_name: Optional[str] = Field(None, description="Last name")
    your_date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    your_social_security_number: Optional[str] = Field(None, description="Social security number")
    your_occupation: Optional[str] = Field(None, description="Occupation")
    are_you_married_: Optional[bool] = Field(None, description="Marital status")
    wages_current_year_not_owned: Optional[str] = Field(None, description="Current year wages")
    wages_next_year_not_owned: Optional[str] = Field(None, description="Next year wages")
    do_you_have_any_children_: Optional[bool] = Field(None, description="Has children")
    your_street_address: Optional[str] = Field(None, description="Street address")
    your_city: Optional[str] = Field(None, description="City")
    your_zip_code: Optional[str] = Field(None, description="ZIP code")
    plan_work_at_home: Optional[bool] = Field(None, description="Plans to work at home")
    home_square_footage: Optional[str] = Field(None, description="Home square footage")
    home_office_square_footage: Optional[str] = Field(None, description="Home office square footage")
    
    # WOTC (Work Opportunity Tax Credit) fields
    wotc_group1: Optional[str] = Field(
        None, 
        description="Total employees: Qualified Veteran (less than 1 year post-discharge)"
    )
    wotc_group2: Optional[str] = Field(
        None, 
        description="Total employees: Qualified Veteran (unemployed 4-6 months)"
    )
    wotc_group3: Optional[str] = Field(
        None, 
        description="Total employees: Qualified Veteran (unemployed 6+ months)"
    )
    wotc_group4: Optional[str] = Field(
        None, 
        description="Total employees: Qualified Veteran with disability (unemployed 6+ months)"
    )
    wotc_group5: Optional[str] = Field(
        None, 
        description="Total employees: Qualified Summer Youth Employee"
    )
    wotc_group6: Optional[str] = Field(
        None, 
        description="Total employees: Long-Term Family Assistance recipients"
    )
    
    export_net_profit: Optional[str] = Field(None, description="Export net profit")
    export_gross_revenue: Optional[str] = Field(None, description="Export gross revenue")
    other_income_notes: Optional[str] = Field(None, description="Other income notes")
    home_office_expenses_notes: Optional[str] = Field(None, description="Home office expenses notes")
    international_notes: Optional[str] = Field(None, description="International notes")
    client_notes: Optional[str] = Field("", description="Client notes")

    class Config:
        json_schema_extra = {
            "example": {
                "your_first_name": "Test",
                "your_last_name": "Member",
                "your_date_of_birth": "2001-01-26",
                "your_social_security_number": "123-45-6789",
                "your_occupation": "test",
                "are_you_married_": False,
                "wages_current_year_not_owned": "75000",
                "wages_next_year_not_owned": "80000",
                "do_you_have_any_children_": False,
                "your_street_address": "xyz",
                "your_city": "test city",
                "your_zip_code": "112232",
                "plan_work_at_home": True,
                "home_square_footage": "2500",
                "home_office_square_footage": "500",
                "wotc_group1": "2",
                "wotc_group2": "1",
                "wotc_group3": "3",
                "wotc_group4": "1",
                "wotc_group5": "4",
                "wotc_group6": "2",
                "export_net_profit": "150000",
                "export_gross_revenue": "500000",
                "other_income_notes": "None",
                "home_office_expenses_notes": "Nil",
                "international_notes": "NO",
                "client_notes": ""
            }
        }


class MetaData(BaseModel):
    """Metadata for the response"""
    brand: Optional[str] = Field("Accountingbiz", description="Brand name")


class TaxReturnResponse(BaseModel):
    """Model for API response"""
    meta: MetaData = Field(default_factory=lambda: MetaData(brand="Accountingbiz"), description="Metadata")
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    answers: TaxReturnAnswers = Field(..., description="Extracted tax return data")
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "meta": {
                    "brand": "Accountingbiz"
                },
                "success": True,
                "message": "Tax return processed successfully",
                "answers": {
                    "your_first_name": "Bharat",
                    "your_last_name": "Bhate",
                    "your_date_of_birth": "1986-08-29",
                    "your_social_security_number": "145-19-3983",
                    "your_occupation": "Entrepreneur",
                    "wotc_group1": "2",
                    "wotc_group2": "1",
                    "wotc_group3": "3",
                    "wotc_group4": "1",
                    "wotc_group5": "4",
                    "wotc_group6": "2"
                },
                "processing_metadata": {
                    "filename": "TaxReturn.pdf",
                    "processed_at": "2025-01-10T12:00:00Z",
                    "fields_extracted": 100
                }
            }
        }

        