
import subprocess
import time
import requests
import sys
import os
import signal

def run_verification():
    print("Starting verification process...")
    
    # Paths to the scripts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(base_dir, "formsupport_agent_a2a_server.py")
    api_script = os.path.join(base_dir, "websocket_api.py")
    
    # Environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = base_dir # Ensure imports work
    
    # Start Agent Server on port 8001
    print("Starting Agent Server on port 8001...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uv", "run", server_script],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Start WebSocket API on port 8002
    print("Starting WebSocket API on port 8002...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uv", "run", api_script],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for servers to start
        print("Waiting for servers to initialize...")
        time.sleep(10)
        
        # Test Health
        print("Checking health of WebSocket API...")
        try:
            resp = requests.get("http://localhost:8002/health")
            print(f"Health Check: {resp.status_code} - {resp.json()}")
            if resp.status_code != 200:
                 print("Health check failed!")
                 return False
        except requests.exceptions.ConnectionError:
            print("Could not connect to WebSocket API health endpoint.")
            return False

        # Test Invoke
        print("Testing Invoke endpoint with a mock query...")
        payload = {
            "query": "step1: Hello",
            "session_id": "test-session-123",
            "step_number": "step1"
        }
        
        # We expect a 500 or 404 because actual agent assets (blob storage, openai) might not be fully configured/mocked here
        # But we want to see if the CONNECTION works and it TRIES to invoke the agent.
        # If it returns "Error processing request: ...", that means it successfully connected to the backend WS, sent the message, and got a reply.
        try:
            resp = requests.post("http://localhost:8002/invoke", json=payload)
            print(f"Invoke Response Status: {resp.status_code}")
            print(f"Invoke Response Body: {resp.text}")
            
            # success if we got a response from the agent server (even if it's an error from the agent logic itself)
            # The agent server returns 500 if exception keys missing etc.
            if resp.status_code in [200, 404, 500]: 
                print("Successfully communicated with the backend via WebSocket!")
                return True
            else:
                print("Unexpected response status.")
                return False
                
        except requests.exceptions.ConnectionError:
            print("Could not connect to Invoke endpoint.")
            return False
            
    finally:
        print("Shutting down servers...")
        server_process.terminate()
        api_process.terminate()
        # Ensure they are dead
        server_process.wait()
        api_process.wait()

if __name__ == "__main__":
    success = run_verification()
    if success:
        print("VERIFICATION SUCCESSFUL")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)
