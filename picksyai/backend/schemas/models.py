import os
from pydantic import BaseModel, Field
from typing import Optional, List

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

llm = LLM(
    model=os.getenv("OPENROUTER_MODEL"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.2,
)


class DealFinderInput(BaseModel):
    product_name: str = Field(..., description='Exact product name to find deals for')
    location: str = Field(..., description='User location (city, state, or pincode)')
    max_results: int = Field(default=5, description='Maximum number of deals to return')
    budget_range: Optional[str] = Field(None, description='Budget range like "1000-5000" (optional)')


class DealAnalysis(BaseModel):
    product_title: str = Field(..., description="Full product title as listed")
    price: str = Field(..., description="Current price")
    original_price: Optional[str] = Field(None, description="Original price if available")
    discount: Optional[str] = Field(None, description="Discount percentage if available")
    platform: str = Field(..., description="Amazon.in or Flipkart.com")
    direct_link: str = Field(..., description="Direct purchase link")
    seller: Optional[str] = Field(None, description="Seller name")
    seller_rating: Optional[str] = Field(None, description="Product rating")
    availability: str = Field(..., description="In stock/Limited stock/Out of stock")
    delivery: Optional[str] = Field(None, description="Estimated delivery time")
    key_features: Optional[str] = Field(None, description="Brief product highlights")
    why_recommended: Optional[str] = Field(None, description="Why this deal is worth surfacing")
    review_count: Optional[str] = Field(None, description="Number of reviews")
    match_score: float = Field(..., description="How well product matches search (0-1)")
    price_numeric: float = Field(..., description="Numeric price for sorting")


class DealSummary(BaseModel):
    product_searched: str
    location: str
    search_date: str
    total_deals_found: int


class Deal(BaseModel):
    platform: str
    product_title: str
    price: str
    original_price: Optional[str] = None
    discount: Optional[str] = None
    direct_link: str
    seller: Optional[str] = None
    seller_rating: Optional[str] = None
    availability: str
    delivery: Optional[str] = None
    key_features: Optional[str] = None
    why_recommended: Optional[str] = None


class DealAnalysisSummary(BaseModel):
    best_overall_value: Optional[str] = None
    fastest_delivery: Optional[str] = None
    highest_discount: Optional[str] = None
    most_trusted_seller: Optional[str] = None


class DealFindingOutput(BaseModel):
    summary: DealSummary
    deals: List[Deal] = Field(default_factory=list)
    analysis: DealAnalysisSummary = Field(default_factory=DealAnalysisSummary)
    recommendations: str
    notes: str