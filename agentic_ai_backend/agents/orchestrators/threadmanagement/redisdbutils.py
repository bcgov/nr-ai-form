from dotenv import load_dotenv
from agent_framework import AgentSession
from utils.redisservice import RedisService
import os
import re
from .thread_manager_interface import IThreadManager

# Leading "stepN-Name:" prefix the orchestrator prepends to user queries.
_STEP_PREFIX_RE = re.compile(r"^step\d[\w-]*:\s*", re.IGNORECASE)


def _message_role_text(msg) -> tuple[str | None, str]:
    """Extract (role, text) from a MAF Message object or its serialized dict form."""
    if isinstance(msg, dict):
        role = msg.get("role")
        text = " ".join(
            c.get("text", "")
            for c in msg.get("contents", [])
            if isinstance(c, dict) and c.get("type") == "text"
        )
    else:
        role = getattr(msg, "role", None)
        text = getattr(msg, "text", "") or ""
    return role, text.strip()


def _extract_messages(state: dict) -> list:
    """Return the stored message list, tolerating history-provider namespacing.

    Messages may sit directly at ``state["messages"]`` or, more commonly, under a
    history provider's source_id (e.g. ``state["in_memory"]["messages"]``).
    """
    if isinstance(state.get("messages"), list):
        return state["messages"]
    for value in state.values():
        if isinstance(value, dict) and isinstance(value.get("messages"), list):
            return value["messages"]
    return []

load_dotenv()

class redisdbutils(IThreadManager):
    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD")
        ssl = os.getenv("REDIS_SSL", "False").lower() == "true"
        ttl_days = int(os.getenv("REDIS_TTL_DAYS", "14"))
        self.redis_service = RedisService(host=host, port=port, password=password, ssl=ssl, ttl=ttl_days*24*60*60)

    async def get_thread_state(self, thread_id: str, agent):
        session = None
        try:
            # Try to load existing session
            if thread_id:
                print(f"Loading thread {thread_id} from Redis...")
                thread_state = await self.redis_service.load_thread(thread_id)
                if thread_state:
                    print("Thread state found in Redis. Resuming conversation.")
                    session = AgentSession.from_dict(thread_state)
                else:
                    print("Thread state not found in Redis. Creating new thread.")
        
        except Exception as e:
            print(f"Error initializing Redis or loading thread: {e}")

        # Create new session if not loaded
        if session is None:
            print("Creating new thread.")
            session = agent.create_session(session_id=thread_id)
        
        return session

    async def get_history_turns(self, thread_id: str, *, limit: int = 10) -> list[dict]:
        """Return recent user/assistant turns for a thread as plain {role, text} dicts.

        Curated context for cross-agent passing (Option 1): only user/assistant turns,
        most-recent `limit`, tool/system messages dropped. Reads Redis directly and
        tolerates a missing/corrupt thread by returning [].
        """
        if not thread_id:
            return []
        try:
            thread_state = await self.redis_service.load_thread(thread_id)
        except Exception as e:
            print(f"Error loading history from Redis: {e}")
            return []
        if not thread_state:
            return []

        session = AgentSession.from_dict(thread_state)
        messages = _extract_messages(session.state or {})

        turns: list[dict] = []
        for msg in messages:
            role, text = _message_role_text(msg)
            if role not in ("user", "assistant") or not text:
                continue
            if role == "user":
                text = _STEP_PREFIX_RE.sub("", text).strip()
            turns.append({"role": role, "text": text})

        return turns[-limit:]

    async def save_thread_state(self, thread_id: str, thread):
        try:
            state = thread.to_dict()
            await self.redis_service.save_thread(thread_id, state) #setting TTL at Service level
        except Exception as e:
            print(f"Error saving thread state to Redis: {e}")

    @staticmethod
    def _no_answer_key(thread_id: str) -> str:
        return f"noanswer:{thread_id}"

    async def get_no_answer_count(self, thread_id: str) -> int:
        """Return how many consecutive turns this session has failed to produce a real answer."""
        if not thread_id:
            return 0
        return await self.redis_service.get_int(self._no_answer_key(thread_id))

    async def increment_no_answer_count(self, thread_id: str) -> int:
        """Increment and return the consecutive no-answer counter for this session."""
        if not thread_id:
            return 1
        new_count = await self.get_no_answer_count(thread_id) + 1
        await self.redis_service.set_int(self._no_answer_key(thread_id), new_count)
        return new_count

    async def reset_no_answer_count(self, thread_id: str) -> None:
        """Reset the consecutive no-answer counter once a real answer is produced."""
        if thread_id:
            await self.redis_service.set_int(self._no_answer_key(thread_id), 0)

    async def close(self):
        if self.redis_service:
            await self.redis_service.close()
