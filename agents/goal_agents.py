import uuid
import json
from datetime import datetime
from agents.llm_main import llm
from agents.json_extractor import extract_json   # SAFE JSON EXTRACTOR


def goal_agent(userId: str, query: str, response: str, lang: str):
    """
    1. Detect if user expressed a goal
    2. Build goal JSON using your schema
    3. Convert to single-line Mongo JSON in ( ... )
    """

    # ---- 1. Ask LLM to detect goal ----
    detect_prompt = f"""
You are a goal detection agent.

User Query: "{query}"
Assistant Answer: "{response}"
Language: "{lang}"

Rules:
- If NO GOAL → return exactly this JSON:
{{"is_goal": false}}

- If GOAL → return JSON like:
{{
 "is_goal": true,
 "type": "<short goal>",
 "description": "<full description>",
 "targetAmountPaise": <number or null>,
 "deadline": "<ISO date or null>"
}}

Return ONLY valid JSON.
"""

    detection = llm.invoke(detect_prompt)
    detection_text = detection.content if hasattr(detection, "content") else str(detection)

    # SAFE JSON extraction
    detection_json = extract_json(detection_text)

    if not detection_json.get("is_goal"):
        print("Goal Agent: No goal found")
        return None

    # ---- 2. Create full Goal JSON ----
    goal_id = f"goal_{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow().isoformat()

    goal_doc = {
        "goalId": goal_id,
        "userId": userId,
        "type": detection_json.get("type"),
        "description": detection_json.get("description"),
        "targetAmountPaise": detection_json.get("targetAmountPaise"),
        "currentAmountPaise": 0,
        "remainingAmountPaise": detection_json.get("targetAmountPaise"),
        "deadline": detection_json.get("deadline"),
        "monthsRemaining": None,
        "requiredMonthlySavingsPaise": None,
        "requiredWeeklySavingsPaise": None,
        "requiredDailySavingsPaise": None,
        "priority": "medium",
        "feasibility": None,
        "gapPaise": None,
        "autoAdjustEnabled": True,
        "createdAt": now,
        "updatedAt": now
    }

    # ---- 3. Format as Mongo single-line JSON ----
    # FIX: Escape curly braces in f-string -> {{ }}
    format_prompt = f"""
You are a MongoDB JSON formatting agent.

Return this EXACT JSON as a single line inside parentheses.  
Do NOT change anything.

JSON:
{json.dumps(goal_doc, ensure_ascii=False)}

Return ONLY:
({{{{"sample":"value"}}}})
"""

    formatted = llm.invoke(format_prompt)
    formatted_text = formatted.content if hasattr(formatted, "content") else str(formatted)

    return formatted_text
