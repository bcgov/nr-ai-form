"""Capture intermediate escalation steps from Crescendo attacks."""

import json
import logging
from typing import List, Dict, Any
from io import StringIO
import structlog


class CrescendoStepCapture:
    """Capture intermediate escalation steps from Crescendo attacks."""
    
    def __init__(self):
        """Initialize step capture."""
        self.steps: List[Dict[str, Any]] = []
        self.current_step = 0
        self.log_stream = StringIO()
        self.log_handler = None
        
    def start_capture(self):
        """Start capturing logs."""
        # Setup log capturing
        self.log_stream = StringIO()
        self.log_handler = logging.StreamHandler(self.log_stream)
        self.log_handler.setLevel(logging.DEBUG)
        
        # Add handler to PyRIT loggers
        pyrit_logger = logging.getLogger("pyrit")
        pyrit_logger.addHandler(self.log_handler)
        pyrit_logger.setLevel(logging.DEBUG)
        
    def stop_capture(self) -> List[Dict[str, Any]]:
        """Stop capturing and extract steps."""
        if self.log_handler:
            log_output = self.log_stream.getvalue()
            self._parse_log_output(log_output)
            
            # Remove handler
            pyrit_logger = logging.getLogger("pyrit")
            pyrit_logger.removeHandler(self.log_handler)
        
        return self.steps
    
    def _parse_log_output(self, log_output: str):
        """Parse PyRIT log output to extract escalation steps."""
        lines = log_output.split('\n')
        
        step_num = 0
        for line in lines:
            # Look for escalation indicators
            if 'attack' in line.lower() and 'prompt' in line.lower():
                self.steps.append({
                    "step": step_num,
                    "log_entry": line.strip()
                })
                step_num += 1
            elif 'response' in line.lower() or 'generated' in line.lower():
                if self.steps:
                    self.steps[-1]["response"] = line.strip()
    
    def add_step(self, step_num: int, prompt: str, response: str = "", metadata: Dict = None):
        """Manually add a captured step."""
        step_data = {
            "step": step_num,
            "prompt": prompt,
            "response": response,
        }
        if metadata:
            step_data.update(metadata)
        self.steps.append(step_data)


class CrescendoMemoryTracer:
    """Trace Crescendo execution by monitoring memory changes."""
    
    def __init__(self, memory):
        """Initialize memory tracer."""
        self.memory = memory
        self.initial_conversations = set()
        self.escalation_steps: List[Dict[str, Any]] = []
        
    def snapshot_initial_state(self):
        """Take initial snapshot of conversations."""
        try:
            # Get initial message pieces
            pieces = self.memory.get_message_pieces()
            self.initial_conversations = {str(p.conversation_id) for p in pieces}
        except Exception as e:
            print(f"Error snapshotting initial state: {e}")
    
    def capture_escalation_chain(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Extract escalation chain from conversation.
        
        For Crescendo, each "turn" in the objective conversation represents
        the cumulative state after all internal escalations led to this prompt.
        """
        try:
            getter = getattr(self.memory, "get_conversation_messages", None) or self.memory.get_conversation
            messages = getter(conversation_id=conversation_id)
            
            escalations = []
            user_prompts = []
            
            for msg in messages:
                role = getattr(msg, 'api_role', getattr(msg, 'role', ''))
                content = getattr(msg, 'converted_value', '') or getattr(msg, 'original_value', '')
                
                if role == 'user':
                    user_prompts.append(content)
                elif role == 'assistant' and user_prompts:
                    # Create escalation entry for this user/assistant pair
                    escalations.append({
                        "escalation_step": len(escalations) + 1,
                        "prompt": str(user_prompts[-1])[:500],
                        "response": str(content)[:500],
                    })
            
            return escalations
            
        except Exception as e:
            print(f"Error capturing escalation chain: {e}")
            return []


def extract_crescendo_escalations_from_log(log_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Extract Crescendo escalation steps from structured log output.
    
    Crescendo logs typically include:
    - Generated questions at each iteration
    - Rationale behind each escalation
    - Scores/feedback at each step
    """
    escalations = []
    current_escalation = None
    step_num = 0
    
    for line in log_lines:
        line_lower = line.lower()
        
        # Detect new escalation step
        if 'generated_question' in line_lower or 'escalation' in line_lower:
            if current_escalation:
                escalations.append(current_escalation)
            
            step_num += 1
            current_escalation = {
                "escalation_step": step_num,
                "prompt": "",
                "rationale": "",
                "score": "",
            }
        
        # Extract prompt/question
        if current_escalation and 'generated_question' in line_lower:
            # Extract the question from the line
            try:
                # Assume format: ...generated_question: "..."
                if '":' in line:
                    content = line.split('"')
                    if len(content) > 1:
                        current_escalation["prompt"] = content[1][:500]
            except:
                pass
        
        # Extract rationale
        if current_escalation and 'rationale_behind_jailbreak' in line_lower:
            try:
                if '":' in line:
                    content = line.split('"')
                    if len(content) > 1:
                        current_escalation["rationale"] = content[1][:500]
            except:
                pass
        
        # Extract score
        if current_escalation and 'score' in line_lower:
            try:
                current_escalation["score"] = line.split(':')[-1].strip()[:100]
            except:
                pass
    
    if current_escalation:
        escalations.append(current_escalation)
    
    return escalations
