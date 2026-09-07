from crewai import Crew, Process
from pydantic import BaseModel, ValidationError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import re
import traceback
from agents.DealFinderAgent import deal_finder_agent
from tasks.DealFindingTask import deal_finding_task

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
    if not isinstance(json_str, str):
        return json_str

    json_str = re.sub(r'^```json\s*\n?', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'\n?```\s*$', '', json_str, flags=re.MULTILINE)
    json_str = json_str.strip()
    json_str = re.sub(r':\s*"null"', ': null', json_str)
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r'(?<!\\)\n(?![}\]",])', ' ', json_str)

    return json_str


def extract_and_parse_json(result):
    try:
        if hasattr(result, "pydantic") and result.pydantic:
            try:
                if hasattr(result.pydantic, 'model_dump'):
                    return result.pydantic.model_dump()
                elif hasattr(result.pydantic, 'dict'):
                    return result.pydantic.dict()
                else:
                    return result.pydantic
            except Exception:
                pass

        if hasattr(result, "json_dict") and isinstance(result.json_dict, dict):
            return result.json_dict

        if hasattr(result, "json") and isinstance(result.json, dict):
            return result.json

        if isinstance(result, dict):
            return result

        if hasattr(result, 'tasks_output') and result.tasks_output:
            for task_output in result.tasks_output:
                if hasattr(task_output, 'pydantic') and task_output.pydantic:
                    try:
                        if hasattr(task_output.pydantic, 'model_dump'):
                            return task_output.pydantic.model_dump()
                        elif hasattr(task_output.pydantic, 'dict'):
                            return task_output.pydantic.dict()
                        else:
                            return task_output.pydantic
                    except Exception:
                        pass

                if hasattr(task_output, 'json_dict') and isinstance(task_output.json_dict, dict):
                    return task_output.json_dict

                if hasattr(task_output, 'raw') and task_output.raw:
                    raw_content = task_output.raw
                    if isinstance(raw_content, str):
                        cleaned_content = clean_json_string(raw_content)
                        try:
                            return json.loads(cleaned_content)
                        except json.JSONDecodeError:
                            pass

        raw_content = None
        if hasattr(result, "raw"):
            raw_content = result.raw
        elif hasattr(result, "content"):
            raw_content = result.content
        elif isinstance(result, str):
            raw_content = result

        if raw_content and isinstance(raw_content, str):
            cleaned_content = clean_json_string(raw_content)

            try:
                return json.loads(cleaned_content)
            except json.JSONDecodeError:
                pass

            patterns = [
                r"```json\s*\n(.*?)\n```",
                r"```\s*\n(\{.*?\})\s*\n```",
                r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})",
            ]

            for pattern in patterns:
                json_match = re.search(pattern, raw_content, re.DOTALL | re.IGNORECASE)
                if json_match:
                    json_str = clean_json_string(json_match.group(1).strip())
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue

            return {"response": raw_content, "type": "text", "error": "Could not parse as JSON"}

    except Exception:
        traceback.print_exc()

    return None


def validate_agent_configuration():
    if not deal_finder_agent:
        return False
    if not hasattr(deal_finder_agent, 'llm') or not deal_finder_agent.llm:
        return False
    return True


@app.post("/picksyai/ask")
async def run_crew(request: QueryRequest):
    product_name = request.product_name

    try:
        if not validate_agent_configuration():
            return JSONResponse(
                content={
                    "error": "Agent configuration error",
                    "message": "Deal finder agent is not properly configured",
                    "type": "configuration_error"
                },
                status_code=500
            )

        crew2 = Crew(
            agents=[deal_finder_agent],
            tasks=[deal_finding_task],
            process=Process.sequential,
            verbose=True,
            memory=False,
            step_callback=None,
            tracing=True,
        )

        result2 = await crew2.kickoff_async(inputs={"product_name": product_name, "location": "TamilNadu"})

        parsed_result = extract_and_parse_json(result2)

        if parsed_result and isinstance(parsed_result, dict) and "error" not in parsed_result:
            required_keys = ["summary", "deals", "analysis", "recommendations", "notes"]
            if all(key in parsed_result for key in required_keys):
                return JSONResponse(
                    content=parsed_result,
                    status_code=200,
                    headers={"Content-Type": "application/json"}
                )
            else:
                missing_keys = [key for key in required_keys if key not in parsed_result]
                return JSONResponse(
                    content={
                        "partial_result": parsed_result,
                        "warning": f"Missing required keys: {missing_keys}",
                        "type": "partial_success"
                    },
                    status_code=200
                )
        else:
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
                    "trace": error_trace.split('\n')[-10:]
                },
                status_code=500
            )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "picksyai"}
