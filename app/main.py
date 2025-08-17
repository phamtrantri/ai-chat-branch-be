from contextlib import asynccontextmanager
from dotenv import load_dotenv
from agents import Agent, Runner
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.db import db

load_dotenv(override=True)
origins = [
    "*",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    yield
    # Shutdown
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# conversations (id, name)
# messages (content, conversation_id, parent_id, role, depth, num_of_children)





@app.get("/")
async def root():
    agent = Agent(name="Assistant", instructions="You are a helpful assistant")

    result = await Runner.run(agent, "Write a haiku about recursion in programming.")
    return {"message": result.final_output}

# get conversations - done
# get one conversations - done
# get nested msg in a parent msg - done
# create conversation - done
# create first level msg
# create nested msg


class ConversationCreate(BaseModel):
    name: str

class ConversationDetails(BaseModel):
    id: int

@app.post("/conversations/v1/getAll")
async def getConversations():
    conversations = await db.fetch_all("SELECT * from conversations")
    return {
        "code": 0, 
        "data": {
            "conversations": conversations
        }
    }

@app.post("/conversations/v1/getDetails")
async def getConversationDetails(body: ConversationDetails):
    messages = await db.fetch_all("SELECT * from messages WHERE conversation_id = %s AND depth = 1", (body.id,))
    return {
        "code": 0,
        "data": {
            "messages": messages
        }
    }
@app.post("/conversations/v1/create")
async def createConversations(body: ConversationCreate):
    await db.execute("INSERT INTO conversations (name) VALUES (%s)", (body.name,))
    return {
        "code": 0
    }

# messages
class GetNestedMessagesReq(BaseModel):
    parent_msg_id: int
    branch_id: int

@app.post("/messages/getNestedMessages")
async def getNestedMessages(body: GetNestedMessagesReq):
    messages = await db.fetch_all("SELECT * from messages where parent_id = %s AND branch_id = %s", (body.parent_msg_id, body.branch_id,))
    return {
        "code": 0,
        "data": {
            "messages": messages
        }
    }