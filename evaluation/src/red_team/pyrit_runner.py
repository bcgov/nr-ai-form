"""PyRIT framework runner for security red-teaming."""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import structlog
from src.config import settings

logger = structlog.get_logger(__name__)


class PyRITRunner:
    """Run PyRIT attacks using the full framework."""

    def __init__(
        self,
        threat_models: Optional[List[str]] = None,
        max_iterations: int = 5,
        verbose: bool = False,
    ):
        """
        Initialize PyRIT runner.
        
        Args:
            threat_models: List of threat models (jailbreak, prompt_injection, data_exfiltration)
            max_iterations: Max iterations per attack
            verbose: Enable verbose output
        """
        self.threat_models = threat_models or ["jailbreak", "prompt_injection", "data_exfiltration"]
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.results: Dict[str, Any] = {}
        
        logger.info("pyrit_runner_initialized", threat_models=self.threat_models)

    async def initialize_pyrit(self) -> None:
        """Initialize PyRIT framework."""
        try:
            from pyrit.setup import initialize_pyrit_async
            from pyrit.setup.initializers import SimpleInitializer
            
            # Set environment variables for PyRIT
            # SimpleInitializer requires these
            os.environ["OPENAI_CHAT_ENDPOINT"] = settings.azure_openai_endpoint
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key
            
            # Also set Azure-specific ones for targets
            os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            
            logger.info("initializing_pyrit")
            await initialize_pyrit_async(
                memory_db_type="InMemory",
                initializers=[SimpleInitializer()],
            )
            logger.info("pyrit_initialized")
        except Exception as e:
            logger.error("pyrit_initialization_failed", error=str(e))
            raise

    async def run_attack(self, query: str, objective_response: Optional[str] = None) -> Dict[str, Any]:
        """
        Run PyRIT attacks against a query/response pair.
        
        Args:
            query: Original user query
            objective_response: Optional response to test (if None, we test if query causes jailbreak)
            
        Returns:
            Attack results with metadata
        """
        try:
            # Initialize PyRIT first
            await self.initialize_pyrit()
            
            # Set environment variables for PyRIT
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key
            
            from pyrit.executor.attack import AttackExecutor, PromptSendingAttack
            from pyrit.prompt_target import OpenAIChatTarget
            
            endpoint = settings.azure_openai_endpoint
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
            
            # Extract base endpoint for OpenAI (remove any path components)
            base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
            
            api_key = settings.azure_openai_api_key
            if not api_key:
                raise ValueError("AZURE_OPENAI_API_KEY not configured")
            
            logger.info("pyrit_attack_start", query=query[:100])
            
            # Create objective target (your backend API or OpenAI)
            objective_target = OpenAIChatTarget(
                endpoint=base_endpoint,
                api_key=api_key,
            )
            
            # Create attack with objective_target (PromptSendingAttack needs this, not attack_adversarial_config)
            attack = PromptSendingAttack(
                objective_target=objective_target,
            )
            
            # Execute attack
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=[query],
            )
            
            logger.info("pyrit_attack_complete", result_count=len(results))
            
            return {
                "query": query,
                "attack_type": "PromptSendingAttack",
                "converters": ["TenseConverter(past)", "TenseConverter(future)"],
                "results": self._format_pyrit_results(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_attack_failed", error=str(e), query=query[:100])
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def run_jailbreak_attack(self, query: str) -> Dict[str, Any]:
        """Run jailbreak-specific attack using PyRIT."""
        try:
            # Initialize PyRIT first
            await self.initialize_pyrit()
            
            # Set environment variables
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key
            
            from pyrit.executor.attack import AttackExecutor, CrescendoAttack
            from pyrit.prompt_target import OpenAIChatTarget
            
            endpoint = settings.azure_openai_endpoint
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
            
            # Extract base endpoint
            base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
            
            logger.info("pyrit_jailbreak_attack_start", query=query[:100])
            
            # Create objective target
            objective_target = OpenAIChatTarget(
                endpoint=base_endpoint,
                api_key=settings.azure_openai_api_key,
            )
            
            # Create attack adversarial config for Crescendo attack
            from pyrit.executor.attack import AttackAdversarialConfig
            
            attack_config = AttackAdversarialConfig(
                target=objective_target,
            )
            
            # Use Crescendo attack (more sophisticated jailbreak attack)
            attack = CrescendoAttack(
                objective_target=objective_target,
                attack_adversarial_config=attack_config,
                max_turns=self.max_iterations,
            )
            
            # Execute attack
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=[query],
            )
            
            logger.info("pyrit_jailbreak_attack_complete", result_count=len(results))
            
            return {
                "query": query,
                "attack_type": "CrescendoAttack",
                "threat_model": "jailbreak",
                "results": self._format_pyrit_results(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_jailbreak_attack_failed", error=str(e))
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def run_multi_turn_attack(self, query: str, max_turns: int = 5) -> Dict[str, Any]:
        """
        Run multi-turn red-team attack using PyRIT's RedTeamingAttack.
        
        Args:
            query: Objective query
            max_turns: Maximum conversation turns
            
        Returns:
            Attack results
        """
        try:
            # Initialize PyRIT first
            await self.initialize_pyrit()
            
            # Set environment variables
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key
            
            from pyrit.executor.attack import AttackExecutor, RedTeamingAttack
            from pyrit.prompt_target import OpenAIChatTarget
            
            endpoint = settings.azure_openai_endpoint
            if not endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
            
            # Extract base endpoint
            base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
            
            logger.info("pyrit_multiturn_attack_start", query=query[:100], max_turns=max_turns)
            
            # Create objective target
            objective_target = OpenAIChatTarget(
                endpoint=base_endpoint,
                api_key=settings.azure_openai_api_key,
            )
            
            # Create attack adversarial config for RedTeaming attack
            from pyrit.executor.attack import AttackAdversarialConfig
            
            attack_config = AttackAdversarialConfig(
                target=objective_target,
            )
            
            # Use RedTeamingAttack (intelligent multi-turn)
            attack = RedTeamingAttack(
                objective_target=objective_target,
                attack_adversarial_config=attack_config,
                max_turns=max_turns,
            )
            
            # Execute attack
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=[query],
            )
            
            logger.info("pyrit_multiturn_attack_complete", result_count=len(results))
            
            return {
                "query": query,
                "attack_type": "RedTeamingAttack",
                "max_turns": max_turns,
                "results": self._format_pyrit_results(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_multiturn_attack_failed", error=str(e))
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def _format_pyrit_results(pyrit_results: List[Any]) -> Dict[str, Any]:
        """Format PyRIT attack results for reporting."""
        formatted = {
            "total_turns": len(pyrit_results),
            "turns": []
        }
        
        for i, result in enumerate(pyrit_results, 1):
            turn_data = {
                "turn": i,
                "prompt": str(result.prompt) if hasattr(result, "prompt") else "",
                "response": str(result.response) if hasattr(result, "response") else "",
            }
            
            # Add scoring if available
            if hasattr(result, "score"):
                turn_data["score"] = result.score
            
            formatted["turns"].append(turn_data)
        
        return formatted

    async def scan_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
        attack_type: str = "PromptSending"
    ) -> List[Dict[str, Any]]:
        """
        Scan multiple test cases using specified attack type.
        
        Args:
            test_cases: List of test cases with 'query' field
            attack_type: Type of attack (PromptSending, Crescendo, RedTeaming, MultiTurn)
            
        Returns:
            List of attack results
        """
        await self.initialize_pyrit()
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            query = test_case.get("query", "")
            case_name = test_case.get("name", f"case_{i}")
            
            logger.info(
                "scanning_test_case",
                case_number=i,
                total=len(test_cases),
                case_name=case_name,
                attack_type=attack_type
            )
            
            # Run appropriate attack based on type
            if attack_type == "Crescendo" or "jailbreak" in test_case.get("threat_models", []):
                result = await self.run_jailbreak_attack(query)
            elif attack_type == "MultiTurn" or attack_type == "RedTeaming":
                result = await self.run_multi_turn_attack(query, max_turns=self.max_iterations)
            else:  # Default to PromptSending
                result = await self.run_attack(query)
            
            results.append(result)
            
            # Delay between tests
            if i < len(test_cases):
                await asyncio.sleep(1)
        
        self.results = {
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "attack_type": attack_type,
            "total_cases": len(test_cases),
            "results": results,
        }
        
        logger.info("security_scan_complete", total_results=len(results))
        return results
