
# src/llm.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
from .config import LLAMA_MODEL

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llama(prompt: str) -> str:
    """
    Sends a prompt to the LLaMA model and returns its response.
    Args:
        prompt (str): The user's query or a structured prompt for the LLM.
    Returns:
        str: The content of the LLM's response.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=LLAMA_MODEL,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        # Re-raise the exception to be handled by the calling function (handlers.py)
        # This allows for specific error messages like LLM_API_FAILURE
        raise Exception(f"LLaMA API error: {e}")

def extract_query_info_from_llm(query: str, tenant_id: str, group_id: str | None) -> dict:
    """
    Uses LLaMA 3 to extract intent and entities (dates, pname) from a natural language query.
    It expects a JSON output from LLaMA 3 for structured parsing.
    Args:
        query (str): The natural language query from the user.
        tenant_id (str): The ID of the logged-in tenant.
        group_id (str | None): The group ID associated with the tenant, if any.
    Returns:
        dict: A dictionary containing extracted intent, start_date, end_date, pname, scope.
              Example: {"intent": "single_day_sales", "start_date": "YYYY-MM-DD", "pname": None, "scope": "tenant"}
              Returns empty dict or specific error indicator if parsing fails.
    """
    # System prompt to guide the LLM to output a JSON structure
    # Emphasize only valid JSON and specific date formats
    system_prompt = f"""
    You are an AI assistant tasked with parsing sales-related queries from a user.
    Your goal is to extract the user's intent, date ranges, property names (pname), and query scope (tenant or group).
    The current logged-in tenant is '{tenant_id}'. Their associated group is '{group_id}' (if available).
    If the user mentions 'my group' or refers to '{group_id}', the scope is 'group'. Otherwise, the scope is 'tenant'.

    Output your response STRICTLY as a JSON object with the following keys:
    - "intent": (string) one of ["single_day_sales", "date_range_sales", "highest_sales", "lowest_sales", "monthly_sales", "weekly_sales", "summary", "unknown"]
    - "start_date": (string or null) date in YYYY-MM-DD format if a specific date or start of range is detected. Set to null if the query implies "all time" (e.g., "highest ever") or "current month/week" (e.g., "monthly sales").
    - "end_date": (string or null) date in YYYY-MM-DD format if an end of range is detected. Set to null if the query implies "all time" (e.g., "highest ever") or "current month/week" (e.g., "monthly sales").
    - "pname": (string or null) The exact property name mentioned if any.
    - "scope": (string) "tenant" or "group" based on the query.

    If dates are ambiguous (e.g., "yesterday", "last week"), use today's date (or a range relative to it) and assume current year.
    For "highest_sales" or "lowest_sales" intents: if no specific date or period is mentioned, assume "all time" and set start_date and end_date to null.
    For "monthly_sales" or "weekly_sales" intents: if no specific month/week is mentioned, assume "current month/week" and set start_date and end_date to null.

    Examples:
    - "What were my sales on 2nd May?" -> {{"intent": "single_day_sales", "start_date": "2025-05-02", "end_date": "2025-05-02", "pname": null, "scope": "tenant"}}
    - "Show sales from March 1st to March 7th for propertyX." -> {{"intent": "date_range_sales", "start_date": "2025-03-01", "end_date": "2025-03-07", "pname": "propertyX", "scope": "tenant"}}
    - "When was my highest sale?" -> {{"intent": "highest_sales", "start_date": null, "end_date": null, "pname": null, "scope": "tenant"}}
    - "Highest sales last month for my group." -> {{"intent": "highest_sales", "start_date": "2025-05-01", "end_date": "2025-05-31", "pname": null, "scope": "group"}} (assuming current month is June)
    - "What was my monthly sale?" -> {{"intent": "monthly_sales", "start_date": null, "end_date": null, "pname": null, "scope": "tenant"}}
    - "Show me this week's sales." -> {{"intent": "weekly_sales", "start_date": null, "end_date": null, "pname": null, "scope": "tenant"}}
    - "Tell me about my overall sales." -> {{"intent": "summary", "start_date": null, "end_date": null, "pname": null, "scope": "tenant"}}
    """
    user_prompt = f"Analyze the following query: '{query}'"

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=LLAMA_MODEL,
            response_format={"type": "json_object"} # Instruct LLM to return JSON
        )
        llm_response_content = response.choices[0].message.content
        return json.loads(llm_response_content)
    except json.JSONDecodeError:
        print(f"LLM did not return valid JSON: {llm_response_content}")
        return {"intent": "unknown", "error": "Invalid JSON from LLM"}
    except Exception as e:
        print(f"Error calling LLM for query extraction: {e}")
        raise # Re-raise to be caught by the main handler for general API failure
