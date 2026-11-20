import json
import re
from typing import Any, Dict, List, Optional

import anthropic
import httpx
from langfuse import get_client


def _get(block: Any, key: str, default: Any = None) -> Any:
    """Read a field from either an Anthropic SDK block or a plain dict."""
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _blocks_to_messages(role: str, content: Any) -> List[Dict[str, Any]]:
    """Convert Anthropic message content into OpenAI-format messages.

    Langfuse renders this format as a readable conversation, with tool calls
    shown as cards (arguments must be JSON-encoded strings).
    """
    if isinstance(content, str):
        return [{"role": role, "content": content}]

    messages: List[Dict[str, Any]] = []
    text_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    for block in content or []:
        block_type = _get(block, "type")
        if block_type == "text":
            text_parts.append(_get(block, "text", ""))
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": _get(block, "id"),
                    "type": "function",
                    "function": {
                        "name": _get(block, "name"),
                        "arguments": json.dumps(_get(block, "input", {})),
                    },
                }
            )
        elif block_type == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": _get(block, "tool_use_id"),
                    "content": str(_get(block, "content", "")),
                }
            )
    if text_parts or tool_calls:
        message: Dict[str, Any] = {"role": role, "content": "\n".join(text_parts)}
        if tool_calls:
            message["tool_calls"] = tool_calls
        messages.insert(0, message)
    return messages


def _trace_input(system: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the generation input: system prompt followed by the conversation."""
    traced: List[Dict[str, Any]] = [{"role": "system", "content": system}]
    for message in messages:
        traced.extend(_blocks_to_messages(message["role"], message["content"]))
    return traced


class AIGenerator:
    """Handles interactions with LLM providers (Anthropic Claude or local Ollama)
    for generating responses with tool usage."""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to search tools for course information.

Available Tools:
- **Content Search Tool**: Use for questions about specific course content or detailed educational materials
- **Course Outline Tool**: Use for questions about course structure, lesson lists, or course overviews

Tool Usage Guidelines:
- Use content search for detailed questions about specific topics or lessons
- Use course outline tool for questions about course structure, lesson titles, or complete course overviews
- **You can make up to 2 rounds of tool calls to gather comprehensive information**
- Use multiple rounds for complex queries that require information gathering then refinement
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Course Outline Responses:
When using the course outline tool, always include:
- Course title
- Course link (if available)
- Complete lesson list with lesson numbers and titles
- Present information in a clear, structured format

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: str = "anthropic",
        ollama_base_url: str = "http://localhost:11434",
    ):
        """provider is one of "anthropic", "openai" or "ollama"."""
        self.provider = provider
        self.model = model or "claude-sonnet-4-20250514"

        if provider == "openai":
            # Drop-in replacement that traces every call as a Langfuse generation
            # (model, usage, cost, errors). Imported lazily so the dependency is
            # only needed when this provider is selected.
            from langfuse.openai import OpenAI

            self.model = model or "gpt-4o-mini"
            self.client = OpenAI(api_key=api_key)
            # Reasoning models only accept the default temperature and count
            # reasoning tokens against the completion limit, so leave room.
            self.base_params = {"max_completion_tokens": 2000}
        elif provider == "ollama":
            self.ollama_base_url = ollama_base_url.rstrip("/")
            self.client = None
            self.base_params = {"temperature": 0}
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
            # Pre-build base API parameters
            self.base_params = {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 800,
            }

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential rounds of tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        if self.provider in ("ollama", "openai"):
            return self._generate_openai_format(
                query, system_content, tools, tool_manager
            )

        # Start with initial messages
        messages = [{"role": "user", "content": query}]

        # Execute up to 2 rounds of tool calling
        for round_num in range(2):
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            response = self._create_message(api_params)

            # Handle tool execution if needed
            if response.stop_reason == "tool_use" and tool_manager:
                messages, should_continue = self._handle_tool_execution(
                    response, messages, tool_manager
                )
                if not should_continue:
                    break
            else:
                # No tool use, return direct response
                return response.content[0].text

        # After max rounds, make final call without tools to get response
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self._create_message(final_params)
        return final_response.content[0].text

    def _create_message(self, api_params: Dict[str, Any]):
        """Call the Anthropic API, recording the call as a Langfuse generation."""
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="generate-response",
            model=self.model,
            input=_trace_input(api_params["system"], api_params["messages"]),
            model_parameters={
                "temperature": self.base_params["temperature"],
                "max_tokens": self.base_params["max_tokens"],
            },
            metadata={"provider": "anthropic", "tools_enabled": "tools" in api_params},
        ) as generation:
            response = self.client.messages.create(**api_params)
            usage = response.usage
            usage_details = {
                "input": usage.input_tokens,
                "output": usage.output_tokens,
            }
            # Anthropic reports cache tokens separately from input_tokens,
            # which matches Langfuse's non-overlapping usage buckets.
            for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
                value = getattr(usage, key, None)
                if value:
                    usage_details[key] = value
            output = _blocks_to_messages("assistant", response.content)
            generation.update(
                output=output[0] if output else None,
                usage_details=usage_details,
                metadata={"stop_reason": response.stop_reason},
            )
        return response

    def _handle_tool_execution(self, initial_response, messages: List, tool_manager):
        """
        Handle execution of tool calls and update message history.

        Args:
            initial_response: The response containing tool use requests
            messages: Current message history
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (updated_messages, should_continue)
        """
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Tool execution failed, stop rounds
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error: Tool execution failed - {str(e)}",
                        }
                    )
                    # Add tool results and signal to stop
                    if tool_results:
                        messages.append({"role": "user", "content": tool_results})
                    return messages, False

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Continue with next round
        return messages, True

    # ------------------------------------------------------------------
    # Ollama provider (OpenAI-compatible /v1/chat/completions endpoint)
    # ------------------------------------------------------------------

    @staticmethod
    def _to_openai_tools(tools: Optional[List]) -> Optional[List[Dict]]:
        """Convert Anthropic-style tool definitions to OpenAI/Ollama format."""
        if tools is None:
            return None
        if not tools:
            return []
        openai_tools = []
        for tool in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                }
            )
        return openai_tools

    def _chat(self, messages: List[Dict], tools: Optional[List]) -> Dict:
        """Dispatch a single chat completion to the configured provider."""
        if self.provider == "openai":
            return self._openai_chat(messages, tools)
        return self._ollama_chat(messages, tools)

    def _openai_chat(self, messages: List[Dict], tools: Optional[List]) -> Dict:
        """Make a single chat completion call against the OpenAI API."""
        params: Dict[str, Any] = {**self.base_params}
        openai_tools = self._to_openai_tools(tools)
        if openai_tools:
            params["tools"] = openai_tools

        # `name` and `metadata` are consumed by the Langfuse wrapper
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            name="generate-response",
            metadata={"provider": "openai", "tools_enabled": bool(openai_tools)},
            **params,
        )
        return response.choices[0].message.model_dump(exclude_none=True)

    def _ollama_chat(self, messages: List[Dict], tools: Optional[List]) -> Dict:
        """Make a single chat completion call against the local Ollama server."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            **self.base_params,
        }
        openai_tools = self._to_openai_tools(tools)
        if openai_tools:
            payload["tools"] = openai_tools

        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name="generate-response",
            model=self.model,
            input=messages,
            model_parameters={"temperature": self.base_params["temperature"]},
            metadata={"provider": "ollama", "tools_enabled": bool(openai_tools)},
        ) as generation:
            response = httpx.post(
                f"{self.ollama_base_url}/v1/chat/completions",
                json=payload,
                timeout=180.0,
            )
            response.raise_for_status()
            body = response.json()
            message = body["choices"][0]["message"]
            usage = body.get("usage") or {}
            generation.update(
                output=message,
                usage_details={
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                },
                metadata={"finish_reason": body["choices"][0].get("finish_reason")},
            )
        return message

    @staticmethod
    def _parse_text_tool_calls(content: str) -> List[Dict]:
        """Parse tool calls from raw text output when the model doesn't use
        the OpenAI function calling format.

        Handles patterns like:
          <function=search_course_content> <parameter=query> what to search
          <function=get_course_outline> <parameter=course_name> MCP
        """
        if not content:
            return []

        tool_calls = []
        # Find all <function=NAME> positions
        func_starts = list(re.finditer(r"<function=(\w+)>", content))

        for i, match in enumerate(func_starts):
            func_name = match.group(1)
            # Extract text between this <function=...> and the next (or end)
            start = match.end()
            end = (
                func_starts[i + 1].start() if i + 1 < len(func_starts) else len(content)
            )
            params_text = content[start:end].strip()

            # Parse <parameter=key> value pairs
            params = {}
            for param_match in re.finditer(
                r"<parameter=(\w+)>\s*(.*?)(?=<parameter=|<|$)", params_text, re.DOTALL
            ):
                params[param_match.group(1)] = param_match.group(2).strip()

            tool_calls.append(
                {
                    "id": f"text_{func_name}_{len(tool_calls)}",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(params),
                    },
                }
            )

        return tool_calls

    def _generate_openai_format(
        self,
        query: str,
        system_content: str,
        tools: Optional[List],
        tool_manager,
    ) -> str:
        """Generate a response via an OpenAI-format chat API (OpenAI or Ollama),
        supporting up to 2 rounds of tool calls."""
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        for _ in range(2):
            message = self._chat(messages, tools)

            # Try structured tool_calls first, then fall back to text parsing
            tool_calls = message.get("tool_calls")
            if not tool_calls and message.get("content"):
                tool_calls = self._parse_text_tool_calls(message["content"])

            if not tool_calls or not tool_manager:
                return message.get("content") or ""

            # Preserve the assistant's tool-call turn in history
            history_entry = {"role": "assistant", "content": message.get("content")}
            history_entry["tool_calls"] = tool_calls
            messages.append(history_entry)

            for tool_call in tool_calls:
                function = tool_call["function"]
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                    result = tool_manager.execute_tool(function["name"], **arguments)
                except Exception as e:
                    result = f"Error: Tool execution failed - {str(e)}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id") or function["name"],
                        "content": str(result),
                    }
                )

        # After max rounds, make final call without tools to get a direct answer
        final_message = self._chat(messages, tools=None)
        return final_message.get("content") or ""
