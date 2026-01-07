import pytest
import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load real environment variables from .env
# This will provide AZURE_OPENAI_ENDPOINT, API_KEY, and DEPLOYMENT_NAME
load_dotenv()

from formsupportagent import dryrun

# This suite performs LIVE Integration tests.
# It will call the actual Azure OpenAI model.
# NOTE: This requires a valid .env file in the formsupportagent directory.
#
# To run this test and see all output (including passed tests), use:
# uv run python -m pytest -v -rA .\tests\test_dryrun_integration.py

@pytest.mark.asyncio
async def test_dryrun_live_industrial_livestock(capsys):
    """
    Live test against the actual model for a complex query.
    Verifies that the model understands the prompt and returns a valid JSON structure.
    """
    # Verify environment is set
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        pytest.skip("AZURE_OPENAI_API_KEY not found in environment. Skipping live test.")

    # Execute real dryrun
    query = "step3-AddPurpose-Industrial-Livestock: I need the water for my beef from july to october"
    await dryrun(query)
    
    # Capture output
    captured = capsys.readouterr()
    # Assert on the print statements (generic logic)
    assert "Using form schema" in captured.out
    assert "Result:" in captured.out
    
    # Assert that we got some JSON-like blocks in the output
    # Since the model is non-deterministic, we check for expected key identifiers
    assert "ID" in captured.out
    assert "SuggestedValue" in captured.out
    
    # Check for specific IDs that should be in step3-AddPurpose-Industrial-Livestock
    # Based on user's sample output
    assert "WSLICUseOfWaterFromMonth" in captured.out
    assert "July" in captured.out
    assert "October" in captured.out

@pytest.mark.asyncio
async def test_dryrun_live_eligibility(capsys):
    """
    Live test for a different step to ensure generic prompting works.
    """
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        pytest.skip("AZURE_OPENAI_API_KEY not found in environment. Skipping live test.")

    # Execute
    await dryrun("step2-Eligibility: I am a non-profit organization")
    
    captured = capsys.readouterr()
    assert "Using form schema: step2-Eligibility.json" in captured.out
    assert "Result:" in captured.out
    # Expected field for eligibility might include applicant type or similar
    assert "ID" in captured.out
