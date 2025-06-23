from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import requests

TAVILY_CLIENT_API_KEY = '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'


class TavilyInput(BaseModel):
    query: str = Field(..., description="Input query for Tavily tool")


class TavilyOutput(BaseModel):
    response: list = Field(..., description="Products extracted by Tavily")


class TavilySearchTool(BaseTool):
    name: str = 'Tavily Search tool'
    description: str = 'Useful to fetch real-time ecommerce data from the web like product prices, URLs, and so on'
    args_schema: Type[BaseModel] = TavilyInput
    return_schema: Type[BaseModel] = TavilyOutput

    def _run(self, query: str) -> TavilyOutput:
        response = requests.post(
            'https://api.tavily.com/search',
            headers={'Authorization': f"Bearer {TAVILY_CLIENT_API_KEY}"},
            json={
                'query': query,
                'search_depth': 'advanced',
                'include_answer': True,
                'include_raw_content': True,
                'max_results': 15,
                'include_domains': ['amazon.in', 'flipkart.com'],
                'include_images': False,
            }
        )

        if response.status_code != 200:
            return TavilyOutput(response=[])

        data = response.json()
        results = data.get('results', [])

        final = []
        for result in results:
            url = result.get('url')
            title = result.get('title', '')
            content = result.get('content', '')
            raw_content = result.get('raw_content', '')

            if not url:
                continue

            site = ''
            if 'flipkart' in url.lower():
                site = 'flipkart.com'
            elif 'amazon' in url.lower():
                site = 'amazon.in'
            else:
                continue  # Skip non-relevant domains

            final.append({
                'url': url,
                'site': site,
                'title': title,
                'content': content,
                'raw_content': raw_content
            })

        return TavilyOutput(response=final)

    def _arun(self, query: str):
        raise NotImplementedError('Async not implemented')