# tax_planning_service/main.py
"""
AI-Driven Tax Planning Service with Gemini Flash 2.5
Analyzes tax data and provides personalized recommendations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
import json
import google.generativeai as genai

# Import logging configuration
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from shared.database import Database
from shared.db_models import TaxAnalysisDocument, model_to_dict

from logging_config import setup_logger, get_logger



# Setup logger
logger = setup_logger(
    service_name="tax-planning",
    log_level="INFO"
)

# Initialize FastAPI app
app = FastAPI(
    title="AI-Driven Tax Planning Service (Gemini Flash 2.5)",
    description="Microservice for tax planning analysis and recommendations using Gemini",
    version="1.0.0"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DATABASE CONNECTION ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("Starting up Tax Planning Service...")
    await Database.connect_db()
    logger.info("Database connected successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("Shutting down Tax Planning Service...")
    await Database.close_db()
    logger.info("Database connection closed")


# Configure Gemini API - REPLACE WITH YOUR API KEY
genai.configure(api_key='AIzaSyBrCDaECvgQLeju542GD7SBOnPzG3abU6k')

# Initialize Gemini model
gemini_model = genai.GenerativeModel(
    model_name='gemini-2.0-flash-exp',
    generation_config={
        'temperature': 0.3,
        'top_p': 0.95,
        'top_k': 40,
        'max_output_tokens': 8192,
    }
)


# ==================== MODELS ====================

class PersonalInfo(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    ssn: str
    occupation: str
    marital_status: str
    street_address: str
    city: str
    zip_code: str


class Income(BaseModel):
    wages_current_year: float
    wages_next_year: float
    business_net_profit: float
    business_gross_revenue: float


class HomeOffice(BaseModel):
    home_square_footage: int
    office_square_footage: int
    works_from_home: bool


class WOTC(BaseModel):
    group1: int = 0  # Qualified Veteran (<1 year)
    group2: int = 0  # Qualified Veteran (unemployed 4-6 months)
    group3: int = 0  # Qualified Veteran (unemployed 6+ months)
    group4: int = 0  # Qualified Veteran with disability (6+ months)
    group5: int = 0  # Summer Youth
    group6: int = 0  # Long-Term Family Assistance


class Deductions(BaseModel):
    home_office: Optional[HomeOffice] = None


class Credits(BaseModel):
    wotc: Optional[WOTC] = None


class Dependents(BaseModel):
    has_children: bool
    num_dependents: int = 0


class TaxData(BaseModel):
    personal_info: PersonalInfo
    income: Income
    deductions: Optional[Deductions] = None
    credits: Optional[Credits] = None
    dependents: Optional[Dependents] = None


class AnalysisOptions(BaseModel):
    include_scenarios: bool = True
    optimization_level: str = "moderate"  # conservative, moderate, aggressive
    projection_years: int = 1


class TaxAnalysisRequest(BaseModel):
    user_id: str
    tax_year: int
    tax_data: TaxData
    options: AnalysisOptions = AnalysisOptions()


class Recommendation(BaseModel):
    id: str
    title: str
    description: str
    potential_savings: float
    priority: str  # high, medium, low
    category: str
    action_items: List[str]
    deadline: Optional[str] = None
    confidence: float


class TaxScenario(BaseModel):
    name: str
    description: str
    tax_liability: float
    effective_rate: float
    changes: List[str]
    savings: Optional[float] = None


class AIInsights(BaseModel):
    key_findings: List[str]
    risks: List[str]
    opportunities: List[str]


class TaxSummary(BaseModel):
    total_income: float
    total_deductions: float
    total_credits: float
    taxable_income: float
    total_tax_liability: float
    effective_tax_rate: float


class QuarterlyEstimates(BaseModel):
    q1: float
    q2: float
    q3: float
    q4: float
    total: float


class ProcessingMetadata(BaseModel):
    processing_time_seconds: float
    ai_model: str
    optimization_level: str
    total_potential_savings: float


class TaxAnalysisResponse(BaseModel):
    success: bool
    user_id: str
    tax_year: int
    summary: TaxSummary
    recommendations: List[Recommendation]
    scenarios: List[TaxScenario]
    ai_insights: AIInsights
    quarterly_estimates: QuarterlyEstimates
    processing_metadata: ProcessingMetadata
    timestamp: str


# ==================== TAX CALCULATION FUNCTIONS ====================

def calculate_federal_tax(taxable_income: float, filing_status: str = "single") -> float:
    """Calculate federal income tax based on 2024 tax brackets"""
    if filing_status == "single":
        brackets = [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (float('inf'), 0.37)
        ]
    else:  # married_joint
        brackets = [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float('inf'), 0.37)
        ]
    
    tax = 0
    previous_limit = 0
    
    for limit, rate in brackets:
        if taxable_income <= previous_limit:
            break
        
        taxable_in_bracket = min(taxable_income, limit) - previous_limit
        tax += taxable_in_bracket * rate
        previous_limit = limit
        
        if taxable_income <= limit:
            break
    
    return tax


def calculate_self_employment_tax(net_profit: float) -> float:
    """Calculate self-employment tax (15.3%)"""
    if net_profit <= 0:
        return 0
    
    se_income = net_profit * 0.9235
    ss_limit = 160200
    ss_tax = min(se_income, ss_limit) * 0.124
    medicare_tax = se_income * 0.029
    
    if se_income > 200000:
        medicare_tax += (se_income - 200000) * 0.009
    
    return ss_tax + medicare_tax


def calculate_home_office_deduction(home_sqft: int, office_sqft: int, business_use_percentage: float = 1.0) -> tuple:
    """Calculate home office deduction using both methods"""
    simplified = min(office_sqft, 300) * 5
    
    if home_sqft > 0:
        percentage = (office_sqft / home_sqft) * business_use_percentage
        annual_home_expenses = 18000
        actual = annual_home_expenses * percentage
    else:
        actual = 0
    
    return simplified, actual


def calculate_wotc_credit(wotc_data: WOTC) -> float:
    """Calculate Work Opportunity Tax Credit"""
    credit = 0
    credit += wotc_data.group1 * 2400
    credit += wotc_data.group2 * 4800
    credit += wotc_data.group3 * 5600
    credit += wotc_data.group4 * 9600
    credit += wotc_data.group5 * 1200
    credit += wotc_data.group6 * 9000
    return credit


def calculate_child_tax_credit(num_children: int, income: float) -> float:
    """Calculate Child Tax Credit (2024)"""
    if num_children == 0:
        return 0
    
    base_credit = 2000 * num_children
    
    if income > 400000:
        reduction = ((income - 400000) // 1000) * 50
        return max(0, base_credit - reduction)
    
    return base_credit


# ==================== AI ANALYSIS FUNCTIONS ====================

def generate_ai_recommendations(tax_data: TaxData, tax_summary: TaxSummary) -> tuple:
    """Use Gemini to generate personalized tax recommendations"""
    logger.info("Generating AI recommendations with Gemini Flash 2.5...")
    
    input_text = f"""You are a tax planning expert. Analyze this tax situation and provide personalized recommendations.

**TAX SITUATION:**
- Name: {tax_data.personal_info.first_name} {tax_data.personal_info.last_name}
- Marital Status: {tax_data.personal_info.marital_status}
- Total Income: ${tax_summary.total_income:,.2f}
- Current Tax Liability: ${tax_summary.total_tax_liability:,.2f}
- Effective Tax Rate: {tax_summary.effective_tax_rate:.1f}%

**INCOME DETAILS:**
- W-2 Wages (Current Year): ${tax_data.income.wages_current_year:,.2f}
- W-2 Wages (Next Year): ${tax_data.income.wages_next_year:,.2f}
- Business Net Profit: ${tax_data.income.business_net_profit:,.2f}
- Business Gross Revenue: ${tax_data.income.business_gross_revenue:,.2f}

**DEDUCTIONS:**
{f"- Home Office: {tax_data.deductions.home_office.office_square_footage} sqft office in {tax_data.deductions.home_office.home_square_footage} sqft home" if tax_data.deductions and tax_data.deductions.home_office else "- No home office deduction"}

**CREDITS:**
{f"- WOTC Employees: Group1={tax_data.credits.wotc.group1}, Group2={tax_data.credits.wotc.group2}, Group3={tax_data.credits.wotc.group3}, Group4={tax_data.credits.wotc.group4}, Group5={tax_data.credits.wotc.group5}, Group6={tax_data.credits.wotc.group6}" if tax_data.credits and tax_data.credits.wotc else "- No WOTC credits"}

**DEPENDENTS:**
{f"- Has Children: {tax_data.dependents.has_children}, Number: {tax_data.dependents.num_dependents}" if tax_data.dependents else "- No dependents information"}

---

**TASK: Provide 5-8 specific, actionable tax planning recommendations.**

For each recommendation, provide:
1. A clear, specific title
2. Detailed description
3. Estimated potential savings (realistic dollar amount)
4. Priority (high/medium/low)
5. Category (deduction/credit/retirement/business_structure/estimated_payments)
6. 2-4 specific action items
7. Deadline (if applicable)
8. Confidence score (0.0-1.0)

Also provide:
- 3-5 key findings about this tax situation
- 2-3 potential risks to watch out for
- 2-3 opportunities for tax savings

**OUTPUT FORMAT (JSON):**
```json
{{
  "recommendations": [
    {{
      "id": "rec_1",
      "title": "Maximize Home Office Deduction",
      "description": "Detailed description...",
      "potential_savings": 1875,
      "priority": "high",
      "category": "deduction",
      "action_items": [
        "Calculate exact business use percentage",
        "Document monthly home expenses",
        "Compare simplified vs actual expense method"
      ],
      "deadline": "2024-12-31",
      "confidence": 0.9
    }}
  ],
  "ai_insights": {{
    "key_findings": [
      "Strong W-2 income provides stable tax base",
      "Home office deduction is underutilized"
    ],
    "risks": [
      "No retirement contributions detected",
      "Estimated tax payments may be needed"
    ],
    "opportunities": [
      "Consider S-Corp election for SE tax savings",
      "Maximize HSA contributions"
    ]
  }}
}}
```

**IMPORTANT:**
- Be specific and actionable
- Base savings on realistic calculations
- Consider both federal and state tax implications
- Prioritize recommendations by impact
- Ensure action items are clear and achievable"""

    try:
        # Call Gemini API
        response = gemini_model.generate_content(input_text)
        response_text = response.text.strip()
        
        # Remove markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON
        ai_response = json.loads(response_text)
        
        # Convert to Pydantic models
        recommendations = [
            Recommendation(**rec) for rec in ai_response.get("recommendations", [])
        ]
        
        ai_insights = AIInsights(**ai_response.get("ai_insights", {
            "key_findings": [],
            "risks": [],
            "opportunities": []
        }))
        
        logger.info(f"Generated {len(recommendations)} recommendations")
        
        return recommendations, ai_insights
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini JSON response: {e}")
        return get_fallback_recommendations(tax_data, tax_summary)
    
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return get_fallback_recommendations(tax_data, tax_summary)


def get_fallback_recommendations(tax_data: TaxData, tax_summary: TaxSummary) -> tuple:
    """Provide rule-based recommendations if AI fails"""
    logger.warning("Using fallback rule-based recommendations")
    
    recommendations = []
    rec_id = 1
    
    # Home office recommendation
    if tax_data.deductions and tax_data.deductions.home_office and tax_data.deductions.home_office.works_from_home:
        simplified, actual = calculate_home_office_deduction(
            tax_data.deductions.home_office.home_square_footage,
            tax_data.deductions.home_office.office_square_footage
        )
        savings = max(simplified, actual) * 0.22
        
        recommendations.append(Recommendation(
            id=f"rec_{rec_id}",
            title="Maximize Home Office Deduction",
            description="You qualify for a home office deduction. Choose between simplified ($5/sqft) and actual expense methods.",
            potential_savings=savings,
            priority="high",
            category="deduction",
            action_items=[
                "Calculate exact business use percentage",
                "Document all home expenses monthly",
                "Compare simplified vs actual expense method",
                "Keep detailed records for audit protection"
            ],
            deadline="2024-12-31",
            confidence=0.9
        ))
        rec_id += 1
    
    # WOTC recommendation
    if tax_data.credits and tax_data.credits.wotc:
        total_wotc = calculate_wotc_credit(tax_data.credits.wotc)
        if total_wotc > 0:
            recommendations.append(Recommendation(
                id=f"rec_{rec_id}",
                title="Claim Work Opportunity Tax Credit (WOTC)",
                description=f"You're eligible for ${total_wotc:,.0f} in WOTC credits for qualified employee hires.",
                potential_savings=total_wotc,
                priority="high",
                category="credit",
                action_items=[
                    "File Form 8850 within 28 days of hire",
                    "Obtain state workforce agency certification",
                    "Complete Form 5884 with tax return",
                    "Maintain employee documentation"
                ],
                deadline="Within 28 days of each hire",
                confidence=0.95
            ))
            rec_id += 1
    
    # Retirement contribution recommendation
    if tax_data.income.wages_current_year > 50000:
        retirement_contribution = min(23000, tax_data.income.wages_current_year * 0.15)
        savings = retirement_contribution * 0.22
        
        recommendations.append(Recommendation(
            id=f"rec_{rec_id}",
            title="Maximize Retirement Contributions",
            description="Contributing to retirement accounts reduces taxable income while building wealth.",
            potential_savings=savings,
            priority="high",
            category="retirement",
            action_items=[
                f"Contribute ${retirement_contribution:,.0f} to 401(k)/IRA",
                "Set up automatic monthly contributions",
                "Consider employer match opportunities",
                "Review contribution limits annually"
            ],
            deadline="2024-12-31",
            confidence=0.85
        ))
        rec_id += 1
    
    # Quarterly payments recommendation
    if tax_summary.total_tax_liability > 1000:
        recommendations.append(Recommendation(
            id=f"rec_{rec_id}",
            title="Make Quarterly Estimated Tax Payments",
            description="Avoid penalties by making timely quarterly estimated tax payments.",
            potential_savings=0,
            priority="high",
            category="estimated_payments",
            action_items=[
                "Calculate quarterly payment amounts",
                "Set up IRS Direct Pay",
                "Mark calendar for quarterly deadlines",
                "Adjust payments based on income changes"
            ],
            deadline="Q1: Apr 15, Q2: Jun 15, Q3: Sep 15, Q4: Jan 15",
            confidence=1.0
        ))
        rec_id += 1
    
    # Business structure recommendation
    if tax_data.income.business_net_profit > 50000:
        se_tax_current = calculate_self_employment_tax(tax_data.income.business_net_profit)
        estimated_savings = se_tax_current * 0.4
        
        recommendations.append(Recommendation(
            id=f"rec_{rec_id}",
            title="Consider S-Corporation Election",
            description="An S-Corp election could reduce self-employment taxes on business profits.",
            potential_savings=estimated_savings,
            priority="medium",
            category="business_structure",
            action_items=[
                "Consult with tax advisor about S-Corp benefits",
                "Calculate potential SE tax savings",
                "File Form 2553 if beneficial",
                "Set up reasonable salary structure"
            ],
            deadline="March 15 for current year election",
            confidence=0.7
        ))
        rec_id += 1
    
    # AI Insights
    ai_insights = AIInsights(
        key_findings=[
            f"Total income of ${tax_summary.total_income:,.0f} places you in strong financial position",
            f"Current effective tax rate is {tax_summary.effective_tax_rate:.1f}%",
            f"Multiple tax-saving opportunities identified"
        ],
        risks=[
            "Ensure all income is properly reported",
            "Keep detailed records for all deductions",
            "Stay current on quarterly estimated payments"
        ],
        opportunities=[
            "Maximize retirement account contributions",
            "Optimize business structure for tax efficiency",
            "Consider additional tax-advantaged accounts (HSA, 529)"
        ]
    )
    
    return recommendations, ai_insights


# ==================== DATABASE OPERATIONS ====================

async def save_analysis_to_db(
    user_id: str,
    tax_year: int,
    response,  # TaxAnalysisResponse
    tax_return_id: Optional[str] = None
) -> Optional[str]:
    """Save tax analysis to MongoDB"""
    try:
        db = Database.get_database()
        
        # Create document
        analysis_doc = TaxAnalysisDocument(
            user_id=user_id,
            tax_year=tax_year,
            summary=response.summary.dict(),
            recommendations=[rec.dict() for rec in response.recommendations],
            scenarios=[scenario.dict() for scenario in response.scenarios],
            ai_insights=response.ai_insights.dict(),
            quarterly_estimates=response.quarterly_estimates.dict(),
            processing_metadata=response.processing_metadata.dict(),
            tax_return_id=tax_return_id
        )
        
        # Insert into database
        result = await db.tax_analyses.insert_one(
            model_to_dict(analysis_doc)
        )
        
        logger.info(f"Saved analysis to database: {result.inserted_id}")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error saving analysis to database: {e}")
        return None

# ==================== API ENDPOINTS ====================

@app.post("/api/v1/planning/analyze", response_model=TaxAnalysisResponse)
async def analyze_tax_situation(request: TaxAnalysisRequest):
    """Analyze tax situation and generate personalized recommendations"""
    try:
        start_time = datetime.utcnow()
        logger.info(f"Starting tax analysis for user: {request.user_id}")
        logger.info(f"Tax year: {request.tax_year}")
        
        # Calculate tax summary
        total_income = (
            request.tax_data.income.wages_current_year +
            request.tax_data.income.business_net_profit
        )
        
        # Calculate deductions
        total_deductions = 14600 if request.tax_data.personal_info.marital_status != "married" else 29200
        
        # Add home office deduction
        if request.tax_data.deductions and request.tax_data.deductions.home_office:
            if request.tax_data.deductions.home_office.works_from_home:
                simplified, actual = calculate_home_office_deduction(
                    request.tax_data.deductions.home_office.home_square_footage,
                    request.tax_data.deductions.home_office.office_square_footage
                )
                total_deductions += max(simplified, actual)
        
        # SE tax deduction
        if request.tax_data.income.business_net_profit > 0:
            se_tax = calculate_self_employment_tax(request.tax_data.income.business_net_profit)
            total_deductions += se_tax * 0.5
        
        taxable_income = max(0, total_income - total_deductions)
        
        # Calculate federal tax
        filing_status = "married_joint" if request.tax_data.personal_info.marital_status == "married" else "single"
        federal_tax = calculate_federal_tax(taxable_income, filing_status)
        
        # Add SE tax
        se_tax = 0
        if request.tax_data.income.business_net_profit > 0:
            se_tax = calculate_self_employment_tax(request.tax_data.income.business_net_profit)
        
        # Calculate credits
        total_credits = 0
        
        if request.tax_data.credits and request.tax_data.credits.wotc:
            wotc_credit = calculate_wotc_credit(request.tax_data.credits.wotc)
            total_credits += wotc_credit
        
        if request.tax_data.dependents and request.tax_data.dependents.has_children:
            ctc = calculate_child_tax_credit(
                request.tax_data.dependents.num_dependents,
                total_income
            )
            total_credits += ctc
        
        total_tax_liability = max(0, federal_tax + se_tax - total_credits)
        effective_tax_rate = (total_tax_liability / total_income * 100) if total_income > 0 else 0
        
        tax_summary = TaxSummary(
            total_income=total_income,
            total_deductions=total_deductions,
            total_credits=total_credits,
            taxable_income=taxable_income,
            total_tax_liability=total_tax_liability,
            effective_tax_rate=effective_tax_rate
        )
        
        logger.info(f"Tax summary: ${total_tax_liability:,.2f} liability")
        
        # Generate AI recommendations
        recommendations, ai_insights = generate_ai_recommendations(request.tax_data, tax_summary)
        
        total_potential_savings = sum(rec.potential_savings for rec in recommendations)
        logger.info(f"Total potential savings: ${total_potential_savings:,.2f}")
        
        # Create scenarios
        baseline_scenario = TaxScenario(
            name="Current Situation (Baseline)",
            description="Your current tax situation with no changes",
            tax_liability=total_tax_liability,
            effective_rate=effective_tax_rate,
            changes=[]
        )
        
        optimized_tax = max(0, total_tax_liability - total_potential_savings)
        optimized_rate = (optimized_tax / total_income * 100) if total_income > 0 else 0
        
        optimized_scenario = TaxScenario(
            name="Optimized Strategy (Recommended)",
            description="Implementing all recommended tax strategies",
            tax_liability=optimized_tax,
            effective_rate=optimized_rate,
            changes=[rec.title for rec in recommendations[:5]],
            savings=total_potential_savings
        )
        
        scenarios = [baseline_scenario, optimized_scenario]
        
        # Calculate quarterly estimates
        quarterly_amount = total_tax_liability / 4
        quarterly_estimates = QuarterlyEstimates(
            q1=quarterly_amount,
            q2=quarterly_amount,
            q3=quarterly_amount,
            q4=quarterly_amount,
            total=total_tax_liability
        )
        
        # Create response
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        response = TaxAnalysisResponse(
            success=True,
            user_id=request.user_id,
            tax_year=request.tax_year,
            summary=tax_summary,
            recommendations=recommendations,
            scenarios=scenarios,
            ai_insights=ai_insights,
            quarterly_estimates=quarterly_estimates,
            processing_metadata=ProcessingMetadata(
                processing_time_seconds=processing_time,
                ai_model="gemini-2.0-flash-exp",
                optimization_level=request.options.optimization_level,
                total_potential_savings=total_potential_savings
            ),
            timestamp=end_time.isoformat()
        )
        logger.info(f"Analysis completed successfully in {processing_time:.2f}s")
        
        # Save to database
        analysis_id = await save_analysis_to_db(
            request.user_id,
            request.tax_year,
            response
        )
        
        if analysis_id:
            logger.info(f"Analysis saved to MongoDB with ID: {analysis_id}")
    
        return response
        
    except Exception as e:
        logger.error(f"Error in tax analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing tax situation: {str(e)}"
        )


@app.get("/api/v1/planning/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "tax-planning",
        "version": "1.0.0",
        "ai_model": "gemini-2.0-flash-exp",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI-Driven Tax Planning Service",
        "version": "1.0.0",
        "ai_model": "Gemini Flash 2.5",
        "endpoints": {
            "analyze": "/api/v1/planning/analyze",
            "health": "/api/v1/planning/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Tax Planning Service with Gemini Flash 2.5 on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)