"""Groundedness evaluator adapter for Azure AI Evaluation SDK."""

import logging
from typing import Dict, Any
from azure.ai.evaluation import GroundednessEvaluator
from src.config import settings
from src.evaluators.base import BaseEvaluator, SKIPPED_SCORE

logger = logging.getLogger(__name__)


class AzureGroundednessEvaluatorAdapter(BaseEvaluator):
    """
    Detect hallucinations - ensure response facts match the context.
    
    Uses the official GroundednessEvaluator from azure-ai-evaluation library.
    
    Score Meaning:
    - 1.0 (Excellent): All claims supported by context
    - 0.8 (Good): Most claims supported, minor inferences
    - 0.6 (Fair): Some claims supported, some assumptions
    - 0.4 (Poor): Few facts from context, mostly hallucination
    - 0.2 (Failed): Contradicts context
    - 0.0 (Failed): Complete hallucination or error
    
    Note: No context = skip evaluation (score 1.0)
    """

    def __init__(self, threshold: float = None):
        """
        Initialize groundedness evaluator.
        
        Args:
            threshold: Score threshold for acceptable groundedness (0.0-1.0)
                      If None, uses settings.groundedness_threshold
        """
        self.threshold = threshold or settings.groundedness_threshold
        
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be 0.0-1.0")
        
        self.evaluator = None
        
        try:
            self.evaluator = self._init_evaluator()
            logger.info(
                "groundedness_evaluator_initialized",
                threshold=self.threshold,
                deployment=settings.azure_openai_deployment,
            )
        except ValueError as e:
            logger.warning(f"groundedness_config_missing: {e}")
            raise
        except Exception as e:
            logger.error(f"groundedness_init_failed: {e}")
            raise

    def _init_evaluator(self) -> GroundednessEvaluator:
        """
        Initialize Azure AI GroundednessEvaluator.
        
        Returns:
            Configured GroundednessEvaluator instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        # Validate configuration
        if not settings.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT required")
        if not settings.azure_openai_deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT required")
        if not settings.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY required")
        
        # Initialize evaluator with model configuration
        evaluator = GroundednessEvaluator(
            model_config={
                "api_key": settings.azure_openai_api_key,
                "azure_endpoint": settings.azure_openai_endpoint,
                "azure_deployment": settings.azure_openai_deployment,
                "api_version": settings.azure_openai_api_version,
            }
        )
        
        return evaluator

    def __call__(self, response: str, context: str, **kwargs) -> Dict[str, Any]:
        """
        Evaluate groundedness of response against context.
        
        Args:
            response: The AI-generated response to evaluate
            context: Reference context/ground truth
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Normalized evaluation result with score, reason, metadata
        """
        if not self.evaluator:
            return self.handle_error(
                ValueError("Evaluator not initialized"),
                "GroundednessEvaluator initialization failed"
            )
        
        # Skip if no context or response
        if not context or not response:
            return self.normalize_result(
                score=SKIPPED_SCORE,
                reason="No context or response provided - skipped",
                metadata={"skipped": True}
            )
        
        try:
            # Call Azure AI GroundednessEvaluator
            result = self.evaluator(response=response, context=context)
            
            # Extract score from result
            # Azure AI evaluators typically return dict with 'gpt_groundedness' key
            score = result.get("gpt_groundedness", 0.0)
            
            # Determine pass/fail based on threshold
            passed = score >= self.threshold
            category = self._categorize_score(score)
            
            return self.normalize_result(
                score=score,
                reason=f"Groundedness score: {score:.2f} - {category} ({'Pass' if passed else 'Fail'})",
                metadata={
                    "threshold": self.threshold,
                    "passed": passed,
                    "category": category,
                    "raw_result": result,
                }
            )
            
        except Exception as e:
            return self.handle_error(e, f"Groundedness evaluation failed: {str(e)}")

    @staticmethod
    def _categorize_score(score: float) -> str:
        """Categorize score into human-readable category."""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        elif score >= 0.2:
            return "poor"
        else:
            return "failed"
