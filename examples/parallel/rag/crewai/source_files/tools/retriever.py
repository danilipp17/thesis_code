"""Retriever tool exposed as a CrewAI tool (port of the LangGraph retriever_tool)."""

import os

from crewai.tools import tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

_PDF_PATH = "Stock_Market_Performance_2024.pdf"
_PERSIST_DIR = "chroma_store"
_COLLECTION = "stock_market"

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
    pages_split = splitter.split_documents(pages)
    vectorstore = Chroma.from_documents(
        documents=pages_split,
        embedding=embeddings,
        persist_directory=_PERSIST_DIR,
        collection_name=_COLLECTION,
    )
    _retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    return _retriever


@tool("retriever_tool")
def retriever_tool(query: str) -> str:
    """This tool searches and returns the information from the Stock Market Performance 2024 document."""
    docs = _get_retriever().invoke(query)
    if not docs:
        return "I found no relevant information in the Stock Market Performance 2024 document."
    return "\n\n".join(f"Document {i + 1}:\n{doc.page_content}" for i, doc in enumerate(docs))
