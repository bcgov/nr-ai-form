"""Base evaluator class and constants for consistency."""

import logging
from typing import Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


# Score Definitions (Standard 0.0 - 1.0)
# All evaluators MUST use this standard
SCORE_RANGES = {
    "excellent": (0.8, 1.0),    # ✅ Excellent - meets or exceeds expectations
    "good": (0.6, 0.8),          # ✅ Good - acceptable, minor issues
    "fair": (0.4, 0.6),          # ⚠️ Fair - acceptable but has issues
    "poor": (0.2, 0.4),          # ❌ Poor - significant issues
    "failed": (0.0, 0.2),        # ❌ Failed - critical issues
}

# Error handling defaults
ERROR_SCORE = 0.0  # When evaluator fails, return this score
UNAVAILABLE_SCORE = 0.5  # When evaluator not available, return this score
SKIPPED_SCORE = 1.0  # When evaluation skipped (no input), return this score


class BaseEvaluator(ABC):
    """
    Abstract base class for all evaluators.
    
    Guidelines for creating new evaluators:
    1. Inherit from BaseEvaluator
    2. Implement __init__ with configuration
    3. Implement __call__ with evaluation logic
    4. Always return normalized result dict with score (0.0-1.0)
    5. Use consistent error handling
    6. Document score meaning in docstring
    7. Never hardcode values - use config/settings
    
    Return Format (MUST BE CONSISTENT):
    {
        "score": float,           # 0.0 to 1.0
        "reason": str,            # Why this score
        "metadata": Dict[str, Any] # Additional info (timestamps, details, etc)
    }
    """

    @abstractmethod
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Evaluate and return normalized result.
        
        Returns:
            dict with keys: score (0.0-1.0), reason (str), metadata (dict)
        """
        pass

    @staticmethod
    def normalize_result(score: float, reason: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Normalize evaluator result to standard format.
        
        Args:
            score: Evaluation score (0.0 - 1.0)
            reason: Explanation of score
            metadata: Additional context (optional)
            
        Returns:
            Normalized dict with score, reason, metadata
        """
        # Clamp score to 0.0 - 1.0
        clamped_score = max(0.0, min(1.0, float(score)))
        
        return {
            "score": round(clamped_score, 2),
            "reason": str(reason),
            "metadata": metadata or {},
        }

    @staticmethod
    def handle_error(error: Exception, reason: str = None) -> Dict[str, Any]:
        """
        Standard error handling for all evaluators.
        
        Args:
            error: Exception that occurred
            reason: Optional custom error message
            
        Returns:
            Error result dict
        """
        error_msg = reason or f"Evaluation error: {str(error)}"
        logger.exception("evaluator_error")
        
        return {
            "score": ERROR_SCORE,
            "reason": error_msg,
            "metadata": {"error": str(error), "type": type(error).__name__},
        }

    @staticmethod
    def unavailable() -> Dict[str, Any]:
        """Return result when evaluator is not available."""
        return {
            "score": UNAVAILABLE_SCORE,
            "reason": "Evaluator not available",
            "metadata": {"available": False},
        }

    @staticmethod
    def skipped(reason: str = "Evaluation skipped") -> Dict[str, Any]:
        """Return result when evaluation is skipped."""
        return {
            "score": SKIPPED_SCORE,
            "reason": reason,
            "metadata": {"skipped": True},
        }
