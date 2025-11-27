from fastapi import FastAPI , UploadFile, File, Form
from pydantic import BaseModel
import json 
from sp_text import speech_to_text
from agents.sms_agent import data_creater
from agents.db_agent_one import mongo_query_agent
from db import save_tx
app = FastAPI()


@app.get('/')
def home():
    print('Server running')
    return {'message':'FastAPI running'}

from fastapi import FastAPI, UploadFile, File, Form
import json
from sp_text import speech_to_text
from agents.sms_agent import data_creater

app = FastAPI()

@app.post("/api/speech_msg")
async def speech_input(
    meta: str = Form(...),
    audio: UploadFile = File(...)
):

    # parse incoming JSON
    parsed = json.loads(meta)
    user_id = parsed["userId"]
    timestamp = parsed["timestamp"]

    # save audio temp file
    audio_bytes = await audio.read()
    temp_path = "temp_input_audio.mp3"
    with open(temp_path, "wb") as f:
        f.write(audio_bytes)

    # run whisper
    sms_text = speech_to_text(temp_path)

    # run SMS agent
    result = data_creater(user_id, sms_text, timestamp)
    print(type(result))
    fin= mongo_query_agent(result)
    response = await save_tx(fin)
    print(response)
    return {'message':'Success'}