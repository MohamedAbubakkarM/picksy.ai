from crewai.tools import BaseTool
from typing import Type, List, Dict, Optional
from pydantic import BaseModel, Field
from picksyai.models.LLM import llm
from ..tools.Tavilyphase2 import TavilySearchTool
import re
from urllib.parse import urlparse
from datetime import datetime
import json
from ..models.DealFindingOutput import DealFindingOutput

tavily = TavilySearchTool()


class DealFinderInput(BaseModel):
    product_name: str = Field(..., description='Exact product name to find deals for')
    location: str = Field(..., description='User location (city, state, or pincode)')
    max_results: int = Field(default=5, description='Maximum number of deals to return')
    budget_range: Optional[str] = Field(None, description='Budget range like "1000-5000" (optional)')


class DealAnalysis(BaseModel):
    product_title: str = Field(..., description="Full product title as listed")
    price: str = Field(..., description="Current price")
    original_price: Optional[str] = Field(None, description="Original price if available")
    discount_percentage: Optional[str] = Field(None, description="Discount percentage if available")
    platform: str = Field(..., description="Amazon.in or Flipkart.com")
    product_url: str = Field(..., description="Direct purchase link")
    seller_info: Optional[str] = Field(None, description="Seller name and rating")
    availability_status: str = Field(..., description="In stock/Limited stock/Out of stock")
    delivery_info: Optional[str] = Field(None, description="Estimated delivery time")
    key_features: Optional[str] = Field(None, description="Brief product highlights")
    rating: Optional[str] = Field(None, description="Product rating")
    review_count: Optional[str] = Field(None, description="Number of reviews")
    match_score: float = Field(..., description="How well product matches search (0-1)")
    price_numeric: float = Field(..., description="Numeric price for sorting")


class EnhancedDealFinder(BaseTool):
    name: str = "Enhanced Deal Finding Tool"
    description: str = "Comprehensive deal finder with analysis, comparison, and location-specific insights"
    args_schema: Type[BaseModel] = DealFinderInput

    def _run(self, product_name: str, location: str = "India", max_results: int = 5,
             budget_range: str = None) -> str:
        """Main execution method with comprehensive deal analysis"""

        try:
            print(f"Starting deal search for: {product_name} in {location}")

            # Search for deals
            deals_data = self._search_deals(product_name, location)
            print(f"Found {len(deals_data)} raw search results")

            if not deals_data:
                return self._create_no_results_response(product_name, location)

            # Process and analyze deals
            analyzed_deals = self._analyze_deals(deals_data, product_name, location, budget_range)
            print(f"Analyzed {len(analyzed_deals)} deals")

            if not analyzed_deals:
                return self._create_no_results_response(product_name, location)

            # Filter and rank deals
            filtered_deals = self._filter_and_rank_deals(analyzed_deals, product_name, max_results)
            print(f"Filtered to {len(filtered_deals)} best deals")

            # Generate analysis and recommendations
            analysis = self._generate_analysis(filtered_deals)
            recommendations = self._generate_recommendations(filtered_deals)

            # Create search summary
            search_summary = {
                "product_searched": product_name,
                "location": location,
                "search_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_deals_found": len(filtered_deals),
                "budget_filter": budget_range
            }

            # Generate important notes
            notes = self._generate_notes(filtered_deals, product_name, location)

            output = {
                "summary": search_summary,
                "deals": [deal.dict() for deal in filtered_deals],
                "analysis": analysis,
                "recommendations": recommendations,
                "notes": notes
            }
            validated = DealFindingOutput(**output)
            return validated.model_dump()

        except Exception as e:
            print(f"Error in deal finder: {str(e)}")
            return f"Error occurred while searching for deals: {str(e)}"

    def _create_no_results_response(self, product_name: str, location: str) -> str:
        """Create a response when no deals are found"""
        return f"""# 🔍 Product Search Summary
- **Product searched**: {product_name}
- **Location**: {location}
- **Search date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Total deals found**: 0

❌ **No deals found for "{product_name}" in {location}.**

## Possible Reasons:
- Product may be out of stock on Amazon.in and Flipkart.com
- Product name may need to be more specific
- Product may not be available in your region
- Temporary server issues

## Suggestions:
- Try a more specific product name with brand and model
- Check the spelling of the product name
- Try searching for similar products
- Visit the websites directly to verify availability
"""


    def _search_deals(self, product_name: str, location: str) -> List[Dict]:
        """Enhanced search strategy for better results"""
        all_results = []

        # Multiple search strategies
        search_queries = [
            f"{product_name} buy online amazon flipkart price",
            f"{product_name} deals discount offers india",
            f"site:amazon.in {product_name} price",
            f"site:flipkart.com {product_name} price"
        ]

        for query in search_queries:
            try:
                print(f"Searching with query: {query}")
                result = tavily.run(query)

                # Handle different response formats
                if hasattr(result, 'response') and result.response:
                    all_results.extend(result.response)
                elif hasattr(result, 'results') and result.results:
                    all_results.extend(result.results)
                elif isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, dict) and 'results' in result:
                    all_results.extend(result['results'])

            except Exception as e:
                print(f"Search query failed: {query} - {e}")
                continue

        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()
        for result in all_results:
            if isinstance(result, dict):
                url = result.get('url', '')
                if url and url not in seen_urls:
                    unique_results.append(result)
                    seen_urls.add(url)

        print(f"Found {len(unique_results)} unique results")
        return unique_results

    def _analyze_deals(self, deals_data: List[Dict], product_name: str, location: str, budget_range: str = None) -> \
    List[DealAnalysis]:
        """Comprehensive deal analysis"""
        analyzed_deals = []

        for deal in deals_data:
            try:
                analysis = self._analyze_single_deal(deal, product_name, location, budget_range)
                if analysis:
                    analyzed_deals.append(analysis)
            except Exception as e:
                print(f"Failed to analyze deal: {e}")
                continue

        return analyzed_deals

    def _analyze_single_deal(self, deal: Dict, product_name: str, location: str, budget_range: str = None) -> Optional[
        DealAnalysis]:
        """Analyze a single deal comprehensively"""

        url = deal.get('url', '')
        title = deal.get('title', '')
        content = deal.get('content', '') or deal.get('snippet', '')

        if not url or not title:
            return None

        # Extract platform
        platform = 'Unknown'
        if 'amazon' in url.lower():
            platform = 'Amazon.in'
        elif 'flipkart' in url.lower():
            platform = 'Flipkart.com'
        else:
            return None  # Skip non-target platforms

        # Calculate match score
        match_score = self._calculate_match_score(title + ' ' + content, product_name)
        if match_score < 0.4:  # Lowered threshold for better results
            return None

        # Extract price information
        price_info = self._extract_comprehensive_price_info(content, title)

        # Apply budget filter if specified
        if budget_range and price_info['price_numeric'] != float('inf'):
            if not self._fits_budget(price_info['price_numeric'], budget_range):
                return None

        # Extract additional product information
        product_info = self._extract_product_info(content, title, platform)

        return DealAnalysis(
            product_title=title or product_name,
            price=price_info['current_price'],
            original_price=price_info['original_price'],
            discount_percentage=price_info['discount_percentage'],
            platform=platform,
            product_url=url,
            seller_info=product_info['seller_info'],
            availability_status=product_info['availability'],
            delivery_info=product_info['delivery_info'],
            key_features=product_info['features'],
            rating=product_info['rating'],
            review_count=product_info['review_count'],
            match_score=match_score,
            price_numeric=price_info['price_numeric']
        )

    def _extract_comprehensive_price_info(self, content: str, title: str) -> Dict:
        """Extract detailed price information"""
        text = (content + ' ' + title).lower()

        price_info = {
            'current_price': 'Price not available',
            'original_price': None,
            'discount_percentage': None,
            'price_numeric': float('inf')
        }

        # Enhanced price patterns
        price_patterns = [
            r'₹\s*[\d,]+(?:\.\d{2})?',
            r'rs\.?\s*[\d,]+(?:\.\d{2})?',
            r'price:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'cost:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'mrp:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'\b[\d,]+(?:\.\d{2})?\s*rupees?\b'
        ]

        # Find all price matches
        all_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                numeric_price = self._extract_numeric_from_price(match)
                if numeric_price and 10 <= numeric_price <= 1000000:  # Reasonable price range
                    all_prices.append(numeric_price)

        if all_prices:
            all_prices = sorted(list(set(all_prices)))  # Remove duplicates and sort

            # Current price is typically the lowest mentioned
            current_price = min(all_prices)
            price_info['current_price'] = f"₹{current_price:,.0f}"
            price_info['price_numeric'] = current_price

            # If multiple prices, highest might be original price
            if len(all_prices) > 1:
                original_price = max(all_prices)
                if original_price > current_price * 1.1:  # At least 10% difference
                    price_info['original_price'] = f"₹{original_price:,.0f}"
                    discount = ((original_price - current_price) / original_price) * 100
                    price_info['discount_percentage'] = f"{discount:.0f}%"

        # Look for explicit discount mentions
        discount_patterns = [
            r'(\d+)%\s*off',
            r'save\s*(\d+)%',
            r'discount:?\s*(\d+)%',
            r'(\d+)%\s*discount'
        ]

        for pattern in discount_patterns:
            matches = re.findall(pattern, text)
            if matches and not price_info['discount_percentage']:
                discount_val = int(matches[0])
                if 1 <= discount_val <= 90:  # Reasonable discount range
                    price_info['discount_percentage'] = f"{discount_val}%"
                    break

        return price_info

    def _extract_product_info(self, content: str, title: str, platform: str) -> Dict:
        """Extract additional product information"""
        text = (content + ' ' + title).lower()

        info = {
            'seller_info': None,
            'availability': 'Check availability',
            'delivery_info': None,
            'features': None,
            'rating': None,
            'review_count': None
        }

        # Availability status
        if any(phrase in text for phrase in ['in stock', 'available now', 'buy now', 'add to cart']):
            info['availability'] = 'In Stock'
        elif any(phrase in text for phrase in ['out of stock', 'unavailable', 'sold out', 'not available']):
            info['availability'] = 'Out of Stock'
        elif any(phrase in text for phrase in ['limited stock', 'few left', 'hurry', 'limited time']):
            info['availability'] = 'Limited Stock'

        # Rating extraction
        rating_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:out of\s*5|/5|\*|stars?)',
            r'rating:?\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*star'
        ]

        for pattern in rating_patterns:
            matches = re.findall(pattern, text)
            if matches:
                rating = float(matches[0])
                if 0 <= rating <= 5:
                    info['rating'] = f"{rating}/5"
                    break

        # Review count
        review_patterns = [
            r'(\d+(?:,\d+)*)\s*reviews?',
            r'(\d+(?:,\d+)*)\s*ratings?',
            r'rated by\s*(\d+(?:,\d+)*)',
            r'(\d+k?)\s*reviews?'
        ]

        for pattern in review_patterns:
            matches = re.findall(pattern, text)
            if matches:
                info['review_count'] = matches[0]
                break

        # Basic features from title
        if len(title) > 20:
            # Extract key features from title
            feature_words = ['gb', 'tb', 'inch', 'mp', 'ghz', 'core', 'ram', 'storage']
            features = []
            title_words = title.lower().split()
            for i, word in enumerate(title_words):
                if any(fw in word for fw in feature_words):
                    # Get context around the feature word
                    context = ' '.join(title_words[max(0, i - 1):i + 2])
                    features.append(context)

            if features:
                info['features'] = ', '.join(features[:3])  # Limit to 3 features

        return info

    def _calculate_match_score(self, text: str, product_name: str) -> float:
        """Calculate how well the product matches the search query"""
        if not text or not product_name:
            return 0.0

        text_lower = text.lower()
        product_words = [word for word in product_name.lower().split() if len(word) > 2]

        if not product_words:
            return 0.0

        matched_words = 0
        for word in product_words:
            if word in text_lower:
                matched_words += 1

        # Bonus for exact phrase match
        if product_name.lower() in text_lower:
            matched_words += 1

        return min(matched_words / len(product_words), 1.0)

    def _fits_budget(self, price: float, budget_range: str) -> bool:
        """Check if price fits within budget range"""
        try:
            if '-' in budget_range:
                min_budget, max_budget = map(float, budget_range.split('-'))
                return min_budget <= price <= max_budget
            else:
                max_budget = float(budget_range)
                return price <= max_budget
        except:
            return True  # If budget parsing fails, include the item

    def _filter_and_rank_deals(self, deals: List[DealAnalysis], product_name: str, max_results: int) -> List[
        DealAnalysis]:
        """Filter and rank deals by relevance and value"""

        # Filter deals with reasonable match scores
        filtered_deals = [deal for deal in deals if deal.match_score >= 0.3]

        if not filtered_deals:
            # If no good matches, return top deals anyway
            filtered_deals = sorted(deals, key=lambda x: x.match_score, reverse=True)[:max_results]

        # Sort by multiple criteria
        def sort_key(deal):
            availability_score = 3 if deal.availability_status == 'In Stock' else 1 if deal.availability_status == 'Limited Stock' else 0
            price_score = 1 / (deal.price_numeric + 1) if deal.price_numeric != float('inf') else 0
            return (deal.match_score, availability_score, price_score)

        filtered_deals.sort(key=sort_key, reverse=True)
        return filtered_deals[:max_results]

    def _generate_analysis(self, deals: List[DealAnalysis]) -> Dict:
        """Generate comparative analysis of deals"""
        if not deals:
            return {}

        analysis = {}

        # Filter deals with valid prices
        priced_deals = [d for d in deals if d.price_numeric != float('inf')]
        available_deals = [d for d in priced_deals if d.availability_status == 'In Stock']

        if priced_deals:
            # Best value (lowest price)
            best_value = min(priced_deals, key=lambda x: x.price_numeric)
            analysis['best_overall_value'] = {
                'product': best_value.product_title[:50] + "..." if len(
                    best_value.product_title) > 50 else best_value.product_title,
                'price': best_value.price,
                'platform': best_value.platform,
                'reason': f"Lowest price at {best_value.price}"
            }

            # Highest discount
            discount_deals = [d for d in priced_deals if d.discount_percentage]
            if discount_deals:
                highest_discount = max(discount_deals, key=lambda x: float(x.discount_percentage.rstrip('%')))
                analysis['highest_discount'] = {
                    'product': highest_discount.product_title[:50] + "..." if len(
                        highest_discount.product_title) > 50 else highest_discount.product_title,
                    'discount': highest_discount.discount_percentage,
                    'platform': highest_discount.platform,
                    'reason': f"Highest discount of {highest_discount.discount_percentage}"
                }

            # Best rated (if ratings available)
            rated_deals = [d for d in priced_deals if d.rating]
            if rated_deals:
                best_rated = max(rated_deals, key=lambda x: float(x.rating.split('/')[0]))
                analysis['highest_rated'] = {
                    'product': best_rated.product_title[:50] + "..." if len(
                        best_rated.product_title) > 50 else best_rated.product_title,
                    'rating': best_rated.rating,
                    'platform': best_rated.platform,
                    'reason': f"Highest rating of {best_rated.rating}"
                }

        return analysis

    def _generate_recommendations(self, deals: List[DealAnalysis]) -> Dict:
        """Generate specific purchase recommendations"""
        if not deals:
            return {'primary_recommendation': 'No suitable deals found'}

        recommendations = {}

        # Filter deals with valid prices
        priced_deals = [d for d in deals if d.price_numeric != float('inf')]
        available_deals = [d for d in priced_deals if d.availability_status == 'In Stock']

        if available_deals:
            # Primary recommendation (best deal overall)
            best_deal = available_deals[0]  # Already sorted by our criteria
            recommendations['primary_recommendation'] = {
                'product': best_deal.product_title[:50] + "..." if len(
                    best_deal.product_title) > 50 else best_deal.product_title,
                'price': best_deal.price,
                'platform': best_deal.platform,
                'url': best_deal.product_url,
                'reason': f"Best overall value at {best_deal.price} with good availability"
            }

            # Budget option (cheapest available)
            if len(available_deals) > 1:
                cheapest = min(available_deals, key=lambda x: x.price_numeric)
                if cheapest != best_deal:
                    recommendations['budget_option'] = {
                        'product': cheapest.product_title[:50] + "..." if len(
                            cheapest.product_title) > 50 else cheapest.product_title,
                        'price': cheapest.price,
                        'platform': cheapest.platform,
                        'reason': f"Most affordable option at {cheapest.price}"
                    }
        elif priced_deals:
            # If no in-stock items, recommend the best overall
            best_deal = priced_deals[0]
            recommendations['primary_recommendation'] = {
                'product': best_deal.product_title[:50] + "..." if len(
                    best_deal.product_title) > 50 else best_deal.product_title,
                'price': best_deal.price,
                'platform': best_deal.platform,
                'reason': f"Best match found at {best_deal.price} (check availability)"
            }
        else:
            recommendations['primary_recommendation'] = 'No products with valid pricing found'

        return recommendations

    def _generate_notes(self, deals: List[DealAnalysis], product_name: str, location: str) -> List[str]:
        """Generate important notes and warnings"""
        notes = []

        if not deals:
            notes.append(f"No deals found for '{product_name}' on Amazon.in or Flipkart.com")
            notes.append("Try using more specific product names or check spelling")
            return notes

        # Check availability
        in_stock_count = len([d for d in deals if d.availability_status == 'In Stock'])
        if in_stock_count == 0:
            notes.append("⚠️ No products currently showing as 'In Stock' - availability may vary")
        elif in_stock_count < len(deals):
            notes.append(f"📦 {in_stock_count} out of {len(deals)} products appear to be in stock")

        # Price range information
        prices = [d.price_numeric for d in deals if d.price_numeric != float('inf')]
        if len(prices) > 1:
            min_price, max_price = min(prices), max(prices)
            notes.append(f"💰 Price range: ₹{min_price:,.0f} - ₹{max_price:,.0f}")

        # Discount information
        discount_deals = [d for d in deals if d.discount_percentage]
        if discount_deals:
            discounts = [float(d.discount_percentage.rstrip('%')) for d in discount_deals]
            avg_discount = sum(discounts) / len(discounts)
            notes.append(f"🏷️ Discounts available up to {max(discounts):.0f}% off")

        # Platform distribution
        amazon_count = len([d for d in deals if 'amazon' in d.platform.lower()])
        flipkart_count = len([d for d in deals if 'flipkart' in d.platform.lower()])

        if amazon_count > 0 and flipkart_count > 0:
            notes.append(f"🛒 Found on both platforms: {amazon_count} Amazon deals, {flipkart_count} Flipkart deals")
        elif amazon_count > 0:
            notes.append("🛒 Deals found only on Amazon.in")
        elif flipkart_count > 0:
            notes.append("🛒 Deals found only on Flipkart.com")

        # General advice
        notes.append("💡 Always verify current price and availability on the retailer's website")
        notes.append("🔒 Check seller ratings and return policies before purchasing")

        return notes

    def _extract_numeric_from_price(self, price_str: str) -> Optional[float]:
        """Extract numeric value from price string"""
        try:
            # Remove currency symbols and clean up
            cleaned = re.sub(r'[₹,\s]', '', str(price_str))
            # Extract just the numeric part
            numeric_match = re.search(r'[\d.]+', cleaned)
            if numeric_match:
                return float(numeric_match.group())
        except:
            pass
        return None