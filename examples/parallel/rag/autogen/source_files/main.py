"""
rag — AutoGen v0.4 port of the LangGraph original.

Original: examples/parallel/rag/langgraph — a single LLM agent in a
ReAct loop with one retriever_tool over a Stock Market 2024 PDF.

AutoGen mapping:
  - LangGraph llm node + ReAct loop -> a single AssistantAgent whose
    internal tool-call loop is the ReAct behaviour.
  - LangGraph retriever_tool        -> a FunctionTool wrapper.
  - StateGraph conditional gate      -> a single-member
    RoundRobinGroupChat(max_turns=1) scoping one query.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

_PDF_PATH = "Stock_Market_Performance_2024.pdf"
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is not None:
        return _retriever
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    if not os.path.exists(_PDF_PATH):
        raise FileNotFoundError(f"PDF file not found: {_PDF_PATH}")
    pages = PyPDFLoader(_PDF_PATH).load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    vectorstore = Chroma.from_documents(
        documents=splitter.split_documents(pages),
        embedding=embeddings,
        persist_directory="chroma_store",
        collection_name="stock_market",
    )
    _retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    return _retriever


def retriever_tool(query: str) -> str:
    """This tool searches and returns the information from the Stock Market Performance 2024 document."""
    docs = _get_retriever().invoke(query)
    if not docs:
        return "I found no relevant information in the Stock Market Performance 2024 document."
    return "\n\n".join(f"Document {i + 1}:\n{doc.page_content}" for i, doc in enumerate(docs))


retriever = FunctionTool(
    retriever_tool,
    description="Searches and returns information from the Stock Market Performance 2024 document.",
)

model_client = OpenAIChatCompletionClient(model="gpt-4o")

rag_agent = AssistantAgent(
    name="rag_agent",
    model_client=model_client,
    tools=[retriever],
    system_message=(
        "You are an intelligent AI assistant who answers questions about Stock "
        "Market Performance in 2024 based on the PDF document loaded into your "
        "knowledge base. Use the retriever tool to answer questions, making "
        "multiple calls if needed, and always cite the specific parts of the "
        "documents you use."
    ),
    reflect_on_tool_use=True,
)

team = RoundRobinGroupChat(participants=[rag_agent], max_turns=1)


async def main():
    await Console(team.run_stream(task="How did the stock market perform in 2024?"))
    await model_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
