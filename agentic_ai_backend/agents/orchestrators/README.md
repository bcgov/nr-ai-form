# Orchestrator Agent - Architecture Documentation

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Components](#components)
  - [Conversation Agent](#conversation-agent)
  - [Form Support Agent](#form-support-agent)
  - [Orchestrator Agent](#orchestrator-agent)
- [A2A Protocol](#a2a-protocol)
  - [What is A2A?](#what-is-a2a)
  - [A2A Client-Server Design](#a2a-client-server-design)
  - [Benefits of A2A](#benefits-of-a2a)
- [Workflow Components](#workflow-components)
- [Configuration](#configuration)
- [Usage](#usage)
- [Deployment](#deployment)

---

## Overview

The Orchestrator Agent is a multi-agent system designed for BC Government's Water Permit Application assistance. It coordinates between two specialized agents:

- **Conversation Agent**: Answers general questions using Azure AI Search
- **Form Support Agent**: Provides form-specific assistance with dynamic step support

The system uses the **A2A (Agent to Agent) protocol** for inter-agent communication, enabling a scalable, microservices-based architecture.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User / Frontend                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Query
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator Agent                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            WorkflowBuilder                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │  │
│  │  │Dispatcher│─▶│Executors │─▶│Aggregator│          │  │
│  │  └──────────┘  └──────────┘  └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬──────────────────┬─────────────────────┘
                     │                  │
                     │ A2A Protocol     │ A2A Protocol
                     │ (HTTP/JSON)      │ (HTTP/JSON)
                     │                  │
        ┌────────────▼─────┐   ┌───────▼──────────────┐
        │ Conversation     │   │ Form Support         │
        │ Agent A2A Server │   │ Agent A2A Server     │
        │ Port: 8000       │   │ Port: 8001           │
        │                  │   │                      │
        │ ┌──────────────┐ │   │ ┌────────────────┐  │
        │ │ FastAPI      │ │   │ │ FastAPI        │  │
        │ │ /.well-known/│ │   │ │ /.well-known/  │  │
        │ │ /invoke      │ │   │ │ /invoke        │  │
        │ │ /health      │ │   │ │ /health        │  │
        │ └──────────────┘ │   │ └────────────────┘  │
        │                  │   │                      │
        │ ┌──────────────┐ │   │ ┌────────────────┐  │
        │ │Conversation  │ │   │ │Form Support    │  │
        │ │Agent Logic   │ │   │ │Agent Logic     │  │
        │ │(Azure AI     │ │   │ │(Step-aware)    │  │
        │ │ Search)      │ │   │ └────────────────┘  │
        │ └──────────────┘ │   │                      │
        └──────────────────┘   └──────────────────────┘
```

### Architecture Layers

```
┌────────────────────────────────────────────────────────┐
│              Orchestration Layer                       │
│  - WorkflowBuilder                                     │
│  - Dispatcher, Aggregator                              │
│  - Workflow Execution                                  │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              Executor Layer                            │
│  - ConversationAgentA2AExecutor                        │
│  - FormSupportAgentA2AExecutor                         │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              A2A Client Layer                          │
│  - CSS_AI_A2A_BaseClient                               │
│  - ConversationAgentA2AClient                          │
│  - FormSupportAgentA2AClient                           │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              Network Layer (HTTP/JSON)                 │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              A2A Server Layer                          │
│  - FastAPI Endpoints                                   │
│  - Request Validation (Pydantic)                       │
└────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│              Agent Layer                               │
│  - Agent Business Logic                                │
│  - LLM Integration (Azure OpenAI)                      │
│  - Tool Integration (Azure AI Search)                  │
└────────────────────────────────────────────────────────┘
```

---

## Components

### Conversation Agent

**Purpose**: Provides conversational AI assistance for general water permit questions.

**Technology Stack**:
- **Framework**: Microsoft Agent Framework
- **LLM**: Azure OpenAI (configurable deployment)
- **Knowledge Base**: Azure AI Search
- **A2A Server**: FastAPI

**Features**:
- Semantic search across water permit documentation
- Context-aware responses
- Citation support
- Stateless operation (can be made stateful with session management)

**Directory Structure**:
```
conversationagent/
├── conversationagent.py          # Core agent implementation
├── conversation_agent_a2a_server.py  # A2A HTTP wrapper
├── agentmanifest/
│   └── manifest.json             # A2A capability manifest
├── models/
│   └── conversationmodel.py      # Request/Response models
└── .env                          # Configuration
```

**A2A Endpoints**:
- `GET /.well-known/agent.json` - Agent manifest
- `POST /invoke` - Execute query
- `GET /health` - Health check

---

### Form Support Agent

**Purpose**: Provides intelligent form field suggestions and validation for multi-step water permit forms.

**Technology Stack**:
- **Framework**: Microsoft Agent Framework
- **LLM**: Azure OpenAI (structured output)
- **Form Definitions**: JSON-based step definitions
- **A2A Server**: FastAPI

**Features**:
- **Dynamic Step Loading**: Loads form definitions based on step number
- **Field Matching**: Matches user input to form fields
- **Structured Output**: Returns JSON with field ID and suggested values
- **Multi-Step Support**: Handles multiple form steps simultaneously
- **Caching**: Agent instances cached per step for performance

**Directory Structure**:
```
formsupportagent/
├── formsupportagent.py           # Core agent implementation
├── formsupport_agent_a2a_server.py  # A2A HTTP wrapper
├── agentmanifest/
│   └── manifest.json             # A2A capability manifest
├── models/
│   └── formsupportmodel.py       # Request/Response models
├── formdefinitions/
│   ├── step2.json                # Step 2 form definition
│   ├── step3.json                # Step 3 form definition (if exists)
│   └── ...
└── .env                          # Configuration
```

**Step Number Support**:
```python
# Request with step number
{
    "query": "North Coast Transmission Pipeline",
    "session_id": "abc123",
    "step_number": 2  # Loads step2.json
}
```

**A2A Endpoints**:
- `GET /.well-known/agent.json` - Agent manifest
- `POST /invoke` - Execute query (with step_number support)
- `GET /health` - Health check

---

### Orchestrator Agent

**Purpose**: Coordinates multiple agents, aggregates responses, and manages workflow execution.

**Technology Stack**:
- **Framework**: Microsoft Agent Framework (WorkflowBuilder)
- **Communication**: A2A Protocol (HTTP/JSON)
- **Async Runtime**: asyncio
- **Environment**: python-dotenv

**Key Responsibilities**:
1. **Dispatching**: Send user query to all relevant agents
2. **Parallel Execution**: Execute agents concurrently
3. **Aggregation**: Collect and present responses
4. **Error Handling**: Manage agent failures gracefully

**Workflow Pattern**:
```
User Query
    │
    ▼
[Dispatcher] ────┬───▶ [ConversationAgentA2AExecutor]
                 │
                 └───▶ [FormSupportAgentA2AExecutor]
                           │
                           ▼
                      [Aggregator] ───▶ Aggregated Results
```

**Directory Structure**:
```
orchestrators/
├── orchestratoragent.py          # Main orchestrator
├── a2aclients/
│   ├── a2a_client.py             # Base A2A client
│   ├── conversationagentclient.py
│   └── formsupportagentclient.py
├── workflowcomponents/
│   ├── dispatcher.py             # Query dispatcher
│   ├── aggregator.py             # Response aggregator
│   ├── conversationagentexecutor.py
│   └── formsupportagentexecutor.py
├── .env                          # Configuration
└── README.md                     # This file
```

---

## A2A Protocol

### What is A2A?

**A2A (Agent to Agent)** is a protocol for inter-agent communication that enables:
- **Discoverable** agents via standardized manifests
- **Interoperable** communication using HTTP/JSON
- **Scalable** microservices architecture
- **Language-agnostic** implementations

### A2A Client-Server Design

#### A2A Server Components

Each agent exposes three core endpoints:

```python
# 1. Discovery Endpoint
GET /.well-known/agent.json
Response: {
    "identity": {
        "name": "ConversationAgent",
        "author": "BC Government",
        "version": "1.0.0"
    },
    "capabilities": [...],
    "interaction": {
        "baseUrl": "http://localhost:8000",
        "endpoints": {...}
    }
}

# 2. Invocation Endpoint
POST /invoke
Request: {
    "query": "What is BCeID?",
    "session_id": "abc123",
    "step_number": 2  # Optional, for Form Support Agent
}
Response: {
    "response": "BCeID is...",
    "session_id": "abc123"
}

# 3. Health Endpoint
GET /health
Response: {
    "status": "healthy",
    "agent": "ConversationAgent",
    "version": "1.0.0"
}
```

#### A2A Client Components

**Base Client** (`CSS_AI_A2A_BaseClient`):
```python
class CSS_AI_A2A_BaseClient:
    async def get_manifest(self) -> AgentManifest
    async def invoke(self, query: str, **kwargs) -> str
    async def health_check(self) -> Dict[str, Any]
```

**Specialized Clients**:
- `ConversationAgentA2AClient` - Defaults to port 8000
- `FormSupportAgentA2AClient` - Defaults to port 8001

See complete documentation in this README.md file.

---

© 2025 BC Government. All rights reserved.
