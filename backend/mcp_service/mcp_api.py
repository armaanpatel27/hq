from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, Union
import asyncio
from contextlib import asynccontextmanager
import httpx
import json
import os
from dotenv import load_dotenv
from mcp_client import MCPClient
import traceback
import uvicorn
from typing import Annotated
import anyio


# Load environment variables
load_dotenv()

# Constants
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("MODEL")

# Initialize MCP client
mcp_client = MCPClient()

#lifespan to connect to the mcp server and cleanup --> better cycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup
        await mcp_client.connect_to_server("mcp_server.py")
        yield
    finally:
        # Ensure cleanup happens even if there's an error
        try:
            await mcp_client.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class ToolResponse(BaseModel):
    result: Any

async def generate_plan(user_message: str) -> Dict[str, Any]:
    """Generate a plan using Claude based on user message."""
    
    prompt = f"""
    Please respond with only valid JSON, no extra commentary or explanation. The JSON should be properly formatted.
    Use only the tools given. If the prompt doesn't require a tool, return the tool "none" with no parameters. Don't try to force a prompt into a tool.

    User request: {user_message}
    """
    try:
        #retrieve tools to send
        tools = await mcp_client.get_mcp_tools()
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": tools,
                    "tool_choice": {"type":"any"}
                }
            )
            response.raise_for_status()
            result = response.json()

            tool_use = None
            for item in result.get("content", []):
                if item.get("type") == "tool_use":
                    tool_use = item
                    break
                
            plan = tool_use  # or extract parts of tool_use if needed, e.g., tool_use['name'], tool_use['input']
            return plan

    except Exception as e:
        print("🔍 Unexpected Exception Type:", type(e).__name__)
        print("📜 Exception args:", e.args)
        print("🧵 Full traceback:")
        traceback.print_exc()

        
async def generate_user_response(user_message: str, tool_result: Optional[Dict[str, Any]] = None) -> str:
    """Generate a user-friendly response based on the tool execution results."""
    
    if tool_result is None:
        prompt = f"""Given the original user request, generate a clear, concise and helpful response.
        Original user request: {user_message}"""
    else:
        prompt = f"""Given the original user request and the results of executing the plan, generate a clear, concise and helpful response.
        
        Original user request: {user_message}
        
        Tool execution results: {str(tool_result)}
        
        Generate a natural, conversational response"""

    try:    
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            #raise an error if the response is not successful
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]
    except Exception as e:
        print("🔍 Unexpected Exception Type:", type(e).__name__)
        print("📜 Exception args:", e.args)
        print("🧵 Full traceback:")
        traceback.print_exc()
        
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint that handles the complete flow."""
    try:
        # 1. Generate plan
        plan = await generate_plan(request.message)
        print("Generated plan:", plan)

        # 2. If no tool needed, generate response directly
        if plan['name'] == 'none':
            user_response = await generate_user_response(request.message, None)
            return ChatResponse(response=user_response)

        # 3. Execute tool
        result = await mcp_client.session.call_tool(
            plan['name'],
            arguments=plan['input']
        )
        print("Tool result",result)
        tool_result = {"result": result.content[0].text}
        print("Tool result:", tool_result)

        # 4. Generate user-friendly response
        user_response = await generate_user_response(request.message, tool_result)
        print("User response:", user_response)
        
        return ChatResponse(response=user_response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """Get list of available tools."""
    try:
        tools = await mcp_client.get_mcp_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9001) 