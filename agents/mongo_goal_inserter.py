# mongo_goal_inserter.py

import json
from motor.motor_asyncio import AsyncIOMotorClient
from agents.goal_agents import goal_agent

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["finguru"]
goals = db["goals"]


async def process_and_insert_goal(userId: str, query: str, response: str, lang: str):
    """
    1. Run goal agent → produces single-line Mongo JSON
    2. Clean parentheses
    3. Convert to dict
    4. Insert async
    """

    mongo_json_line = goal_agent(userId, query, response, lang)

    if not mongo_json_line:
        print("No goal detected → skipping goal insert.")
        return None

    clean = mongo_json_line.strip()

    if clean.startswith("(") and clean.endswith(")"):
        clean = clean[1:-1]

    goal_dict = json.loads(clean)

    result = await goals.insert_one(goal_dict)
    print("Inserted Goal ID:", result.inserted_id)
    return result.inserted_id
