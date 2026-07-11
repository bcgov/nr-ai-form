# PyRIT Custom Backend Target Guide

## Overview

`CustomBackendTarget` is a PyRIT `PromptTarget` implementation that enables red-teaming attacks against your custom backend API instead of Azure OpenAI or other public endpoints.

This guide explains:
1. How CustomBackendTarget works
2. How to configure it for your API
3. The API contract it expects
4. How to extend or modify it for your needs

## Architecture

```
PyRIT Attack Strategy (e.g., CrescendoAttack)
    ↓
    PyRIT Executor
    ↓
    CustomBackendTarget (extends PromptTarget)
    ↓
    Your Backend API (/invoke endpoint)
    ↓
    Returns structured response
    ↓
    Message extracted and returned to PyRIT
```

## How It Works

### 1. Initialization

```python
from src.red_team.custom_backend_target import CustomBackendTarget

target = CustomBackendTarget(
    endpoint="https://your-api.com/invoke",
    session_id="unique-session-id",
    step_number=2
)
```

**Parameters:**
- `endpoint`: Full URL to your backend's invoke endpoint
- `session_id`: Session identifier for tracking (auto-generated UUID if None)
- `step_number`: Form step or context number (default: 2)

### 2. Attack Execution Flow

When PyRIT executes an attack:

1. **Message Extraction**: Gets the last user message from PyRIT's conversation
   ```python
   last_message = [msg for msg in normalized_conversation if msg.api_role == "user"][-1]
   prompt = str(last_message.get_value())
   ```

2. **Request Construction**: Builds JSON payload matching your API contract
   ```python
   request_payload = {
       "query": prompt,                    # The attack prompt
       "session_id": self.session_id,      # Session tracking
       "step_number": str(self.step_number)
   }
   ```

3. **HTTP Communication**: Sends POST request with 30s timeout
   ```python
   async with aiohttp.ClientSession() as session:
       async with session.post(
           self.endpoint,
           json=request_payload,
           timeout=aiohttp.ClientTimeout(total=30)
       ) as response:
   ```

4. **Response Parsing**: Extracts text from nested response structure
   ```python
   response_json = await response.json()
   # Navigate: response["response"][0]["response"]
   response_text = response_json["response"][0]["response"]
   ```

5. **Message Creation**: Returns PyRIT Message object
   ```python
   return [Message.from_prompt(response_text, role="assistant")]
   ```

## API Contract

Your backend must implement the `/invoke` endpoint with this contract:

### Request Format

```json
POST /invoke
Content-Type: application/json

{
  "query": "string - the attack prompt/question",
  "session_id": "string - UUID for session tracking",
  "step_number": "string - form step or context number"
}
```

**Example:**
```bash
curl -X POST https://your-api.com/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the application fee?",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "step_number": "2"
  }'
```

### Response Format

```json
{
  "response": [
    {
      "source": "string - where answer came from (optional)",
      "response": "string - the actual answer text"
    }
  ],
  "session_id": "string - echoed session ID"
}
```

**Example:**
```json
{
  "response": [
    {
      "source": "knowledge-base",
      "response": "The application fee for a new water licence is a one-time fee with a minimum of $250."
    }
  ],
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Handling

If your backend returns an error response:
- Still return HTTP 200 with error details in response
- CustomBackendTarget will extract error text and return as response
- PyRIT treats it as a valid response (not an error)

```json
{
  "response": [
    {
      "source": "error",
      "response": "Error: Invalid query format"
    }
  ],
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Configuration

### 1. Environment Setup

Set the backend URL in your environment:

```bash
# In .env file
export BACKEND_API_URL=https://your-api.com/invoke
```

### 2. Application Code

In `pyrit_runner.py`, the framework automatically detects and uses CustomBackendTarget:

```python
if settings.backend_api_url:
    # Use custom backend
    target = CustomBackendTarget(
        endpoint=settings.backend_api_url,
        session_id=session_id
    )
else:
    # Fall back to Azure OpenAI
    target = OpenAIChatTarget(...)
```

No code changes needed - just set `BACKEND_API_URL` in environment!

## Integration with Attack Strategies

### PromptSending Attack

```python
attack = PromptSendingAttack(
    prompt_target=target,          # Your CustomBackendTarget
    converters=[...],               # Text converters (tense, etc.)
    attack_scoring_config=AttackScoringConfig(
        objective_scorer=None,      # Disable scoring
        refusal_scorer=None,
        use_score_as_feedback=False
    )
)
```

### Crescendo Attack (Jailbreak)

```python
attack = CrescendoAttack(
    prompt_target=target,
    adversarial_config=AttackAdversarialConfig(...),
    attack_scoring_config=AttackScoringConfig(
        objective_scorer=None,
        refusal_scorer=None,
        use_score_as_feedback=False
    )
)
```

### RedTeaming Attack (Intelligent Multi-turn)

```python
attack = RedTeamingAttack(
    prompt_target=target,
    attack_strategy=...,
    attack_scoring_config=AttackScoringConfig(
        objective_scorer=None,
        refusal_scorer=None,
        use_score_as_feedback=False
    )
)
```

**Important**: Always disable scoring when using CustomBackendTarget, as scoring would try to call Azure OpenAI which is not available for custom backends.

## Key Implementation Details

### Message API

PyRIT Messages have important attributes:
- `msg.api_role`: The role ("user", "assistant", "system", "tool")
- `msg.get_value()`: Get message text content
- `Message.from_prompt(text, role)`: Create a new Message

```python
# ✅ CORRECT
if msg.api_role == "user":
    prompt = str(msg.get_value())

# ❌ INCORRECT
if msg.role == "user":  # AttributeError: no 'role' attribute
    prompt = str(msg.prompt)  # AttributeError: no 'prompt' attribute
```

### Async Communication

CustomBackendTarget uses async/await for non-blocking HTTP:

```python
async with aiohttp.ClientSession() as session:
    async with session.post(...) as response:
        response_json = await response.json()
```

This allows PyRIT to manage multiple concurrent attacks efficiently.

### Response Extraction

The `_extract_response()` method navigates the nested structure:

```python
def _extract_response(self, response_data: dict) -> str:
    """Navigate nested aggregator response structure."""
    try:
        responses = response_data.get("response", [])
        if responses and len(responses) > 0:
            return responses[0].get("response", "No response")
        return "Empty response"
    except (KeyError, TypeError, IndexError) as e:
        return f"Error parsing response: {str(e)}"
```

This handles the specific structure your backend returns.

## Extending CustomBackendTarget

### Adding Custom Headers

```python
class AuthenticatedBackendTarget(CustomBackendTarget):
    def __init__(self, endpoint: str, api_key: str, **kwargs):
        super().__init__(endpoint, **kwargs)
        self.api_key = api_key
    
    async def _send_prompt_to_target_async(self, *, normalized_conversation):
        # Add authentication
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                json=payload,
                headers=headers
            ) as response:
                # ... rest of implementation
```

### Custom Request Format

```python
class CustomFormatTarget(CustomBackendTarget):
    async def _send_prompt_to_target_async(self, *, normalized_conversation):
        # Extract message as before
        prompt = str(last_message.get_value())
        
        # Custom format
        request_payload = {
            "input": prompt,
            "context": {
                "session": self.session_id,
                "step": int(self.step_number)
            }
        }
        
        # ... send and parse response
```

### Response Processing

```python
class ProcessingTarget(CustomBackendTarget):
    def _extract_response(self, response_data: dict) -> str:
        # Custom parsing logic
        if "results" in response_data:
            return response_data["results"]["answer"]
        elif "data" in response_data:
            return response_data["data"]["text"]
        else:
            return str(response_data)
```

## Debugging

### Enable Debug Logging

```bash
# Set structlog level to debug
export LOG_LEVEL=debug

python -m src.red_team.cli test-query -q "Your query"
```

### Check HTTP Traffic

Add logging in CustomBackendTarget:

```python
logger.info("sending_request", endpoint=self.endpoint, payload=request_payload)
logger.info("response_received", status=response.status, data=response_json)
```

### Verify Backend Accessibility

```bash
# Test endpoint directly
curl -X POST https://your-api.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"query":"test","session_id":"test","step_number":"2"}'
```

## Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `ConnectError: All connection attempts failed` | Backend unreachable | Verify endpoint URL and network connectivity |
| `Invalid JSON response` | Backend returns non-JSON | Check response format matches contract |
| Empty prompt/response in reports | Message extraction failed | Verify normalized_conversation structure |
| Timeout errors | Backend slow to respond | Increase timeout or optimize backend |
| `AttributeError: no 'role' attribute` | Using wrong message API | Use `msg.api_role` not `msg.role` |

## Performance Considerations

### Concurrency
- PyRIT runs attacks asynchronously for efficiency
- CustomBackendTarget uses async/await for non-blocking I/O
- Multiple queries can be in-flight simultaneously

### Timeout Handling
- HTTP timeout: 30 seconds (configurable in code)
- If backend times out, CustomBackendTarget returns error text
- PyRIT handles timeouts gracefully

### Scaling
- For high-concurrency attacks, ensure backend can handle:
  - Multiple concurrent requests
  - Proper connection pooling
  - Resource limits (CPU, memory, database connections)

## Examples

### Basic Usage

```python
from src.red_team.custom_backend_target import CustomBackendTarget
from pyrit.executor.attack import PromptSendingAttack

target = CustomBackendTarget(endpoint="https://your-api.com/invoke")

attack = PromptSendingAttack(
    prompt_target=target,
    converters=[...]
)

results = await attack.execute_attack_async(...)
```

### With Session Tracking

```python
import uuid

session_id = str(uuid.uuid4())

target = CustomBackendTarget(
    endpoint="https://your-api.com/invoke",
    session_id=session_id,
    step_number=2
)

# All requests in this attack will use same session_id
```

### Error Handling

```python
try:
    target = CustomBackendTarget(endpoint=settings.backend_api_url)
    results = await attack.execute_attack_async(...)
except Exception as e:
    logger.error("Attack failed", error=str(e))
    # Handle gracefully
```

## References

- [CustomBackendTarget Source Code](../evaluation/src/red_team/custom_backend_target.py)
- [PyRIT PromptTarget Base Class](https://github.com/Azure/PyRIT/blob/main/pyrit/prompt_target/prompt_target.py)
- [PyRIT Quick Reference](./PYRIT_QUICK_REFERENCE.md)
- [PyRIT Setup Guide](./PYRIT_SETUP_GUIDE.md)
