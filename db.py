from motor.motor_asyncio import AsyncIOMotorClient
import json

MONGO_URL = "mongodb://localhost:27017"

client = AsyncIOMotorClient(MONGO_URL)
db = client["finguru"]
transactions = db["transactions"]


async def save_tx(transaction):
    clean = transaction.strip()

    if clean.startswith("(") and clean.endswith(")"):
        clean = clean[1:-1]
    
    transaction = json.loads(clean)
    result = await transactions.insert_one(transaction)
    print("Inserted ID:", result.inserted_id)
