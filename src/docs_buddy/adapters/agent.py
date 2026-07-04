"""Functionality required by agents"""

import asyncio
import json
from typing import Callable
import textwrap
import os
import logging

import openai
import agents

from docs_buddy import domain, services
from docs_buddy.common import DocsBuddyError, log_input

log = logging.getLogger(__name__)


class AgentError(DocsBuddyError):
    pass


class ToolError(DocsBuddyError):
    pass


class LoggingHooks(agents.RunHooks):
    """Defines logging hooks for the openai agent"""

    async def on_agent_start(self, context, agent):
        log.info(
            "agent started: %s, input tokens: %s, output tokens: %s",
            agent.name,
            context.usage.input_tokens,
            context.usage.output_tokens,
        )

    async def on_llm_end(self, context, agent, response):
        log.info(
            "llm ended: agent %s, output length: %s, input tokens: %s, output tokens: %s",
            agent.name,
            len(response.output),
            context.usage.input_tokens,
            context.usage.output_tokens,
        )

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        log.info(
            "llm started: agent %s, input tokens: %s, output tokens: %s, inputs length %s",
            agent.name,
            context.usage.input_tokens,
            context.usage.output_tokens,
            len(input_items),
        )

    async def on_agent_end(self, context, agent, output):
        log.info(
            "agent %s ended: input tokens: %s, output tokens: %s",
            agent.name,
            context.usage.input_tokens,
            context.usage.output_tokens,
        )

    async def on_tool_start(self, context, agent, tool):
        log.info(
            "tool %s started: agent %s, input tokens: %s, output tokens: %s",
            tool.name,
            agent.name,
            context.usage.input_tokens,
            context.usage.output_tokens,
        )

    async def on_tool_end(self, context, agent, tool, result):
        log.info(
            "tool %s ended: agent %s, input tokens: %s, output tokens: %s",
            tool.name,
            agent.name,
            context.usage.input_tokens,
            context.usage.output_tokens,
        )


def make_search_tool(index: services.DocumentIndex) -> Callable:
    """Creates a search tool over the index"""

    @log_input(log, logging.INFO)
    def search_document_index(phrase: str, max_results: int = 5) -> list[str]:
        """Search the document index for the given phrase

        Args:
          phrase (string): The phrase to search
          max_results (int): The maximum number of results to return

        Returns:
          list[str]: A list of JSON formatted strings representing the
                     the results. Each result has associated content,
                     path and metadata fields
        """

        if not max_results > 0:
            raise ToolError(
                f"maximum results should be greater than 0, got {max_results}"
            )

        query = domain.Query(phrase)
        results = index.search(query, max_results)
        return [str(r) for r in results]

    return search_document_index


def make_fake_research_agent(prompt: str) -> services.Agent:
    """Creates a fake agent"""

    def fake_agent(query: domain.Query, tools: list[Callable]) -> domain.QueryResponse:
        """Uses the search tool provided to get results matching the query"""

        search_tool, *_ = tools
        results = search_tool(str(query))

        try:
            first_result, *_ = results
            json_result = json.loads(first_result)
            answer, citation = json_result["content"], json_result["path"]
        except (TypeError, ValueError) as exc:
            raise AgentError("Something went wrong") from exc
        return domain.QueryResponse(answer, [citation])

    return fake_agent


@agents.function_tool
def generate_final_response(
    final_answer: str, citations: list[str]
) -> domain.QueryResponse:
    """Generates the final response to the user's query in a structed format

    Args:
      final_answer (str): The final answer to the user's query
      citations (list[str]): A list of paths from the search tool results that were instrumental
                             in generating the answer

    Returns:
      QueryResponse: A structured response to the user's query
    """

    try:
        final_response = domain.QueryResponse(final_answer, citations)
    except (TypeError, ValueError) as exc:
        raise AgentError("Could not create response") from exc

    return final_response


def make_openai_research_agent(prompt: str) -> services.Agent:
    """Creates an openai agent"""

    BASE_URL = os.getenv("OPENAI_BASE_URL") or ""
    API_KEY = os.getenv("OPENAI_API_KEY") or ""
    MODEL_NAME = os.getenv("DOCS_BUDDY_MODEL_NAME") or ""

    if not BASE_URL or not API_KEY or not MODEL_NAME:
        raise AgentError(
            "Please set OPENAI_BASE_URL, OPENAI_API_KEY, DOCS_BUDDY_MODEL_NAME"
        )

    client = openai.AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    agents.set_tracing_disabled(disabled=True)

    class CustomModelProvider(agents.ModelProvider):
        def get_model(self, model_name: str | None) -> agents.Model:
            return agents.OpenAIChatCompletionsModel(
                model=model_name or MODEL_NAME, openai_client=client
            )

    CUSTOM_MODEL_PROVIDER = CustomModelProvider()

    def openai_agent(
        query: domain.Query, tools: list[Callable]
    ) -> domain.QueryResponse:
        """OpenaAI compatible agent that answers user's query"""

        final_response_callout = (
            "IMPORTANT: Always call generate_final_response as your final output."
        )

        system_instructions = f"""\
        {prompt}
        
        {final_response_callout}
        """

        agent = agents.Agent(
            name="Docs Buddy Agent",
            instructions=textwrap.dedent(system_instructions),
            tools=[agents.function_tool(func) for func in tools]  # type: ignore[arg-type]
            + [generate_final_response],
            tool_use_behavior=agents.agent.StopAtTools(
                stop_at_tool_names=["generate_final_response"]
            ),
        )

        result = asyncio.run(
            run_agent(
                agent,
                str(query),
                LoggingHooks(),
                agents.RunConfig(model_provider=CUSTOM_MODEL_PROVIDER),
            )
        )

        output: str = result.final_output
        try:
            response = domain.QueryResponse.fromstring(output)
        except json.JSONDecodeError as exc:
            raise AgentError("Could not parse query response from llm") from exc
        return response

    return openai_agent


async def run_agent(
    agent: agents.Agent, query: str, hooks: agents.RunHooks, config: agents.RunConfig
) -> agents.RunResult:
    """Run agent in event loop"""
    return await agents.Runner.run(agent, query, hooks=hooks, run_config=config)
