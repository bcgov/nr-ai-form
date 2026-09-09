"""
Azure AI Foundry GPT-5.1 judge for DeepEval, authenticated with Azure AD
(the developer's `az login` session via DefaultAzureCredential — no API key).

GPT-5.1 is used as the grader here at the user's explicit request. Note that the
system under test is also GPT-5.1-powered, so *live* runs are same-family
self-grading (some leniency bias); offline calibration against the historical
PoC answers in the xlsx is unaffected.

Env (see evaluation/.env.example):
    AZURE_OPENAI_ENDPOINT        https://<your-foundry-resource>.services.ai.azure.com
    AZURE_OPENAI_API_VERSION     2025-04-01-preview
    FOUNDRY_MODEL                gpt-5.1   (deployment name)
    # Optional fallback if you'd rather use a key than az login:
    AZURE_OPENAI_API_KEY
    # Optional: only sent if set (GPT-5.1 reasoning models default to temp=1):
    AZURE_JUDGE_TEMPERATURE
"""

from __future__ import annotations

import os
from typing import Optional

from deepeval.models.base_model import DeepEvalBaseLLM
from openai import AzureOpenAI
from pydantic import BaseModel

AAD_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureJudge(DeepEvalBaseLLM):
    def __init__(
        self,
        deployment: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.deployment = deployment or os.getenv("FOUNDRY_MODEL", "gpt-5.1")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_version = api_version or os.getenv(
            "AZURE_OPENAI_API_VERSION", "2025-04-01-preview"
        )
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY", "")
        self._client: Optional[AzureOpenAI] = None

    def load_model(self) -> AzureOpenAI:
        if self._client is not None:
            return self._client

        common = {"azure_endpoint": self.endpoint, "api_version": self.api_version}
        if self.api_key:
            # Explicit key wins if provided.
            self._client = AzureOpenAI(api_key=self.api_key, **common)
        else:
            # Default: Azure AD via the developer's `az login` session.
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), AAD_SCOPE
            )
            self._client = AzureOpenAI(azure_ad_token_provider=token_provider, **common)
        return self._client

    def _kwargs(self) -> dict:
        kwargs: dict = {}
        temp = os.getenv("AZURE_JUDGE_TEMPERATURE")
        if temp is not None and temp != "":
            kwargs["temperature"] = float(temp)
        return kwargs

    def generate(self, prompt: str, schema: Optional[type[BaseModel]] = None):
        client = self.load_model()
        if schema is not None:
            completion = client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                response_format=schema,
                **self._kwargs(),
            )
            return completion.choices[0].message.parsed
        completion = client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            **self._kwargs(),
        )
        return completion.choices[0].message.content

    async def a_generate(self, prompt: str, schema: Optional[type[BaseModel]] = None):
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return f"AzureAIFoundry/{self.deployment}"
