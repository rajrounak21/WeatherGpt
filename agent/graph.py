"""Simple LangGraph agent: Groq LLM + weather_tool"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

from tools.weather_tool import get_weather_tool as _get_weather
from agent.prompts import SYSTEM_PROMPT

load_dotenv(override=True)

# wrap as LangChain tool
@tool
def get_weather_tool(location: str, forecast_time: str = "now", target_hour: int = 12) -> dict:
    """Get weather. forecast_time: now/today/tomorrow/day_after_tomorrow"""
    return _get_weather(location=location, forecast_time=forecast_time, target_hour=target_hour)

tools = [get_weather_tool]

class State(TypedDict):
    messages: Annotated[list, add_messages]

def build_graph():
    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0.2,
        api_key=os.getenv("GROQ_API_KEY"),
    )
    llm_with_tools = llm.bind_tools(tools)

    def agent(state: State):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
        resp = llm_with_tools.invoke(msgs)
        return {"messages": [resp]}

    graph = StateGraph(State)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()

# singleton
_graph = None
def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph

def ask(query: str) -> str:
    """One-shot text ask, returns final assistant text."""
    g = get_graph()
    result = g.invoke({"messages": [{"role": "user", "content": query}]})
    # last AI message content
    for m in reversed(result["messages"]):
        if m.type == "ai" and m.content:
            return m.content
    return "No response"
