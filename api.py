from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
import json

from sp_text import speech_to_text
from agents.sms_agent import data_creater
from agents.db_agent_one import mongo_query_agent
from db import save_tx
from main_agent import run_agent_pipeline

app = FastAPI(title="FinWell Agent API", version="1.0.0")

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentQuery(BaseModel):
    userId: str
    query: str

@app.get('/')
def root():
    print('Server running')
    return {'message': 'FinWell Agent API is running'}

@app.post("/api/speech_msg")
async def speech_input(
    meta: str = Form(...),
    audio: UploadFile = File(...)
):
    """
    Handles speech-to-text input and processes transaction data.
    """
    try:
        # Parse incoming JSON metadata
        parsed = json.loads(meta)
        user_id = parsed["userId"]
        timestamp = parsed["timestamp"]

        # Save audio temp file
        audio_bytes = await audio.read()
        temp_path = "temp_input_audio.mp3"
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # Run Whisper speech-to-text
        sms_text = speech_to_text(temp_path)

        # Run SMS agent to create data
        result = data_creater(user_id, sms_text, timestamp)
        print(f"SMS agent result type: {type(result)}")
        
        # Process with MongoDB query agent
        fin = mongo_query_agent(result)
        
        # Save transaction
        response = await save_tx(fin)
        print(f"Save transaction response: {response}")
        
        return {'message': 'Success', 'data': response}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in meta field")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing speech input: {str(e)}"
        )

@app.post("/query")
def handle_query(body: AgentQuery):
    """
    Handles user text query without any CSV input.
    Uses run_agent_pipeline(userId, query) and saves to MongoDB.
    """
    try:
        # Run agent pipeline
        response = run_agent_pipeline(body.userId, body.query)

        if response and isinstance(response, dict) and 'error' in response:
            raise HTTPException(status_code=400, detail=response['error'])

        # Save chat to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["finguru"]
        db.chats.insert_one({
            "userId": body.userId,
            "query": body.query,
            "response": response,
            "timestamp": datetime.utcnow()
        })

        return {"response": response}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred: {str(e)}"
        )