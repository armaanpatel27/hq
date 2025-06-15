import asyncio
import os
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

#object to interact with the mcp server
class MCPClient:
    def __init__(self):
        #session to interact with the mcp server
        self.session: Optional[ClientSession] = None
        #stack to manage the async context --> correctly close these contexts laster
        self.exit_stack = AsyncExitStack()
        #stdio to read, write to send messages to the mcp server using stdio transport 
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    #attempt to connect to the mcp server
    async def connect_to_server(self, server_script_path: str):
        server_path = os.path.abspath(server_script_path)

        if not os.path.exists(server_path):
            raise FileNotFoundError(f"❌ Server sxcript not found: {server_path}")

        server_params = StdioServerParameters(command="python", args=[server_path])
        #enter_async_context --> adds to stack so can close in correct order later
        stdio_transport = await self.exit_stack.enter_async_context(
            #launches MCP server process that communicates over stdio
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            #creates a session to interact with the mcp server
            ClientSession(self.stdio, self.write)
        )
        #initialize the session
        await self.session.initialize()

    #get the tools that are available in the mcp server
    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        #list tools
        tools_result = await self.session.list_tools()
        #print the tools in order 
        return [
            {

            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema,
                
            }
            for tool in tools_result.tools
        ]
    #cleanup the session
    async def cleanup(self):
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


async def async_main():
    client = MCPClient()
    try:
        await client.connect_to_server("mcp_service/mcp_server.py")
    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        await client.cleanup()

#synchronous main function to run the async code
def main():
    try:
        asyncio.run(async_main())
    except Exception as e:
        print(f"🔥 Uncaught exception during shutdown: {e}")


if __name__ == "__main__":
    main()
