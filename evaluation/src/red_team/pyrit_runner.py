"""PyRIT framework runner for security red-teaming."""

import asyncio
import logging
import os
import json
import sys
import pathlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from io import StringIO

import structlog
from src.config import settings
from src.red_team.custom_backend_target import CustomBackendTarget
from src.red_team.crescendo_step_capture import CrescendoMemoryTracer

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
        
        # Initialize seed datasets path
        try:
            import pyrit
            pyrit_path = pathlib.Path(pyrit.__file__).parent
            self.datasets_path = pyrit_path / "datasets" / "seed_datasets" / "local"
        except Exception as e:
            logger.warning("failed_to_resolve_datasets_path", error=str(e))
            self.datasets_path = None
        
        # Available AIRT seed datasets for attacks
        self.available_seed_datasets = {
            "illegal": "airt/illegal.prompt",
            "violence": "airt/violence.prompt",
            "hate": "airt/hate.prompt",
            "sexual": "airt/sexual.prompt",
            "harassment": "airt/harassment.prompt",
            "scams": "airt/scams.prompt",
            "malware": "airt/malware.prompt",
            "fairness": "airt/fairness.prompt",
            "leakage": "airt/leakage.prompt",
            "misinformation": "airt/misinformation.prompt",
            "harms": "airt/harms.prompt",
            "psychosocial": "airt/psychosocial.prompt",
        }
        
        logger.info("pyrit_runner_initialized", threat_models=self.threat_models, datasets_path=str(self.datasets_path))

    async def initialize_pyrit(self) -> None:
        """Initialize PyRIT framework."""
        try:
            from pyrit.setup import initialize_pyrit_async
            from pyrit.setup.initializers import SimpleInitializer
            
            # Set environment variables for PyRIT
            # SimpleInitializer requires OPENAI_CHAT_ENDPOINT, OPENAI_CHAT_KEY, and OPENAI_CHAT_MODEL
            os.environ["OPENAI_CHAT_ENDPOINT"] = settings.azure_openai_endpoint or "https://dummy.openai.azure.com"
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key or "dummy-key"
            
            # Also set Azure-specific ones for targets that might use them
            if settings.azure_openai_endpoint:
                os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            if settings.azure_openai_api_key:
                os.environ["AZURE_OPENAI_API_KEY"] = settings.azure_openai_api_key
            
            logger.info("initializing_pyrit")
            await initialize_pyrit_async(
                memory_db_type="InMemory",
                initializers=[SimpleInitializer()],
            )
            logger.info("pyrit_initialized")
        except Exception as e:
            logger.error("pyrit_initialization_failed", error=str(e))
            raise

    def _load_seed_datasets(self, dataset_names: Optional[List[str]] = None) -> List[str]:
        """
        Load seed datasets from PyRIT's built-in AIRT collection.
        
        Args:
            dataset_names: List of dataset names to load (e.g., ['illegal', 'violence', 'hate']).
                          If None, loads all available datasets.
        
        Returns:
            List of extracted seed prompts from the datasets
        """
        try:
            from pyrit.models import SeedDataset
            
            if not self.datasets_path:
                logger.warning("datasets_path_not_available")
                return []
            
            # Use provided dataset names or all available ones
            datasets_to_load = dataset_names or list(self.available_seed_datasets.keys())
            
            all_seeds = []
            
            for dataset_name in datasets_to_load:
                if dataset_name not in self.available_seed_datasets:
                    logger.warning("unknown_seed_dataset", dataset_name=dataset_name)
                    continue
                
                dataset_path = self.available_seed_datasets[dataset_name]
                full_path = self.datasets_path / dataset_path
                
                if not full_path.exists():
                    logger.warning("seed_dataset_file_not_found", path=str(full_path))
                    continue
                
                try:
                    logger.info("loading_seed_dataset", dataset_name=dataset_name, path=str(full_path))
                    seed_dataset = SeedDataset.from_yaml_file(full_path)
                    
                    # Extract seed values (prompts) from the dataset
                    dataset_seeds = [seed.value for seed in seed_dataset.seeds if seed.value]
                    all_seeds.extend(dataset_seeds)
                    
                    logger.info("seed_dataset_loaded", 
                               dataset_name=dataset_name, 
                               seed_count=len(dataset_seeds))
                    
                except Exception as e:
                    logger.error("failed_to_load_seed_dataset", 
                                dataset_name=dataset_name,
                                path=str(full_path),
                                error=str(e))
                    continue
            
            logger.info("seed_datasets_loaded", total_seeds=len(all_seeds))
            return all_seeds
            
        except Exception as e:
            logger.error("seed_dataset_loading_failed", error=str(e))
            return []

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
            
            from pyrit.executor.attack import AttackExecutor, PromptSendingAttack, AttackScoringConfig
            
            logger.info("pyrit_attack_start", query=query[:100])
            
            # Determine which target to use: custom backend or Azure OpenAI
            backend_url = settings.backend_api_url
            logger.info("backend_url_check", backend_url=backend_url, is_set=bool(backend_url))
            
            if backend_url and backend_url not in ["http://localhost:8000", ""]:
                # Use custom backend target
                logger.info("using_custom_backend_target", endpoint=backend_url)
                objective_target = CustomBackendTarget(
                    endpoint=backend_url,
                    session_id=None,  # Will be auto-generated
                    step_number=2,
                )
                
                # When using custom backend, disable scoring since it won't have API access
                attack_config = AttackScoringConfig(
                    objective_scorer=None,
                    refusal_scorer=None,
                    use_score_as_feedback=False,
                )
            else:
                # Fall back to Azure OpenAI
                from pyrit.prompt_target import OpenAIChatTarget
                
                endpoint = settings.azure_openai_endpoint
                if not endpoint:
                    raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
                
                # Extract base endpoint for OpenAI (remove any path components)
                base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
                
                api_key = settings.azure_openai_api_key
                if not api_key:
                    raise ValueError("AZURE_OPENAI_API_KEY not configured")
                
                logger.info("using_openai_target", endpoint=base_endpoint)
                objective_target = OpenAIChatTarget(
                    endpoint=base_endpoint,
                    api_key=api_key,
                )
                
                # Use default scoring config for Azure OpenAI
                attack_config = AttackScoringConfig()
            
            # Create attack with objective_target (PromptSendingAttack needs this, not attack_adversarial_config)
            attack = PromptSendingAttack(
                objective_target=objective_target,
                attack_scoring_config=attack_config,
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

    async def run_attack_seed(
        self, 
        seed_datasets: Optional[List[str]] = None,
        limit_seeds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run PyRIT attacks using seed prompts from built-in AIRT seed datasets.
        
        Args:
            seed_datasets: List of seed dataset names to use (e.g., ['illegal', 'violence']).
                          If None, uses default set: ['illegal', 'violence', 'hate', 'sexual']
            limit_seeds: Maximum number of seeds to use per dataset. If None, uses all seeds.
            
        Returns:
            Attack results with metadata and seed dataset information
        """
        try:
            # Initialize PyRIT first
            await self.initialize_pyrit()
            
            # Set environment variables for PyRIT
            os.environ["OPENAI_CHAT_MODEL"] = settings.azure_openai_deployment
            os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint
            os.environ["OPENAI_CHAT_KEY"] = settings.azure_openai_api_key
            
            from pyrit.executor.attack import AttackExecutor, PromptSendingAttack, AttackScoringConfig
            
            # Default seed datasets if not specified
            if seed_datasets is None:
                seed_datasets = ["illegal", "violence", "hate", "sexual"]
            
            logger.info("pyrit_attack_seed_start", 
                       seed_datasets=seed_datasets, 
                       limit_seeds=limit_seeds)
            
            # Load seed datasets
            all_seeds = self._load_seed_datasets(seed_datasets)
            
            if not all_seeds:
                logger.warning("no_seeds_loaded")
                return {
                    "attack_type": "PromptSendingAttack",
                    "seed_datasets": seed_datasets,
                    "error": "No seed datasets could be loaded",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            
            # Apply seed limit if specified
            if limit_seeds is not None:
                all_seeds = all_seeds[:limit_seeds]
            
            logger.info("seeds_ready_for_attack", 
                       total_seeds=len(all_seeds),
                       seed_datasets=seed_datasets)
            
            # Determine which target to use: custom backend or Azure OpenAI
            backend_url = settings.backend_api_url
            logger.info("backend_url_check", backend_url=backend_url, is_set=bool(backend_url))
            
            if backend_url and backend_url not in ["http://localhost:8000", ""]:
                # Use custom backend target
                logger.info("using_custom_backend_target", endpoint=backend_url)
                objective_target = CustomBackendTarget(
                    endpoint=backend_url,
                    session_id=None,  # Will be auto-generated
                    step_number=2,
                )
                
                # When using custom backend, disable scoring since it won't have API access
                attack_config = AttackScoringConfig(
                    objective_scorer=None,
                    refusal_scorer=None,
                    use_score_as_feedback=False,
                )
            else:
                # Fall back to Azure OpenAI as objective
                from pyrit.prompt_target import OpenAIChatTarget
                
                endpoint = settings.azure_openai_endpoint
                if not endpoint:
                    raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
                
                # Extract base endpoint for OpenAI (remove any path components)
                base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
                
                api_key = settings.azure_openai_api_key
                if not api_key:
                    raise ValueError("AZURE_OPENAI_API_KEY not configured")
                
                logger.info("using_openai_target", endpoint=base_endpoint)
                objective_target = OpenAIChatTarget(
                    endpoint=base_endpoint,
                    api_key=api_key,
                )
                
                # Use default scoring config for Azure OpenAI
                attack_config = AttackScoringConfig()
            
            # Create attack with objective_target
            attack = PromptSendingAttack(
                objective_target=objective_target,
                attack_scoring_config=attack_config,
            )
            
            # Execute attack with all seed objectives
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=all_seeds,
            )
            
            logger.info("pyrit_attack_seed_complete", 
                       result_count=len(results) if hasattr(results, 'completed_results') else len([results]))
            
            return {
                "attack_type": "PromptSendingAttack",
                "seed_source": "AIRT Datasets",
                "seed_datasets": seed_datasets,
                "total_seeds_used": len(all_seeds),
                "converters": ["TenseConverter(past)", "TenseConverter(future)"],
                "results": self._format_pyrit_results(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_attack_seed_failed", error=str(e))
            return {
                "attack_type": "PromptSendingAttack",
                "seed_datasets": seed_datasets,
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
            
            logger.info("pyrit_jailbreak_attack_start", query=query[:100])
            
            # Setup objective target (what we're attacking)
            backend_url = settings.backend_api_url
            if backend_url and backend_url not in ["http://localhost:8000", ""]:
                # Use custom backend as objective target
                logger.info("using_custom_backend_target_jailbreak", endpoint=backend_url)
                objective_target = CustomBackendTarget(
                    endpoint=backend_url,
                    session_id=None,
                    step_number=2,
                )
            else:
                # Fall back to Azure OpenAI as objective
                endpoint = settings.azure_openai_endpoint
                if not endpoint:
                    raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
                
                base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
                logger.info("using_openai_target_jailbreak", endpoint=base_endpoint)
                objective_target = OpenAIChatTarget(
                    endpoint=base_endpoint,
                    api_key=settings.azure_openai_api_key,
                )
            
            # Setup adversarial target (Azure OpenAI for generating attacks)
            adversarial_endpoint = settings.adversarial_endpoint or settings.azure_openai_endpoint
            adversarial_api_key = settings.adversarial_api_key or settings.azure_openai_api_key
            adversarial_deployment = settings.adversarial_deployment or settings.azure_openai_deployment
            adversarial_api_version = settings.adversarial_api_version or settings.azure_openai_api_version
            
            if not adversarial_endpoint:
                raise ValueError("ADVERSARIAL_ENDPOINT or AZURE_OPENAI_ENDPOINT not configured")
            if not adversarial_api_key:
                raise ValueError("ADVERSARIAL_API_KEY or AZURE_OPENAI_API_KEY not configured")
            
            # Use custom Azure OpenAI target with proper api-key header authentication
            from .custom_azure_openai_target import CustomAzureOpenAITarget
            
            logger.info(
                "using_custom_azure_openai_target",
                endpoint=adversarial_endpoint,
                deployment=adversarial_deployment,
                api_version=adversarial_api_version,
            )
            
            adversarial_target = CustomAzureOpenAITarget(
                endpoint=adversarial_endpoint,
                api_key=adversarial_api_key,
                deployment=adversarial_deployment,
                api_version=adversarial_api_version,
            )
            
            # Create attack adversarial config with Azure OpenAI as adversarial chat
            from pyrit.executor.attack import AttackAdversarialConfig, AttackScoringConfig
            
            attack_config = AttackAdversarialConfig(
                target=adversarial_target,  # Azure OpenAI generates the attacks
            )
            
            # Crescendo REQUIRES scoring feedback to escalate properly
            # Use default scoring config to enable multi-turn escalation
            # NOTE: For custom backends, the default scorer will still work as it checks if response exists
            scoring_config = AttackScoringConfig(
                use_score_as_feedback=True,  # CRITICAL: Must be True for Crescendo escalation
            )
            
            # Use Crescendo attack (more sophisticated jailbreak attack)
            attack = CrescendoAttack(
                objective_target=objective_target,
                attack_adversarial_config=attack_config,
                attack_scoring_config=scoring_config,
                max_turns=self.max_iterations,
            )
            
            # Execute attack
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=[query],
            )
            
            logger.info("pyrit_jailbreak_attack_complete", result_count=len(results))
            
            # Capture escalation steps from memory (wrapped in try-except to handle missing memory)
            escalation_chains = []
            try:
                from pyrit.memory.central_memory import CentralMemory
                memory = CentralMemory.get_memory_instance()
                tracer = CrescendoMemoryTracer(memory)
                
                # DEBUG: Log raw result structure
                if hasattr(results, 'completed_results'):
                    completed = results.completed_results
                else:
                    completed = results if isinstance(results, list) else [results]
                
                # Extract escalation chain for each result
                for i, result in enumerate(completed):
                    logger.info(f"result_{i}_structure",
                               has_conversation_id=hasattr(result, 'conversation_id'),
                               conversation_id=getattr(result, 'conversation_id', 'N/A'),
                               executed_turns=getattr(result, 'executed_turns', 0),
                               result_type=type(result).__name__)
                    
                    # Try to capture escalation steps
                    conv_id = getattr(result, 'conversation_id', None)
                    if conv_id:
                        escalations = tracer.capture_escalation_chain(str(conv_id))
                        escalation_chains.append({
                            "conversation_id": str(conv_id),
                            "escalations": escalations
                        })
                        logger.info("escalation_chain_captured",
                                   conversation_id=str(conv_id),
                                   escalation_count=len(escalations))
            except Exception as capture_error:
                logger.warning("escalation_capture_failed", error=str(capture_error))
                escalation_chains = []
            
            return {
                "query": query,
                "attack_type": "CrescendoAttack",
                "threat_model": "jailbreak",
                "results": self._format_pyrit_results(results),
                "escalation_steps": escalation_chains,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_jailbreak_attack_failed", error=str(e))
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "escalation_steps": [],
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
            
            logger.info("pyrit_multiturn_attack_start", query=query[:100], max_turns=max_turns)
            
            # Setup objective target (what we're attacking)
            backend_url = settings.backend_api_url
            if backend_url and backend_url not in ["http://localhost:8000", ""]:
                # Use custom backend as objective target
                logger.info("using_custom_backend_target_multiturn", endpoint=backend_url)
                objective_target = CustomBackendTarget(
                    endpoint=backend_url,
                    session_id=None,
                    step_number=2,
                )
            else:
                # Fall back to Azure OpenAI as objective
                endpoint = settings.azure_openai_endpoint
                if not endpoint:
                    raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
                
                base_endpoint = endpoint.split("/wlrs")[0] if "/wlrs" in endpoint else endpoint
                logger.info("using_openai_target_multiturn", endpoint=base_endpoint)
                objective_target = OpenAIChatTarget(
                    endpoint=base_endpoint,
                    api_key=settings.azure_openai_api_key,
                )
            
            # Setup adversarial target (Azure OpenAI for generating attacks)
            adversarial_endpoint = settings.adversarial_endpoint or settings.azure_openai_endpoint
            adversarial_api_key = settings.adversarial_api_key or settings.azure_openai_api_key
            adversarial_deployment = settings.adversarial_deployment or settings.azure_openai_deployment
            adversarial_api_version = settings.adversarial_api_version or settings.azure_openai_api_version
            
            if not adversarial_endpoint:
                raise ValueError("ADVERSARIAL_ENDPOINT or AZURE_OPENAI_ENDPOINT not configured")
            if not adversarial_api_key:
                raise ValueError("ADVERSARIAL_API_KEY or AZURE_OPENAI_API_KEY not configured")
            
            # Use custom Azure OpenAI target with proper api-key header authentication
            from .custom_azure_openai_target import CustomAzureOpenAITarget
            
            logger.info(
                "using_custom_azure_openai_target",
                endpoint=adversarial_endpoint,
                deployment=adversarial_deployment,
                api_version=adversarial_api_version,
            )
            
            adversarial_target = CustomAzureOpenAITarget(
                endpoint=adversarial_endpoint,
                api_key=adversarial_api_key,
                deployment=adversarial_deployment,
                api_version=adversarial_api_version,
            )
            
            # Create attack adversarial config with Azure OpenAI as adversarial chat
            from pyrit.executor.attack import AttackAdversarialConfig, AttackScoringConfig
            
            attack_config = AttackAdversarialConfig(
                target=adversarial_target,  # Azure OpenAI generates the attacks
            )
            
            # RedTeaming REQUIRES an objective scorer in the attack scoring configuration
            # Use SubStringScorer to detect jailbreak success indicators
            from pyrit.score import SubStringScorer
            
            # Score positively if response contains indicators of successful jailbreak
            objective_scorer = SubStringScorer(substring="sorry")
            
            scoring_config = AttackScoringConfig(
                objective_scorer=objective_scorer,
                use_score_as_feedback=False,
            )
            
            # Use RedTeamingAttack (intelligent multi-turn)
            attack = RedTeamingAttack(
                objective_target=objective_target,
                attack_adversarial_config=attack_config,
                attack_scoring_config=scoring_config,
                max_turns=max_turns,
            )
            
            # Execute attack
            executor = AttackExecutor()
            results = await executor.execute_attack_async(
                attack=attack,
                objectives=[query],
            )
            
            logger.info("pyrit_multiturn_attack_complete", result_count=len(results))
            
            # Capture escalation steps from memory (wrapped in try-except to handle missing memory)
            escalation_chains = []
            try:
                from pyrit.memory.central_memory import CentralMemory
                memory = CentralMemory.get_memory_instance()
                tracer = CrescendoMemoryTracer(memory)
                
                # Extract escalation chain for each result
                if hasattr(results, 'completed_results'):
                    completed = results.completed_results
                else:
                    completed = results if isinstance(results, list) else [results]
                
                for result in completed:
                    conv_id = getattr(result, 'conversation_id', None)
                    if conv_id:
                        escalations = tracer.capture_escalation_chain(str(conv_id))
                        escalation_chains.append({
                            "conversation_id": str(conv_id),
                            "escalations": escalations
                        })
            except Exception as capture_error:
                logger.warning("escalation_capture_failed", error=str(capture_error))
                escalation_chains = []
            
            return {
                "query": query,
                "attack_type": "RedTeamingAttack",
                "max_turns": max_turns,
                "results": self._format_pyrit_results(results),
                "escalation_steps": escalation_chains,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            logger.error("pyrit_multiturn_attack_failed", error=str(e))
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "escalation_steps": [],
            }

    async def run_red_team_attack(self, query: str, max_turns: int = 5) -> Dict[str, Any]:
        """
        Run red-teaming attack (alias for run_multi_turn_attack).
        
        Args:
            query: Query to attack
            max_turns: Maximum number of turns
            
        Returns:
            Attack results with turns
        """
        return await self.run_multi_turn_attack(query, max_turns=max_turns)

    @staticmethod
    def _format_pyrit_results(pyrit_results: Any) -> Dict[str, Any]:
        """Format PyRIT attack results for reporting.
        
        Args:
            pyrit_results: AttackExecutorResult containing completed_results
            
        Returns:
            Formatted results with turns containing prompts and responses
        """
        formatted = {
            "total_turns": 0,
            "turns": []
        }
        
        from pyrit.memory.central_memory import CentralMemory
        
        # Handle AttackExecutorResult wrapper
        if hasattr(pyrit_results, 'completed_results'):
            # This is an AttackExecutorResult
            completed = pyrit_results.completed_results
        else:
            # Assume it's a list of results
            completed = pyrit_results if isinstance(pyrit_results, list) else [pyrit_results]
        
        # For multi-turn attacks, extract all turns from conversation history
        all_turns = []
        memory = CentralMemory.get_memory_instance()
        
        for result in completed:
            executed_turns = getattr(result, 'executed_turns', 0)
            outcome = getattr(result, 'outcome', 'unknown')
            
            # For Crescendo/multi-turn attacks, check for adversarial conversation IDs (the escalating attacks)
            adversarial_conv_ids = getattr(result, 'adversarial_chat_conversation_ids', [])
            conversation_id = getattr(result, 'conversation_id', None)
            
            logger.info("attack_result_structure",
                       executed_turns=executed_turns,
                       has_conversation_id=bool(conversation_id),
                       has_adversarial_ids=bool(adversarial_conv_ids),
                       adversarial_id_count=len(adversarial_conv_ids) if adversarial_conv_ids else 0)
            
            # ALWAYS try to get from memory if ANY conversation IDs exist, regardless of executed_turns
            memory_turns_extracted = False
            
            # Try adversarial conversation IDs first (for Crescendo attacks)
            # NOTE: adversarial_chat_conversation_ids may be empty, so we focus on conversation_id
            if adversarial_conv_ids:
                try:
                    logger.info("fetching_adversarial_conversations",
                               conversation_count=len(adversarial_conv_ids))
                    
                    for adv_conv_id in adversarial_conv_ids:
                        messages = memory.get_conversation(conversation_id=str(adv_conv_id))
                        
                        # Extract attack prompts from adversarial conversation
                        user_message = None
                        for msg in messages:
                            role = getattr(msg, 'api_role', getattr(msg, 'role', ''))
                            content = getattr(msg, 'converted_value', '') or getattr(msg, 'original_value', '')
                            
                            if role == 'user':
                                user_message = content
                            elif role == 'assistant' and user_message:
                                # This is a completed adversarial turn
                                turn_data = {
                                    "prompt": str(user_message)[:500],
                                    "response": str(content)[:500],
                                    "outcome": str(outcome),
                                }
                                all_turns.append(turn_data)
                                user_message = None
                    
                    if all_turns:
                        memory_turns_extracted = True
                        logger.info("extracted_adversarial_turns",
                                   turn_count=len(all_turns))
                        
                except Exception as e:
                    logger.warning("adversarial_fetch_failed",
                                  error=str(e),
                                  error_type=type(e).__name__)
            
            # For Crescendo: try objective conversation which contains all interaction turns
            if not memory_turns_extracted and conversation_id and executed_turns > 1:
                try:
                    messages = memory.get_conversation(conversation_id=str(conversation_id))
                    
                    logger.info("fetching_objective_conversation_multiturn",
                               conversation_id=conversation_id,
                               message_count=len(messages),
                               executed_turns=executed_turns)
                    
                    # Extract user/assistant pairs as separate turns
                    user_message = None
                    for msg in messages:
                        role = getattr(msg, 'api_role', getattr(msg, 'role', ''))
                        content = getattr(msg, 'converted_value', '') or getattr(msg, 'original_value', '')
                        
                        if role == 'user':
                            user_message = content
                        elif role == 'assistant' and user_message:
                            turn_data = {
                                "prompt": str(user_message)[:500],
                                "response": str(content)[:500],
                                "outcome": str(outcome),
                            }
                            all_turns.append(turn_data)
                            user_message = None
                    
                    if all_turns:
                        memory_turns_extracted = True
                        logger.info("extracted_objective_turns_multiturn",
                                   turn_count=len(all_turns),
                                   executed_turns=executed_turns)
                        
                except Exception as e:
                    logger.warning("objective_fetch_multiturn_failed",
                                  conversation_id=conversation_id,
                                  error=str(e),
                                  error_type=type(e).__name__)
            
            # If we couldn't get turns from memory, use the fallback (final turn only)
            if not memory_turns_extracted:
                logger.info("using_fallback_formatting",
                           executed_turns=executed_turns,
                           has_conversation_ids=bool(conversation_id or adversarial_conv_ids))
                
                objective = getattr(result, 'objective', '')
                last_response = getattr(result, 'last_response', None)
                response_text = ""
                if last_response:
                    response_text = getattr(last_response, 'converted_value', '') or getattr(last_response, 'original_value', '')
                
                turn_data = {
                    "prompt": str(objective)[:500],
                    "response": str(response_text)[:500],
                    "outcome": str(outcome),
                    "turns_executed": executed_turns,
                }
                
                # Add scoring if available
                last_score = getattr(result, 'last_score', None)
                if last_score:
                    turn_data["score"] = getattr(last_score, 'score_value', None)
                
                # Add error info if present
                error_msg = getattr(result, 'error_message', None)
                if error_msg:
                    turn_data["error"] = error_msg
                
                all_turns.append(turn_data)
        
        # Format turns with numbering and add metadata about total execution
        formatted["total_turns"] = len(all_turns)
        formatted["executed_turns_count"] = 0  # Will track actual execution
        
        for result in completed:
            executed = getattr(result, 'executed_turns', 0)
            if executed > formatted["executed_turns_count"]:
                formatted["executed_turns_count"] = executed
        
        # Add note if more turns were executed than shown in memory
        if formatted["executed_turns_count"] > len(all_turns):
            formatted["note"] = f"Attack executed {formatted['executed_turns_count']} turns but only final result available in memory"
        
        for i, turn_data in enumerate(all_turns, 1):
            turn_data["turn"] = i
            formatted["turns"].append(turn_data)
        
        return formatted

    def save_detailed_results(self, results: List[Dict[str, Any]], output_path: str) -> str:
        """
        Save complete attack results including intermediate escalation steps to JSON.
        
        Args:
            results: List of attack results from scan_test_cases
            output_path: Path to save JSON file
            
        Returns:
            Path to saved file
        """
        import os
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        
        # Build detailed report with all escalation steps
        detailed_report = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "attack_type": self.results.get("attack_type", "unknown"),
                "total_cases": self.results.get("total_cases", 0),
            },
            "attacks": []
        }
        
        for result in results:
            # Build attack entry with all details
            attack_entry = {
                "query": result.get("query", ""),
                "attack_type": result.get("attack_type", ""),
                "threat_model": result.get("threat_model", ""),
                "timestamp": result.get("timestamp", ""),
                "summary": {
                    "total_turns": result.get("results", {}).get("total_turns", 0),
                    "executed_turns": result.get("results", {}).get("executed_turns_count", 0),
                    "note": result.get("results", {}).get("note", ""),
                }
            }
            
            # Add escalation steps if available
            if "escalation_steps" in result and result["escalation_steps"]:
                attack_entry["escalation_chain"] = []
                
                for chain in result["escalation_steps"]:
                    chain_entry = {
                        "conversation_id": chain.get("conversation_id"),
                        "steps": chain.get("escalations", [])
                    }
                    attack_entry["escalation_chain"].append(chain_entry)
            
            # Add final result
            attack_entry["final_result"] = result.get("results", {})
            
            # Add error if present
            if "error" in result:
                attack_entry["error"] = result["error"]
            
            detailed_report["attacks"].append(attack_entry)
        
        # Write to file
        with open(output_path, "w") as f:
            json.dump(detailed_report, f, indent=2, default=str)
        
        logger.info("detailed_results_saved", output_path=output_path)
        return output_path

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
            # NOTE: attack_type parameter explicitly set by user overrides threat_models routing
            if attack_type == "Crescendo":
                result = await self.run_jailbreak_attack(query)
            elif attack_type == "MultiTurn" or attack_type == "RedTeaming":
                result = await self.run_multi_turn_attack(query, max_turns=self.max_iterations)
            else:  # Default to PromptSending (ignore threat_models, use user's explicit choice)
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
