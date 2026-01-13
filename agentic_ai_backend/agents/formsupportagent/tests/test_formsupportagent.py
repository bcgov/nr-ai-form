import pytest
import os
import sys
# Import MagicMock, patch, mock_open for mocking objects, functions, and files
# Import AsyncMock to mock asynchronous methods that are awaited
from unittest.mock import MagicMock, patch, mock_open, AsyncMock

# Add the parent directory of the current file to sys.path
# This allows the tests to import formsupportagent even if they are in a subfolder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions and classes to be tested from the formsupportagent module
from formsupportagent import (
    extract_step_from_query,
    resolve_agent_assets,
    dryrun,
    FormSupportAgent
)

# --- Test extract_step_from_query ---
# Use parametrize to run the same test function with different input/output combinations
@pytest.mark.parametrize("query, expected_step, expected_query", [
    # Case: Standard colon format with step identifier
    ("step3-Add-Well: my hole in the ground is 50ft deep", "step3-Add-Well", "my hole in the ground is 50ft deep"),
    # Case: Different step name
    ("step2-Eligibility: I am building a transmission line", "step2-Eligibility", "I am building a transmission line"),
    # Case: Long step name
    ("step4-Location-Land-Details-Private-Land: I own this property", "step4-Location-Land-Details-Private-Land", "I own this property"),
    # Case: Query without a colon (no step identifier detected)
    ("No step here", None, "No step here"),
    # Case: Query with a colon but the prefix doesn't start with "step"
    ("Invalid: format", None, "Invalid: format"),
    # Case: Minimal "step" prefix
    ("step: summary only", "step", "summary only"),
    # Case: Uppercase prefix
    ("STEP5-Finish: All done", "STEP5-Finish", "All done"),
])
def test_extract_step_from_query(query, expected_step, expected_query):
    # Call the function with the parametrized query
    step, actual_query = extract_step_from_query(query)
    # Assert that the extracted step identifier matches the expected value
    assert step == expected_step
    # Assert that the cleaned query matches the expected value
    assert actual_query == expected_query

# --- Test resolve_agent_assets ---
# This test verifies that the agent correctly locates JSON and MD files based on a step ID
def test_resolve_agent_assets_success(tmp_path):
    # Setup a temporary directory structure using pytest's tmp_path fixture
    # Create the 'formdefinitions' subdirectory
    form_defs = tmp_path / "formdefinitions"
    form_defs.mkdir()
    # Create a dummy JSON schema file
    (form_defs / "step3-Add-Well.json").touch()
    
    # Create the 'prompttemplates' subdirectory
    prompts = tmp_path / "prompttemplates"
    prompts.mkdir()
    # Create a dummy Markdown prompt template file
    (prompts / "step3-Add-Well.md").touch()
    
    # Mock the internal path resolution in formsupportagent so it uses our tmp_path
    with patch("formsupportagent.os.path.abspath", return_value=str(tmp_path / "formsupportagent.py")), \
         patch("formsupportagent.os.path.dirname", return_value=str(tmp_path)):
        
        # Call the function to resolve assets for a given step ID
        json_path, prompt_path, step_key = resolve_agent_assets("step3-Add-Well")
        
        # Verify that both paths were found and returned
        assert json_path is not None
        assert prompt_path is not None
        # Verify that the paths actually exist in the temp directory
        assert os.path.exists(json_path)
        assert os.path.exists(prompt_path)
        # Verify the filename content to ensure correct mapping
        assert "step3-Add-Well.json" in json_path
        assert "step3-Add-Well.md" in prompt_path
        # Verify the step key returned
        assert step_key == "step3-Add-Well"

# Test case for when requested assets do not exist
def test_resolve_agent_assets_not_found(tmp_path):
    # Create empty directories to simulate missing files
    (tmp_path / "formdefinitions").mkdir()
    (tmp_path / "prompttemplates").mkdir()
    
    # Mock the internal path resolution again
    with patch("formsupportagent.os.path.abspath", return_value=str(tmp_path / "formsupportagent.py")), \
         patch("formsupportagent.os.path.dirname", return_value=str(tmp_path)):
        
        # Call the function with a step identifier that shouldn't match anything
        json_path, prompt_path, step_key = resolve_agent_assets("non-existent")
        # Assert that no paths were returned
        assert json_path is None
        assert prompt_path is None
        # Verify the step key is still returned as requested
        assert step_key == "non-existent"

# --- Test dryrun ---
# Mock the FormSupportAgent class to avoid creating real OpenAI clients during testing
@patch("formsupportagent.FormSupportAgent")
# Mock get_form_context to avoid reading real YAML/JSON form definitions
@patch("formsupportagent.get_form_context")
# Mock resolve_agent_assets to avoid actual file system checks in this flow test
@patch("formsupportagent.resolve_agent_assets")
# Provide mock environment variables required by the dryrun function
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment"
})
# Mark the test as an asynchronous test for pytest-asyncio
@pytest.mark.asyncio
async def test_dryrun_success(mock_resolve, mock_get_context, mock_agent_class):
    # Define what the mock asset resolver should return
    mock_resolve.return_value = ("/path/to/step3.json", "/path/to/step3.md", "step3")
    # Define what the mock form context generator should return
    mock_get_context.return_value = "Mock Form Context"
    
    # Create a mock instance of the agent
    mock_agent_instance = MagicMock()
    # Mock the run method using AsyncMock because it is awaited (returns a coroutine)
    mock_agent_instance.run = AsyncMock(return_value="AI Response")
    # Configure the class mock to return our instance mock when initialized
    mock_agent_class.return_value = mock_agent_instance
    
    # Mock 'open' to simulate reading the prompt template from disk
    with patch("builtins.open", mock_open(read_data="Mock Instructions")):
        # Mock 'print' to suppress console output during the test run
        with patch("builtins.print"):
            # Execute the dryrun function with a sample query
            await dryrun("step3: hello")
        
    # Assert that the asset resolver was called with the correct step ID
    mock_resolve.assert_called_once_with("step3")
    # Assert that get_form_context was called with the path returned by the resolver
    mock_get_context.assert_called_once_with("/path/to/step3.json")
    # Assert that the FormSupportAgent was instantiated
    mock_agent_class.assert_called_once()
    # Assert that the agent's run method was called with the extracted user query
    mock_agent_instance.run.assert_called_once_with("hello")

# Test dryrun behavior when no step identifier is provided
@patch("formsupportagent.resolve_agent_assets")
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment"
})
@pytest.mark.asyncio
async def test_dryrun_no_step(mock_resolve, capsys):
    # Call dryrun with a query that lacks the "stepX:" prefix
    await dryrun("no step here")
    # Read the captured stdout and stderr outputs using the capsys fixture
    captured = capsys.readouterr()
    # Verify that the appropriate warning message was printed to stdout
    assert "WARNING: Step identifier is required" in captured.out

# Test dryrun behavior when assets for a step cannot be found
@patch("formsupportagent.resolve_agent_assets")
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment"
})
@pytest.mark.asyncio
async def test_dryrun_no_assets(mock_resolve, capsys):
    # Configure our mock to simulate "not found" (None paths)
    mock_resolve.return_value = (None, None, "step3")
    # Execute the dryrun function
    await dryrun("step3: hello")
    # Read captured output
    captured = capsys.readouterr()
    # Verify the error message indicating the missing form definition
    assert "Form definition file not found for identifier: step3" in captured.out
