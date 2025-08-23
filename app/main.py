import asyncio
import json
from contextlib import asynccontextmanager
from email import message
from dotenv import load_dotenv
from agents import Agent, Runner
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from httpx import Response
from openai.types.responses import ResponseTextDeltaEvent
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

agent = Agent(name="Assistant", instructions="You are a helpful assistant")

# conversations (id, name)
# messages (content, conversation_id, parent_id, role, depth, num_of_children)





@app.get("/")
async def root():
    result = await Runner.run(agent, "Write a haiku about recursion in programming.")
    return {"message": result.final_output}

# get conversations - done
# get one conversations - done
# get nested msg in a parent msg - done
# create conversation - done
# create first level msg - done
# create nested msg


class ConversationCreate(BaseModel):
    name: str
    message_id: str | None = None

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
    messages = await db.fetch_all("SELECT * from messages WHERE conversation_id = %s", (body.id,))
    return {
        "code": 0,
        "data": {
            "messages": messages
        }
    }
@app.post("/conversations/v1/create")
async def createConversations(body: ConversationCreate):
    if (not body.message_id):
        await db.execute("INSERT INTO conversations (name) VALUES (%s)", (body.name,))
    else:
        await db.execute("INSERT INTO conversations (name, message_id) VALUES (%s, %s)", (body.name, body.message_id,))
    return {
        "code": 0
    }

# messages
# class GetNestedMessagesReq(BaseModel):
#     parent_msg_id: int
#     branch_id: int

# @app.post("/messages/v1/getNestedMessages")
# async def getNestedMessages(body: GetNestedMessagesReq):
#     messages = await db.fetch_all("SELECT * from messages where parent_id = %s AND branch_id = %s", (body.parent_msg_id, body.branch_id,))
#     return {
#         "code": 0,
#         "data": {
#             "messages": messages
#         }
#     }

class CreateMessageReq(BaseModel):
    conversation_id: int
    user_message: str


@app.post("/messages/v1/create")
async def createMessage(body: CreateMessageReq):
    async def generate_stream():
        # Insert user message first
        await db.execute("INSERT INTO messages (content, conversation_id, role, num_of_children) VALUES (%s, %s, %s, %s)", (body.user_message, body.conversation_id, "user", 0,))
            
        # Get conversation history
        history = await db.fetch_all("SELECT content, role from messages WHERE conversation_id = %s ORDER BY created_at ASC", (body.conversation_id,))
            
        # Stream the response
        full_response = ""
        result = Runner.run_streamed(agent, history + [{"role": "user", "content": body.user_message}])
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                full_response += event.data.delta
                yield event.data.delta
            
        # Insert assistant message after streaming completes
        await db.execute("INSERT INTO messages (content, conversation_id, role, num_of_children) VALUES (%s, %s, %s, %s)", (full_response, body.conversation_id, "assistant", 0,))
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )




# class CreateNestedMessagesReq(BaseModel):
#     conversation_id: int
#     parent_msg_id: int
#     user_message: str
#     branch_id: str
#     depth: str

# @app.post("/messages/v1/createNestedMessage")
# async def createNestedMessage(body: CreateNestedMessagesReq):
#     try:
#         async def getHistory(parent_msg_id, branch_id):
#             if (not parent_msg_id):
#                 return await db.fetch_all("SELECT content, role, parent_msg_id, branch_id from messages WHERE conversation_id = %s ORDER BY created_at ASC", (body.conversation_id))
            
#             [parent_msg, db_result] = await asyncio.gather([
#                 db.fetch_one("SELECT parent_msg_id, branch_id from messages WHERE id = %s", (parent_msg_id)),
#                 db.fetch_all("SELECT content, role from messages WHERE parent_msg_id = %s AND branch_id = %s ORDER BY created_at ASC", (parent_msg_id, branch_id,))
#             ])

#             return await getHistory(parent_msg.parent_msg_id, parent_msg.branch_id) + db_result

#         history = await getHistory(body.parent_msg_id, body.branch_id)
#         result = await Runner.run(agent, history + [{"role": "user", "content": body.user_message}])

#         # Use transaction to ensure both inserts succeed or fail together
#         async with db.transaction() as conn:
#             with conn.cursor() as cur:
#                 cur.execute("BEGIN")
#                 cur.execute("SELECT id FROM messages WHERE branch_id = %s LIMIT 1", (body.branch_id,))
#                 branch_exists = cur.fetchone()
#                 if not branch_exists:
#                     cur.execute("UPDATE messages SET num_of_children = num_of_children + 1 WHERE id = %s", (body.parent_msg_id,))
#                 cur.execute("INSERT INTO messages (content, conversation_id, branch_id, role, depth) VALUES (%s, %s, %s, %s, %s, %s)", (body.user_message, body.conversation_id, body.branch_id, "user", body.depth,))
#                 cur.execute("INSERT INTO messages (content, conversation_id, branch_id, role, depth) VALUES (%s, %s, %s, %s, %s, %s)", (result.final_output, body.conversation_id, body.branch_id, "assistant", body.depth,))
#                 cur.execute("COMMIT")
        
#         return {"code": 0}
#     except Exception as e:
#         return {"code": 1}
    


