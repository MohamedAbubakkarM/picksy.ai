from crewai.tools import BaseTool
from typing import Type, List, Dict, Optional
from pydantic import BaseModel, Field
from schemas.models import llm
from tools.Tavilyphase2 import TavilySearchTool
import re
from urllib.parse import urlparse
from datetime import datetime
import json

from schemas.models import DealAnalysis, DealFinderInput, DealFindingOutput


tavily = TavilySearchTool()



class EnhancedDealFinder(BaseTool):
    name: str = "Enhanced Deal Finding Tool"
    description: str = "Comprehensive deal finder with analysis, comparison, and location-specific insights"
    args_schema: Type[BaseModel] = DealFinderInput

    def _run(self, product_name: str, location: str = "India", max_results: int = 5,
             budget_range: str = None) -> str:
        try:
            deals_data = self._search_deals(product_name, location)
            if not deals_data:
                return self._create_no_results_response(product_name, location)

            analyzed_deals = self._analyze_deals(deals_data, product_name, location, budget_range)
            if not analyzed_deals:
                return self._create_no_results_response(product_name, location)

            filtered_deals = self._filter_and_rank_deals(analyzed_deals, product_name, max_results)

            analysis = self._generate_analysis(filtered_deals)
            recommendations = self._generate_recommendations(filtered_deals)

            search_summary = {
                "product_searched": product_name,
                "location": location,
                "search_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_deals_found": len(filtered_deals),
            }

            notes = self._generate_notes(filtered_deals, product_name, location)

            internal_fields = {"match_score", "price_numeric", "review_count"}
            output = {
                "summary": search_summary,
                "deals": [deal.model_dump(exclude=internal_fields) for deal in filtered_deals],
                "analysis": analysis,
                "recommendations": recommendations,
                "notes": notes,
            }
            validated = DealFindingOutput(**output)
            return validated.model_dump_json()

        except Exception as e:
            return f"Error occurred while searching for deals: {str(e)}"

    def _create_no_results_response(self, product_name: str, location: str) -> str:
        return f"""# Product Search Summary
                - **Product searched**: {product_name}
                - **Location**: {location}
                - **Search date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                - **Total deals found**: 0

                **No deals found for "{product_name}" in {location}.**

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
        all_results = []

        search_queries = [
            f"{product_name} buy online amazon flipkart price",
            f"{product_name} deals discount offers india",
            f"site:amazon.in {product_name} price",
            f"site:flipkart.com {product_name} price"
        ]

        for query in search_queries:
            try:
                result = tavily.run(query)

                if hasattr(result, 'response') and result.response:
                    all_results.extend(result.response)
                elif hasattr(result, 'results') and result.results:
                    all_results.extend(result.results)
                elif isinstance(result, list):
                    all_results.extend(result)
                elif isinstance(result, dict) and 'results' in result:
                    all_results.extend(result['results'])

            except Exception:
                continue

        unique_results = []
        seen_urls = set()
        for result in all_results:
            if isinstance(result, dict):
                url = result.get('url', '')
                if url and url not in seen_urls:
                    unique_results.append(result)
                    seen_urls.add(url)

        return unique_results

    def _analyze_deals(self, deals_data: List[Dict], product_name: str, location: str, budget_range: str = None) -> \
    List[DealAnalysis]:
        analyzed_deals = []

        for deal in deals_data:
            try:
                analysis = self._analyze_single_deal(deal, product_name, location, budget_range)
                if analysis:
                    analyzed_deals.append(analysis)
            except Exception:
                continue

        return analyzed_deals

    def _analyze_single_deal(self, deal: Dict, product_name: str, location: str, budget_range: str = None) -> Optional[
        DealAnalysis]:
        url = deal.get('url', '')
        title = deal.get('title', '')
        content = deal.get('content', '') or deal.get('snippet', '')

        if not url or not title:
            return None

        platform = 'Unknown'
        if 'amazon' in url.lower():
            platform = 'Amazon.in'
        elif 'flipkart' in url.lower():
            platform = 'Flipkart.com'
        else:
            return None

        match_score = self._calculate_match_score(title + ' ' + content, product_name)
        if match_score < 0.4:
            return None

        price_info = self._extract_comprehensive_price_info(content, title)

        if budget_range and price_info['price_numeric'] != float('inf'):
            if not self._fits_budget(price_info['price_numeric'], budget_range):
                return None

        product_info = self._extract_product_info(content, title, platform)

        why_bits = []
        if price_info['discount_percentage']:
            why_bits.append(f"{price_info['discount_percentage']} off")
        if product_info['availability'] == 'In Stock':
            why_bits.append("in stock now")
        if product_info['rating']:
            why_bits.append(f"rated {product_info['rating']}")
        if not why_bits:
            why_bits.append(f"listed on {platform}")
        why_recommended = ", ".join(why_bits).capitalize()

        return DealAnalysis(
            product_title=title or product_name,
            price=price_info['current_price'],
            original_price=price_info['original_price'],
            discount=price_info['discount_percentage'],
            platform=platform,
            direct_link=url,
            seller=product_info['seller_info'],
            seller_rating=product_info['rating'],
            availability=product_info['availability'],
            delivery=product_info['delivery_info'],
            key_features=product_info['features'],
            why_recommended=why_recommended,
            review_count=product_info['review_count'],
            match_score=match_score,
            price_numeric=price_info['price_numeric']
        )

    def _extract_comprehensive_price_info(self, content: str, title: str) -> Dict:
        text = (content + ' ' + title).lower()

        price_info = {
            'current_price': 'Price not available',
            'original_price': None,
            'discount_percentage': None,
            'price_numeric': float('inf')
        }

        price_patterns = [
            r'₹\s*[\d,]+(?:\.\d{2})?',
            r'rs\.?\s*[\d,]+(?:\.\d{2})?',
            r'price:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'cost:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'mrp:?\s*₹?\s*[\d,]+(?:\.\d{2})?',
            r'\b[\d,]+(?:\.\d{2})?\s*rupees?\b'
        ]

        all_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                numeric_price = self._extract_numeric_from_price(match)
                if numeric_price and 10 <= numeric_price <= 1000000:
                    all_prices.append(numeric_price)

        if all_prices:
            all_prices = sorted(list(set(all_prices)))

            current_price = min(all_prices)
            price_info['current_price'] = f"₹{current_price:,.0f}"
            price_info['price_numeric'] = current_price

            if len(all_prices) > 1:
                original_price = max(all_prices)
                if original_price > current_price * 1.1:
                    price_info['original_price'] = f"₹{original_price:,.0f}"
                    discount = ((original_price - current_price) / original_price) * 100
                    price_info['discount_percentage'] = f"{discount:.0f}%"

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
                if 1 <= discount_val <= 90:
                    price_info['discount_percentage'] = f"{discount_val}%"
                    break

        return price_info

    def _extract_product_info(self, content: str, title: str, platform: str) -> Dict:
        text = (content + ' ' + title).lower()

        info = {
            'seller_info': None,
            'availability': 'Check availability',
            'delivery_info': None,
            'features': None,
            'rating': None,
            'review_count': None
        }

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

        if len(title) > 20:
            feature_words = ['gb', 'tb', 'inch', 'mp', 'ghz', 'core', 'ram', 'storage']
            features = []
            title_words = title.lower().split()
            for i, word in enumerate(title_words):
                if any(fw in word for fw in feature_words):
                    context = ' '.join(title_words[max(0, i - 1):i + 2])
                    features.append(context)

            if features:
                info['features'] = ', '.join(features[:3])

        return info

    def _calculate_match_score(self, text: str, product_name: str) -> float:
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

        if product_name.lower() in text_lower:
            matched_words += 1

        return min(matched_words / len(product_words), 1.0)

    def _fits_budget(self, price: float, budget_range: str) -> bool:
        try:
            if '-' in budget_range:
                min_budget, max_budget = map(float, budget_range.split('-'))
                return min_budget <= price <= max_budget
            else:
                max_budget = float(budget_range)
                return price <= max_budget
        except:
            return True

    def _filter_and_rank_deals(self, deals: List[DealAnalysis], product_name: str, max_results: int) -> List[
        DealAnalysis]:
        filtered_deals = [deal for deal in deals if deal.match_score >= 0.3]

        if not filtered_deals:
            filtered_deals = sorted(deals, key=lambda x: x.match_score, reverse=True)[:max_results]

        def sort_key(deal):
            availability_score = 3 if deal.availability == 'In Stock' else 1 if deal.availability == 'Limited Stock' else 0
            price_score = 1 / (deal.price_numeric + 1) if deal.price_numeric != float('inf') else 0
            return (deal.match_score, availability_score, price_score)

        filtered_deals.sort(key=sort_key, reverse=True)
        return filtered_deals[:max_results]

    def _short_title(self, title: str, limit: int = 50) -> str:
        return title[:limit] + "..." if len(title) > limit else title

    def _generate_analysis(self, deals: List[DealAnalysis]) -> Dict:
        analysis = {
            "best_overall_value": None,
            "fastest_delivery": None,
            "highest_discount": None,
            "most_trusted_seller": None,
        }
        if not deals:
            return analysis

        priced_deals = [d for d in deals if d.price_numeric != float('inf')]

        if priced_deals:
            best_value = min(priced_deals, key=lambda x: x.price_numeric)
            analysis["best_overall_value"] = (
                f"{self._short_title(best_value.product_title)} on {best_value.platform} at {best_value.price}"
            )

        discount_deals = [d for d in deals if d.discount]
        if discount_deals:
            top = max(discount_deals, key=lambda x: float(x.discount.rstrip('%')))
            analysis["highest_discount"] = (
                f"{self._short_title(top.product_title)} on {top.platform} — {top.discount} off"
            )

        delivery_deals = [d for d in deals if d.delivery]
        if delivery_deals:
            first = delivery_deals[0]
            analysis["fastest_delivery"] = (
                f"{self._short_title(first.product_title)} on {first.platform} — {first.delivery}"
            )

        rated_deals = [d for d in deals if d.seller_rating]
        if rated_deals:
            top_rated = max(rated_deals, key=lambda x: float(x.seller_rating.split('/')[0]))
            analysis["most_trusted_seller"] = (
                f"{self._short_title(top_rated.product_title)} on {top_rated.platform} — {top_rated.seller_rating}"
            )

        return analysis

    def _generate_recommendations(self, deals: List[DealAnalysis]) -> str:
        if not deals:
            return "No suitable deals found."

        priced_deals = [d for d in deals if d.price_numeric != float('inf')]
        available_deals = [d for d in priced_deals if d.availability == 'In Stock']

        parts = []
        if available_deals:
            best_deal = available_deals[0]
            parts.append(
                f"Top pick: {self._short_title(best_deal.product_title)} on {best_deal.platform} "
                f"at {best_deal.price} — best overall value with confirmed availability."
            )
            if len(available_deals) > 1:
                cheapest = min(available_deals, key=lambda x: x.price_numeric)
                if cheapest is not best_deal:
                    parts.append(
                        f"Budget option: {self._short_title(cheapest.product_title)} on {cheapest.platform} "
                        f"at {cheapest.price}."
                    )
        elif priced_deals:
            best_deal = priced_deals[0]
            parts.append(
                f"Best match found: {self._short_title(best_deal.product_title)} on {best_deal.platform} "
                f"at {best_deal.price}. Verify availability before ordering."
            )
        else:
            parts.append("No products with valid pricing were found; check the retailer sites directly.")

        return " ".join(parts)

    def _generate_notes(self, deals: List[DealAnalysis], product_name: str, location: str) -> str:
        notes: List[str] = []

        if not deals:
            notes.append(f"No deals found for '{product_name}' on Amazon.in or Flipkart.com")
            notes.append("Try using more specific product names or check spelling")
            return "\n".join(notes)

        in_stock_count = len([d for d in deals if d.availability == 'In Stock'])
        if in_stock_count == 0:
            notes.append("No products currently showing as 'In Stock' - availability may vary")
        elif in_stock_count < len(deals):
            notes.append(f"{in_stock_count} out of {len(deals)} products appear to be in stock")

        prices = [d.price_numeric for d in deals if d.price_numeric != float('inf')]
        if len(prices) > 1:
            min_price, max_price = min(prices), max(prices)
            notes.append(f"Price range: Rs.{min_price:,.0f} - Rs.{max_price:,.0f}")

        discount_deals = [d for d in deals if d.discount]
        if discount_deals:
            discounts = [float(d.discount.rstrip('%')) for d in discount_deals]
            notes.append(f"Discounts available up to {max(discounts):.0f}% off")

        amazon_count = len([d for d in deals if 'amazon' in d.platform.lower()])
        flipkart_count = len([d for d in deals if 'flipkart' in d.platform.lower()])

        if amazon_count > 0 and flipkart_count > 0:
            notes.append(f"Found on both platforms: {amazon_count} Amazon deals, {flipkart_count} Flipkart deals")
        elif amazon_count > 0:
            notes.append("Deals found only on Amazon.in")
        elif flipkart_count > 0:
            notes.append("Deals found only on Flipkart.com")

        notes.append("Always verify current price and availability on the retailer's website")
        notes.append("Check seller ratings and return policies before purchasing")

        return "\n".join(notes)

    def _extract_numeric_from_price(self, price_str: str) -> Optional[float]:
        try:
            cleaned = re.sub(r'[₹,\s]', '', str(price_str))
            numeric_match = re.search(r'[\d.]+', cleaned)
            if numeric_match:
                return float(numeric_match.group())
        except:
            pass
        return None