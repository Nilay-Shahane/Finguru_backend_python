from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi import BackgroundTasks

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
import json

# from sp_text import speech_to_text  # Commented out - causing whisper import issues
from agents.sms_agent import data_creater
from agents.db_agent_one import mongo_query_agent
from db import save_tx
from main_agent import run_agent_pipeline
from agents.mongo_goal_inserter import process_and_insert_goal
from agents.weeklybudget_updater import update_weekly_budget_analysis
from agents.weeklybudget_generator import create_next_week_budget

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
    lang: str = "english"  # supports: "english", "hindi"


@app.get('/')
def root():
    print('Server running')
    return {'message': 'FinWell Agent API is running'}

@app.post("/api/speech_msg")
# async def speech_input(
#     meta: str = Form(...),
#     audio: UploadFile = File(...),
#     lang: str = Form(...)   # "en" | "hi"
# ):
#     try:
#         # Parse metadata
#         parsed = json.loads(meta)
#         user_id = parsed["userId"]
#         timestamp = parsed["timestamp"]

#         # Save audio
#         audio_bytes = await audio.read()
#         temp_path = "temp_input_audio.mp3"
#         with open(temp_path, "wb") as f:
#             f.write(audio_bytes)

#         # Speech → Text (Hindi remains Hindi)
#         sms_text = speech_to_text(temp_path,lang)

#         # --- NEW: Force English data creation ---
#         result = data_creater(
#             user_id=user_id,
#             sms_text=sms_text,
#             timestamp=timestamp      # 👈 Force English always
#         )

#         # Query agent
#         fin = mongo_query_agent(result)

#         # Save transaction
#         response = await save_tx(fin)

#         return {'message': 'Success', 'data': response}

#     except json.JSONDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid JSON in meta field")
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing speech input: {str(e)}"
#         )

    
#     except json.JSONDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid JSON in meta field")
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing speech input: {str(e)}"
#         )

@app.post("/query")
async def handle_query(body: AgentQuery,background_tasks: BackgroundTasks):
    """
    Handles user text query without any CSV input.
    Uses run_agent_pipeline(userId, query) and saves to MongoDB.
    """
    try:
        # Run agent pipeline
        response = run_agent_pipeline(body.userId, body.query,body.lang)

        if response and isinstance(response, dict) and 'error' in response:
                raise HTTPException(status_code=400, detail=response['error'])

        # Save chat to MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["finguru"]
        db.chats.insert_one({
            "userId": body.userId,
            "query": body.query,
            "lang":body.lang,
            "response": response,
            "timestamp": datetime.utcnow()
        })
        background_tasks.add_task(
            process_and_insert_goal,
            body.userId,
            body.query,
            response,
            body.lang
        )
        return {"response": response}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred: {str(e)}"
        )


class WeeklyBudgetRequest(BaseModel):
    userId: str


@app.post("/api/weekly-budget/analyze")
async def analyze_weekly_budget(body: WeeklyBudgetRequest):
    """
    Analyzes the current week's budget for a user using AI and updates MongoDB.
    Compares with previous 2 weeks to generate risk scores and status for each category.
    
    Example usage:
    POST http://localhost:8000/api/weekly-budget/analyze
    Body: {"userId": "usr_rahul_001"}
    """
    try:
        result = update_weekly_budget_analysis(body.userId)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=404 if "No budget found" in result.get("error", "") else 500,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing weekly budget: {str(e)}"
        )


@app.post("/api/weekly-budget/create-next")
async def create_next_weekly_budget(body: WeeklyBudgetRequest):
    """
    Creates next week's budget based on current week's maxBudgetPaise values.
    All spending fields are reset to 0, ready for new week tracking.
    
    Example usage:
    POST http://localhost:8000/api/weekly-budget/create-next
    Body: {"userId": "usr_rahul_001"}
    """
    try:
        result = create_next_week_budget(body.userId)
        
        if not result.get("success", False):
            status_code = 409 if "already exists" in result.get("error", "") else 404
            raise HTTPException(
                status_code=status_code,
                detail=result.get("error", "Unknown error occurred")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating next week's budget: {str(e)}"
        )