from crewai import Task
from ..models.LLM import llm
from ..tools.DealFinder import EnhancedDealFinder
from ..agents.DealFinderAgent import deal_finder_agent
from ..models.DealFindingOutput import DealFindingOutput

deal_finder_tool = EnhancedDealFinder()

deal_finding_task = Task(
    description="""
    Use the Enhanced Deal Finding Tool to search for the best deals for the requested product.

    Search Parameters:
    - Product: {product_name}
    - Location: {location}
    - Maximum results: 5

    Your task is to:
    1. Use the deal finder tool to search for available deals
    2. Analyze the results comprehensively
    3. Provide structured insights and recommendations

    CRITICAL OUTPUT REQUIREMENTS:
    - MUST return ONLY raw JSON - no markdown formatting, no backticks, no code blocks
    - NO ```json or ``` wrapper - just pure JSON starting with { and ending with }
    - The JSON must be valid and parseable
    - Must match the DealFindingOutput schema exactly
    - All string fields must be properly quoted
    - All array elements must be properly separated by commas
    - No trailing commas allowed

    ANALYSIS REQUIREMENTS:
    - Compare prices across all platforms and identify the best value
    - Calculate discount percentages where original prices are available
    - Evaluate delivery options and identify the fastest available
    - Assess seller reliability based on ratings and platform reputation
    - Reference specific deals by their position (Deal #1, Deal #2, etc.) in your analysis

    RECOMMENDATION GUIDELINES:
    - Provide specific, actionable advice based on the actual deals found
    - Consider different buyer priorities: budget-conscious, speed of delivery, brand preference
    - Avoid generic recommendations like "check Amazon or Flipkart"
    - Base recommendations on concrete factors: price differences, seller ratings, delivery times
    - The "recommendations" field must be a single string, not an array

    IMPORTANT NOTES:
    - Include working direct links to each product deal page
    - If original prices aren't available, set them as null (not "null" string)
    - If discount information isn't available, set as null (not "null" string)
    - Ensure all seller ratings are captured accurately
    - Today's date should be used for search_date in YYYY-MM-DD format
    - All numeric values in analysis section should be strings
    - Ensure proper JSON escaping for any quotes within strings
    """,
    expected_output="""
    Raw JSON output matching this exact structure (no markdown formatting):
    {
      "summary": {
        "product_searched": "string",
        "location": "string", 
        "search_date": "2025-06-20",
        "total_deals_found": 5
      },
      "deals": [
        {
          "platform": "string",
          "product_title": "string",
          "price": "string",
          "original_price": "string or null",
          "discount": "string or null", 
          "direct_link": "string",
          "seller": "string",
          "seller_rating": "string",
          "availability": "string",
          "delivery": "string",
          "key_features": "string",
          "why_recommended": "string"
        }
      ],
      "analysis": {
        "best_overall_value": "string",
        "fastest_delivery": "string", 
        "highest_discount": "string",
        "most_trusted_seller": "string"
      },
      "recommendations": "string (single string, not array)",
      "notes": "string"
    }
    """,
    tools=[deal_finder_tool],
    agent=deal_finder_agent,
    context=None,
    config=None,
    human_input=False,
    async_execution=False,
    callback=None,
    dependencies=[],
    output_pydantic=DealFindingOutput,
)