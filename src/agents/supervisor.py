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
from src.agents.finance.prompts import get_finance_prompt
from src.agents.finance.tools import finance_tools
from src.agents.executive.prompts import get_executive_prompt

logger = logging.getLogger(__name__)

# Simple conversation memory
_conversations: Dict[str, List] = {}


def extract_text_content(content) -> str:
    """Extract text from various response content formats.

    Handles:
    - Simple string
    - List of content blocks (Gemini 2.5 format)
    - Dict with 'text' key
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # Handle list of content blocks
        texts = []
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict):
                if 'text' in block:
                    texts.append(block['text'])
                elif 'content' in block:
                    texts.append(str(block['content']))
        return '\n'.join(texts) if texts else str(content)

    if isinstance(content, dict):
        if 'text' in content:
            return content['text']
        if 'content' in content:
            return str(content['content'])

    return str(content)


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

    # Greetings and general chat → executive (human-like responses)
    greeting_keywords = [
        # English greetings
        "hello", "hi ", "hi!", "hey", "good morning", "good afternoon",
        "good evening", "how are you", "what's up", "sup",
        "thanks", "thank you", "bye", "goodbye", "see you",
        # Arabic greetings
        "السلام", "سلام", "مرحبا", "اهلا", "أهلا", "صباح", "مساء",
        "ازيك", "إزيك", "ازاي", "عامل ايه", "شكرا", "مع السلامة",
        # General questions
        "who are you", "what can you do", "help me", "انت مين",
        "بتعمل ايه", "تقدر تساعدني", "ممكن تساعدني",
        # Small talk
        "how's it going", "what's new", "اخبارك", "الاخبار"
    ]

    # Check for greetings/general chat first
    if any(kw in message_lower for kw in greeting_keywords):
        return "executive"

    # Finance/Accounting keywords - check before HR
    finance_keywords = [
        # Sales terms (IMPORTANT: check before HR)
        "sales", "sale order", "sales order", "order", "orders",
        "مبيعات", "المبيعات", "طلب", "طلبات", "أوردر", "اوردر",
        "sold", "selling", "بيع", "باع", "مبيع",
        "top selling", "best selling", "اكتر مبيعاً",
        "customer sales", "sales by customer",
        # Invoice terms
        "invoice", "invoices", "فاتورة", "فواتير",
        # Payment terms
        "payment", "payments", "دفع", "مدفوعات", "دفعات",
        # Financial reports
        "profit", "loss", "p&l", "ربح", "خسارة", "أرباح وخسائر",
        "cash flow", "تدفق نقدي", "الكاش",
        "revenue", "إيرادات", "ايراد", "ايرادات",
        "expense", "expenses", "مصروفات", "مصروف", "مصاريف",
        # Accounting terms
        "accounting", "محاسبة", "حسابات",
        "journal", "journal entry", "قيد", "قيود", "قيد يومية",
        "ledger", "دفتر", "الأستاذ",
        "balance sheet", "ميزانية", "ميزان",
        "financial", "مالي", "مالية",
        # Receivables/Payables
        "receivable", "receivables", "مستحقات", "ذمم مدينة",
        "payable", "payables", "ذمم دائنة", "مستحقات علينا",
        "outstanding", "overdue", "متأخرات", "متأخر",
        "unpaid", "غير مدفوع",
        # Other finance terms
        "debit", "credit", "مدين", "دائن",
        "bank statement", "كشف حساب", "كشف بنك",
        "bill", "bills", "فاتورة مشتريات"
    ]

    # Check for finance keywords
    if any(kw in message_lower for kw in finance_keywords):
        return "finance"

    hr_keywords = [
        # Employee terms
        "employee", "employees", "staff", "personnel", "worker", "workers",
        "headcount", "workforce", "team member", "colleague",
        # Arabic employee terms
        "موظف", "موظفين", "الموظفين", "عدد الموظفين", "كام موظف",
        # Statistics/counting terms (for HR context)
        "how many people", "number of people", "total people",
        "how many work", "who works",
        # Leave terms
        "leave", "vacation", "sick", "time off", "pto", "holiday",
        "absence", "absent",
        # Arabic leave terms
        "اجازة", "إجازة", "اجازات", "الإجازات",
        # Attendance terms
        "attendance", "check in", "check out", "working hours",
        # Recruitment terms
        "hiring", "recruit", "applicant", "cv", "resume", "candidate",
        "job opening", "position open",
        # Organization terms
        "department", "manager", "supervisor", "team lead",
        "org chart", "organization", "reporting",
        # Arabic organization terms
        "قسم", "الأقسام", "مدير", "المدير",
        # Compensation (HR context)
        "salary", "payroll", "wage", "compensation",
        # Job titles/roles
        "job title", "job position", "role",
        # Common department names
        "professional service", "human resource", "hr ", "engineering",
        "sales", "marketing", "operations", "support",
        "development", "developer", "engineer"
    ]

    contract_keywords = [
        # Contract terms
        "contract", "contracts", "agreement", "agreements",
        "renewal", "renewals", "expiring", "expiration",
        "vendor", "supplier", "partner",
        # Arabic contract terms
        "عقد", "عقود", "العقود", "تجديد", "العقد",
        "تقرير العقود", "العقود المنتهية"
    ]

    if any(kw in message_lower for kw in hr_keywords):
        return "hr"

    if any(kw in message_lower for kw in contract_keywords):
        return "contracts"

    # Default to executive for general queries (more human-like)
    return "executive"


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
                return extract_text_content(final_response.content)

        return extract_text_content(response.content)

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
    elif agent_type == "contracts":
        system_prompt = get_contracts_prompt()
        tools = contracts_tools
    elif agent_type == "finance":
        system_prompt = get_finance_prompt()
        tools = finance_tools
    else:  # executive - for greetings, general chat, and human-like responses
        system_prompt = get_executive_prompt()
        tools = []  # Executive handles conversation naturally without tools

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
