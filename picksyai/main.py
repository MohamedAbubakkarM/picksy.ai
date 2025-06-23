from crewai import Crew, Process
from pydantic import BaseModel, ValidationError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import re
import traceback
from picksyai.agents.DealFinderAgent import deal_finder_agent
from picksyai.tasks.DealFindingTask import deal_finding_task

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    product_name: str


def clean_json_string(json_str):
    """
    Clean and fix common JSON formatting issues
    """
    if not isinstance(json_str, str):
        return json_str

    # Remove markdown code blocks
    json_str = re.sub(r'^```json\s*\n?', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'\n?```\s*$', '', json_str, flags=re.MULTILINE)

    # Remove any extra whitespace
    json_str = json_str.strip()

    # Fix common JSON issues
    # Replace "null" strings with null
    json_str = re.sub(r':\s*"null"', ': null', json_str)

    # Fix trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    # Fix line breaks in strings that might break JSON
    json_str = re.sub(r'(?<!\\)\n(?![}\]",])', ' ', json_str)

    return json_str


def extract_and_parse_json(result):
    """
    Enhanced JSON extraction and parsing with better error handling
    """
    try:
        print(f"🔍 Analyzing result type: {type(result)}")
        print(f"🔍 Result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")

        # Method 1: Check if result has pydantic attribute (for output_pydantic)
        if hasattr(result, "pydantic") and result.pydantic:
            print("✅ Found pydantic output")
            try:
                if hasattr(result.pydantic, 'model_dump'):
                    return result.pydantic.model_dump()
                elif hasattr(result.pydantic, 'dict'):
                    return result.pydantic.dict()
                else:
                    return result.pydantic
            except Exception as e:
                print(f"❌ Error extracting pydantic data: {e}")

        # Method 2: Check if result has json_dict attribute
        if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
            print("✅ Found json_dict attribute")
            return result.json_dict

        # Method 3: Check if result has json attribute
        if hasattr(result, "json") and isinstance(result.json, dict):
            print("✅ Found json attribute")
            return result.json

        # Method 4: Check if result itself is a dict
        if isinstance(result, dict):
            print("✅ Result is already a dict")
            return result

        # Method 5: Check tasks_output for pydantic models
        if hasattr(result, 'tasks_output') and result.tasks_output:
            print("🔍 Checking tasks_output...")
            for i, task_output in enumerate(result.tasks_output):
                print(f"🔍 Task {i} attributes: {[attr for attr in dir(task_output) if not attr.startswith('_')]}")

                if hasattr(task_output, 'pydantic') and task_output.pydantic:
                    print(f"✅ Found pydantic in task output {i}")
                    try:
                        if hasattr(task_output.pydantic, 'model_dump'):
                            return task_output.pydantic.model_dump()
                        elif hasattr(task_output.pydantic, 'dict'):
                            return task_output.pydantic.dict()
                        else:
                            return task_output.pydantic
                    except Exception as e:
                        print(f"❌ Error extracting pydantic from task {i}: {e}")

                # Check for json_dict in task output
                if hasattr(task_output, 'json_dict') and isinstance(task_output.json_dict, dict):
                    print(f"✅ Found json_dict in task output {i}")
                    return task_output.json_dict

                # Check raw output from task
                if hasattr(task_output, 'raw') and task_output.raw:
                    print(f"🔍 Found raw output in task {i}")
                    raw_content = task_output.raw
                    if isinstance(raw_content, str):
                        cleaned_content = clean_json_string(raw_content)
                        try:
                            parsed = json.loads(cleaned_content)
                            print(f"✅ Successfully parsed JSON from task {i} raw output")
                            return parsed
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON parse error in task {i} raw: {e}")

        # Method 6: Try to parse raw string content
        raw_content = None
        if hasattr(result, "raw"):
            raw_content = result.raw
        elif hasattr(result, "content"):
            raw_content = result.content
        elif isinstance(result, str):
            raw_content = result

        if raw_content and isinstance(raw_content, str):
            print(f"📝 Raw content preview: {raw_content[:300]}...")

            # Clean the content
            cleaned_content = clean_json_string(raw_content)

            # Try to parse as JSON
            try:
                parsed = json.loads(cleaned_content)
                print("✅ Successfully parsed cleaned JSON")
                return parsed
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                print(
                    f"❌ Problematic content around position {e.pos}: '{cleaned_content[max(0, e.pos - 50):e.pos + 50]}'")

            # Try to find and extract JSON block
            patterns = [
                r"```json\s*\n(.*?)\n```",  # Standard markdown json block
                r"```\s*\n(\{.*?\})\s*\n```",  # Generic code block with JSON
                r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})",  # Direct JSON object
            ]

            for pattern in patterns:
                json_match = re.search(pattern, raw_content, re.DOTALL | re.IGNORECASE)
                if json_match:
                    json_str = json_match.group(1).strip()
                    json_str = clean_json_string(json_str)
                    print(f"🔍 Found JSON with pattern: {json_str[:100]}...")
                    try:
                        parsed = json.loads(json_str)
                        print("✅ Successfully parsed extracted JSON")
                        return parsed
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parse error in extracted block: {e}")
                        continue

            # If all else fails, return as text response
            return {"response": raw_content, "type": "text", "error": "Could not parse as JSON"}

    except Exception as e:
        print(f"❌ Error in JSON extraction: {e}")
        print(traceback.format_exc())

    return None


def validate_agent_configuration():
    """
    Validate that agents are properly configured
    """
    try:
        print("🔍 Validating agent configuration...")

        if not deal_finder_agent:
            raise ValueError("deal_finder_agent is None")

        if not hasattr(deal_finder_agent, 'llm') or not deal_finder_agent.llm:
            raise ValueError("deal_finder_agent.llm is not configured")

        print("✅ Agent configuration validated")
        return True

    except Exception as e:
        print(f"❌ Agent configuration error: {e}")
        return False


@app.post("/picsyai/ask")
async def run_crew(request: QueryRequest):
    product_name = request.product_name

    try:
        print(f"🚀 Starting crew for product: {product_name}")

        # Validate agent configuration
        if not validate_agent_configuration():
            return JSONResponse(
                content={
                    "error": "Agent configuration error",
                    "message": "Deal finder agent is not properly configured",
                    "type": "configuration_error"
                },
                status_code=500
            )

        # Create crew with better error handling
        crew2 = Crew(
            agents=[deal_finder_agent],
            tasks=[deal_finding_task],
            process=Process.sequential,
            verbose=True,
            memory=False,  # Disable memory to avoid potential issues
            step_callback=None,  # Disable callbacks that might cause issues
        )

        print("🚀 Executing crew...")
        result2 = crew2.kickoff(inputs={"product_name": product_name, "location": "Chennai"})

        print(f"📋 Raw result type: {type(result2)}")
        if hasattr(result2, '__dict__'):
            print(f"📋 Raw result dict: {result2.__dict__}")

        # Extract and parse JSON using enhanced method
        parsed_result = extract_and_parse_json(result2)

        if parsed_result and isinstance(parsed_result, dict) and "error" not in parsed_result:
            print("✅ Successfully parsed result")

            # Validate the structure matches expected format
            required_keys = ["summary", "deals", "analysis", "recommendations", "notes"]
            if all(key in parsed_result for key in required_keys):
                return JSONResponse(
                    content=parsed_result,
                    status_code=200,
                    headers={"Content-Type": "application/json"}
                )
            else:
                missing_keys = [key for key in required_keys if key not in parsed_result]
                print(f"⚠️ Missing required keys: {missing_keys}")

                return JSONResponse(
                    content={
                        "partial_result": parsed_result,
                        "warning": f"Missing required keys: {missing_keys}",
                        "type": "partial_success"
                    },
                    status_code=200
                )
        else:
            print("❌ Failed to parse result or result contains errors")
            return JSONResponse(
                content={
                    "error": "Failed to parse crew output",
                    "raw_type": str(type(result2)),
                    "parsed_result": parsed_result,
                    "raw_content": str(result2)[:1000] + "..." if len(str(result2)) > 1000 else str(result2)
                },
                status_code=500
            )

    except ValidationError as ve:
        print(f"💥 Pydantic validation error: {ve}")
        print(f"💥 Error details: {ve.errors()}")
        return JSONResponse(
            content={
                "error": "Data validation error",
                "message": str(ve),
                "errors": ve.errors() if hasattr(ve, 'errors') else [],
                "type": "validation_error",
                "input_value": str(ve.input_value)[:500] if hasattr(ve, 'input_value') else "N/A"
            },
            status_code=422
        )
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"💥 Error in crew execution: {error_trace}")

        # Check for specific known errors
        if "function_calling_llm" in str(e):
            return JSONResponse(
                content={
                    "error": "Agent configuration error",
                    "message": "Agent LLM is not properly configured. Please check agent setup.",
                    "type": "configuration_error",
                    "details": str(e)
                },
                status_code=500
            )
        elif "JSON" in str(e) or "json" in str(e):
            return JSONResponse(
                content={
                    "error": "JSON parsing error",
                    "message": "Failed to parse agent response as JSON",
                    "type": "parsing_error",
                    "details": str(e)
                },
                status_code=500
            )
        else:
            return JSONResponse(
                content={
                    "error": "Internal server error",
                    "message": str(e),
                    "type": "execution_error",
                    "trace": error_trace.split('\n')[-10:]  # Last 10 lines of trace
                },
                status_code=500
            )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "picksyai"}


@app.get("/debug/agent")
async def debug_agent():
    """Debug endpoint to check agent configuration"""
    try:
        agent_info = {
            "deal_finder_agent": {
                "exists": deal_finder_agent is not None,
                "type": str(type(deal_finder_agent)),
                "has_llm": hasattr(deal_finder_agent, 'llm') and deal_finder_agent.llm is not None,
                "has_function_calling_llm": hasattr(deal_finder_agent,
                                                    'function_calling_llm') and deal_finder_agent.function_calling_llm is not None,
                "role": getattr(deal_finder_agent, 'role', 'N/A'),
                "tools": len(getattr(deal_finder_agent, 'tools', [])),
            }
        }

        if deal_finder_agent and hasattr(deal_finder_agent, 'llm') and deal_finder_agent.llm:
            agent_info["deal_finder_agent"]["llm_type"] = str(type(deal_finder_agent.llm))

        return JSONResponse(content=agent_info)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "trace": traceback.format_exc()},
            status_code=500
        )


# Add a test endpoint to debug JSON responses
@app.get("/test-json")
async def test_json():
    return JSONResponse(
        content={
            "test": "success",
            "data": {
                "product_searched": "HP Victus 15 Gaming Laptop",
                "summary": "This is a test response",
                "deals": [
                    {"store": "Amazon", "price": "₹65,000"},
                    {"store": "Flipkart", "price": "₹63,500"}
                ]
            }
        },
        status_code=200
    )