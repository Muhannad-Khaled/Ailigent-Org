"""
Multi-Agent System

LangGraph-based hierarchical agent system with:
- Executive Agent (Supervisor/Orchestrator)
- Contracts Agent (Contract lifecycle management)
- HR Agent (Human resources automation)
"""

from .supervisor import create_agent_system, get_agent_application

__all__ = ["create_agent_system", "get_agent_application"]
