"""
Agent Supervisor - Simple Implementation

Direct multi-agent system without complex state management.
"""

from typing import Optional, Dict, Any, List
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.config import settings
from src.agents.contracts.prompts import get_contracts_prompt
from src.agents.contracts.tools import contracts_tools
from src.agents.hr.prompts import get_hr_prompt
from src.agents.hr.tools import hr_tools

logger = logging.getLogger(__name__)

# Simple conversation memory
_conversations: Dict[str, List] = {}


def create_gemini_model(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    """Create configured Gemini model instance."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        convert_system_message_to_human=True
    )


def classify_request(message: str) -> str:
    """Classify the request to route to appropriate agent."""
    message_lower = message.lower()

    hr_keywords = [
        "employee", "staff", "leave", "vacation", "sick",
        "attendance", "hiring", "recruit", "applicant", "cv",
        "resume", "department", "manager", "salary", "payroll"
    ]

    if any(kw in message_lower for kw in hr_keywords):
        return "hr"

    return "contracts"


async def process_with_agent(
    message: str,
    system_prompt: str,
    tools: list,
    history: List = None
) -> str:
    """Process a message with a specific agent."""
    model = create_gemini_model()

    # Bind tools if available
    if tools:
        model = model.bind_tools(tools)

    # Build messages
    messages = [SystemMessage(content=system_prompt)]

    # Add history (last 5 exchanges)
    if history:
        messages.extend(history[-10:])

    messages.append(HumanMessage(content=message))

    try:
        # Get initial response
        response = await model.ainvoke(messages)

        # Handle tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_results = []

            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})

                logger.info(f"Calling tool: {tool_name} with args: {tool_args}")

                # Find and execute tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_args)
                            tool_results.append(f"{tool_name} result:\n{result}")
                        except Exception as e:
                            tool_results.append(f"{tool_name} error: {str(e)}")
                        break

            # Get final response with tool results
            if tool_results:
                tool_msg = "\n\n".join(tool_results)
                messages.append(response)
                messages.append(HumanMessage(content=f"Tool results:\n{tool_msg}\n\nNow provide a helpful response based on these results."))

                # Get simple model without tools for final response
                simple_model = create_gemini_model()
                final_response = await simple_model.ainvoke(messages)
                return final_response.content

        return response.content

    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"I encountered an error: {str(e)}"


async def invoke_agent(
    message: str,
    thread_id: str,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Invoke the agent system with a user message."""

    # Get conversation history
    if thread_id not in _conversations:
        _conversations[thread_id] = []
    history = _conversations[thread_id]

    # Classify and route
    agent_type = classify_request(message)
    logger.info(f"Routing to {agent_type} agent")

    # Select agent
    if agent_type == "hr":
        system_prompt = get_hr_prompt()
        tools = hr_tools
    else:
        system_prompt = get_contracts_prompt()
        tools = contracts_tools

    # Process
    response = await process_with_agent(message, system_prompt, tools, history)

    # Save to history
    history.append(HumanMessage(content=message))
    history.append(AIMessage(content=response))

    # Trim history
    if len(history) > 20:
        _conversations[thread_id] = history[-20:]

    return {
        "messages": [AIMessage(content=response)],
        "agent_type": agent_type
    }


def get_last_ai_message(result: Dict[str, Any]) -> str:
    """Extract the last AI message from the result."""
    messages = result.get("messages", [])

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message.content

    return "I apologize, but I couldn't generate a response."


# Compatibility functions
def create_agent_system(checkpointer=None):
    logger.info("Agent system initialized (simple mode)")
    return None


def get_agent_application(checkpointer=None):
    return None
