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
def test_resolve_agent_assets_success():
    form_definition_service = MagicMock()
    prompt_template_service = MagicMock()
    form_definition_service.fetch_form_definition.return_value = {"fields": []}
    prompt_template_service.fetch_prompt_template.return_value = "Prompt template"

    form_definition, prompt_template, step_key = resolve_agent_assets(
        "step3-Add-Well",
        form_definition_service=form_definition_service,
        prompt_template_service=prompt_template_service,
    )

    assert form_definition == {"fields": []}
    assert prompt_template == "Prompt template"
    assert step_key == "step3-Add-Well"
    form_definition_service.fetch_form_definition.assert_called_once_with("step3-Add-Well.json")
    prompt_template_service.fetch_prompt_template.assert_called_once_with("step3-Add-Well.md")

def test_resolve_agent_assets_not_found():
    form_definition_service = MagicMock()
    prompt_template_service = MagicMock()
    form_definition_service.fetch_form_definition.return_value = None
    prompt_template_service.fetch_prompt_template.return_value = None

    form_definition, prompt_template, step_key = resolve_agent_assets(
        "non-existent",
        form_definition_service=form_definition_service,
        prompt_template_service=prompt_template_service,
    )

    assert form_definition is None
    assert prompt_template is None
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
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "mock-version",
    "AZURE_BLOBSTORAGE_CONNECTIONSTRING": "",
    "AZURE_BLOBSTORAGE_CONTAINER": ""
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
    mock_resolve.assert_called_once_with(
        "step3",
        form_definition_service=None,
        prompt_template_service=None,
    )
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
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "mock-version",
    "AZURE_BLOBSTORAGE_CONNECTIONSTRING": "",
    "AZURE_BLOBSTORAGE_CONTAINER": ""
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
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "mock-version",
    "AZURE_BLOBSTORAGE_CONNECTIONSTRING": "",
    "AZURE_BLOBSTORAGE_CONTAINER": ""
})
@pytest.mark.asyncio
async def test_dryrun_no_assets(mock_resolve, capsys):
    # Configure our mock to simulate "not found" (None paths)
    mock_resolve.return_value = (None, None, "step3")
    # Execute the dryrun function
    await dryrun("step3: hello")
    # Read captured output
    captured = capsys.readouterr()
    # Verify the error message indicating the missing prompt template
    assert "No prompt template" in captured.out


@patch("formsupportagent.FormSupportAgent")
@patch("formsupportagent.resolve_agent_assets")
@patch.dict(os.environ, {
    "AZURE_OPENAI_ENDPOINT": "http://mock-endpoint",
    "AZURE_OPENAI_API_KEY": "mock-key",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": "mock-deployment",
    "AZURE_OPENAI_API_VERSION": "mock-version",
    "AZURE_BLOBSTORAGE_CONNECTIONSTRING": "",
    "AZURE_BLOBSTORAGE_CONTAINER": ""
})
@pytest.mark.asyncio
async def test_dryrun_prompt_only_step(mock_resolve, mock_agent_class, capsys):
    mock_resolve.return_value = (None, "/path/to/step3.md", "step3")
    mock_agent_instance = MagicMock()
    mock_agent_instance.run = AsyncMock(return_value="AI Response")
    mock_agent_class.return_value = mock_agent_instance

    with patch("builtins.open", mock_open(read_data="Mock Instructions")):
        with patch("builtins.print"):
            await dryrun("step3: hello")

    mock_resolve.assert_called_once_with(
        "step3",
        form_definition_service=None,
        prompt_template_service=None,
    )
    mock_agent_class.assert_called_once()
    mock_agent_instance.run.assert_called_once_with("hello")
