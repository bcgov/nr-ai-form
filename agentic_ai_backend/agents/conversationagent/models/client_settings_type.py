"""Type definitions for conversation agent client settings from Cosmos DB."""

from typing import TypedDict, Literal


class ConversationAgentConfig(TypedDict, total=False):
    """The 'config' block for a conversationAgent sub-agent in the client profile."""

    # Mode selection
    conversationAgentMode: Literal["knowledgebase", "llm"]

    # Azure AI Search / Knowledge Base
    azureSearchIndexName: str
    azureSearchKnowledgeAgentName: str
    azureSearchKnowledgeAgentApiVersion: str
    azureSearchKnowledgeAgentRequestMode: Literal["messages", "intents"]
    azureSearchKnowledgeAgentOutputMode: Literal["answerSynthesis", "extractiveData"]
    azureSearchKnowledgeAgentReasoningEffort: Literal["minimal", "low", "medium"]
    azureSearchKnowledgeAgentMaxOutputSize: int
    azureSearchKnowledgeAgentMaxRuntimeSeconds: int
    azureSearchKnowledgeAgentMaxHistoryMessages: int

    # Azure AI Search query settings
    azureSearchTop: int
    azureSearchTrimLength: int
    azureSearchEnableTrimming: bool
    azureSearchIncludeTotalCount: bool
    azureSearchQueryType: str
    azureSearchSemanticConfiguration: str
    azureSearchQueryCaption: str
    azureSearchQueryAnswer: str
    azureSearchQueryAnswerCount: int
    azureSearchQueryLanguage: str

    # LLM mode settings
    azureOpenaiChatDeploymentName: str
    azureOpenaiApiVersion: str
    agentMaxTokens: int
    agentTemperature: float


class ConversationAgentClientSettings(TypedDict):
    """The full client_settings dict passed to ConversationAgent.run()."""

    agentType: str
    enabled: bool
    clientId: str
    configFingerprint: str
    promptPath: str
    config: ConversationAgentConfig
