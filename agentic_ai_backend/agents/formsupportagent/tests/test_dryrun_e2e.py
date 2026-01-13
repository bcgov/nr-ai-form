import pytest
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Add the parent directory to sys.path to allow importing formsupportagent
# This ensures that 'import formsupportagent' works correctly during tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from formsupportagent import dryrun

# This suite performs "End-to-End" (E2E) style tests for the dryrun functionality.
# It uses REAL form definition JSON files and REAL prompt template MD files
# from the project, but mocks the Azure OpenAI client to intercept network calls.

@patch("formsupportagent.AzureOpenAIChatClient")
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment"
})
@pytest.mark.asyncio
async def test_dryrun_e2e_industrial_livestock_single_field(mock_client_class, capsys):
    """
    Simulates a query for a single month and verifies the output structure.
    Uses real assets for step3-AddPurpose-Industrial-Livestock.
    """
    # 1. Setup Mock Agent and its response
    mock_agent = MagicMock()
    # Mock response text matching the user's provided example
    response_text = '''```json
{
  "ID": "WSLICUseOfWaterFromMonth_100536333_N0",
  "Description": "during which months do you want to use the water?",
  "SuggestedValue": "July"
}
```'''
    mock_agent.run = AsyncMock(return_value=MagicMock(text=response_text))
    
    # 2. Setup Mock Client to return our Mock Agent
    mock_client_instance = MagicMock()
    mock_client_instance.create_agent.return_value = mock_agent
    mock_client_class.return_value = mock_client_instance

    # 3. Execute dryrun with a query targeting a real step
    await dryrun("step3-AddPurpose-Industrial-Livestock: I need the water from july")
    
    # 4. Verify Output
    captured = capsys.readouterr()
    
    # Check if the correct assets were loaded
    assert "Using form schema: step3-AddPurpose-Industrial-Livestock.json" in captured.out
    assert "Loaded custom instructions from step3-AddPurpose-Industrial-Livestock.md" in captured.out
    assert "User Query is: I need the water from july" in captured.out
    
    # Check if the AI's "Result" was printed
    assert "WSLICUseOfWaterFromMonth_100536333_N0" in captured.out
    assert "July" in captured.out


@patch("formsupportagent.AzureOpenAIChatClient")
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment"
})
@pytest.mark.asyncio
async def test_dryrun_e2e_industrial_livestock_multiple_fields(mock_client_class, capsys):
    """
    Simulates a query for all possible properties and verifies the multi-block JSON output.
    Uses real assets for step3-AddPurpose-Industrial-Livestock.
    """
    mock_agent = MagicMock()
    # Mock response text with multiple JSON blocks
    response_text = '''```json
{
  "ID": "PurposeUseSector_100534931_N0",
  "Description": "what purpose do you want to use the water for?",
  "SuggestedValue": "Industrial"
},
{
  "ID": "WSLICUseOfWaterFromMonth_100536333_N0",
  "Description": "during which months do you want to use the water?",
  "SuggestedValue": "July"
},
{
  "ID": "WSLICUseOfWaterToMonth_100536333_N0",
  "Description": "to",
  "SuggestedValue": "October"
},
{
  "ID": "TypeOfStock_100536098_N0",
  "Description": "type of stock:",
  "SuggestedValue": "Beef"
},
{
  "ID": "WSLICUseOfWaterSeasonal_100536333_N0",
  "Description": "do you want to use the water only seasonally?",
  "SuggestedValue": "Yes"
}
```'''
    mock_agent.run = AsyncMock(return_value=MagicMock(text=response_text))
    
    mock_client_instance = MagicMock()
    mock_client_instance.create_agent.return_value = mock_agent
    mock_client_class.return_value = mock_client_instance

    # Execute
    query = "step3-AddPurpose-Industrial-Livestock: I need the water for my beef from july to october for Industrial purpose. give me all possible properities"
    await dryrun(query)
    
    # Verify
    captured = capsys.readouterr()
    assert "PurposeUseSector_100534931_N0" in captured.out
    assert "Industrial" in captured.out
    assert "TypeOfStock_100536098_N0" in captured.out
    assert "Beef" in captured.out
    assert "WSLICUseOfWaterSeasonal_100536333_N0" in captured.out
    assert "Yes" in captured.out
