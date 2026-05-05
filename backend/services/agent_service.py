"""
agent_service.py

Initializes the LangGraph ReAct agent that orchestrates our construction tools.
Uses MemorySaver to persist conversation history within a specific `page_session_id`.
"""

import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from prompts import AGENT_SYSTEM_PROMPT

# Global in-memory checkpointer.
# Thread IDs map to page_session_idx so memory resets when the user uploads a new plan.
memory = MemorySaver()

# Use gpt-4o for complex reasoning steps and tool calling
llm = ChatOpenAI(model="gpt-4o", temperature=0)

SYSTEM_PROMPT = AGENT_SYSTEM_PROMPT

