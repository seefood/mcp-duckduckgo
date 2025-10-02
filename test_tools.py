#!/usr/bin/env python3
import json
import asyncio

def test_list_tools():
    # Test the MCP initialization and tool listing sequence
    import subprocess
    import time
    
    def send_command(cmd):
        process = subprocess.Popen(
            ['python', '-m', 'mcp_duckduckgo.main'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=cmd)
        return stdout, stderr
    
    # Initialize
    init_cmd = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"}
        }
    }) + "\n"
    
    # List tools
    tools_cmd = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }) + "\n"
    
    print("Sending initialization...")
    init_response, stderr = send_command(init_cmd)
    print("Init response:", init_response)
    
    time.sleep(0.5)
    
    print("Sending tools/list...")
    tools_response, stderr = send_command(tools_cmd)
    print("Tools response:", tools_response)

if __name__ == "__main__":
    test_list_tools()
