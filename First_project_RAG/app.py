"""Beginner-friendly RAG social post assistant using LangGraph.

Features:
- RAG over a PDF (auto-ingest and vector store build)
- LangGraph state machine
- Human-in-the-loop approval with interrupt/resume
- Checkpointer (MemorySaver)
- Tools (date/time and hashtag helper)
"""

from __future__ import annotations

import argparse
import os
import uuid
import operator
from typing import Annotated, List, TypedDict

from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt


load_dotenv()


class PostState(TypedDict):
	# Input fields
	topic: str
	audience: str
	tone: str
	constraints: str
	pdf_path: str
	# Conversation context (LangGraph merges this list across nodes)
	messages: Annotated[List[BaseMessage], operator.add]
	# RAG artifacts
	retrieved_docs: List[Document]
	# Draft and approval
	draft: str
	approved: bool
	human_feedback: str
	final_post: str


VECTORSTORE = None


def get_llm():
	# Default to Ollama when available.
	provider = os.getenv("LLM_PROVIDER", "").strip().lower()
	if not provider:
		if os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL"):
			provider = "ollama"
		elif os.getenv("GROQ_API_KEY"):
			provider = "groq"
		else:
			provider = "ollama"

	if provider == "ollama":
		from langchain_ollama import ChatOllama

		model_name = os.getenv("OLLAMA_MODEL", "gemma3:270m")
		base_url = os.getenv("OLLAMA_BASE_URL", "").strip()
		kwargs = {"model": model_name, "temperature": 0.3}
		if base_url:
			kwargs["base_url"] = base_url
		return ChatOllama(**kwargs)

	if provider == "groq":
		from langchain_groq import ChatGroq

		model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
		return ChatGroq(model=model_name, temperature=0.3)

	raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


def get_llm_provider() -> str:
	provider = os.getenv("LLM_PROVIDER", "").strip().lower()
	if provider:
		return provider
	if os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL"):
		return "ollama"
	if os.getenv("GROQ_API_KEY"):
		return "groq"
	return "ollama"


def get_embeddings():
	# Choose embeddings based on explicit provider or available keys.
	provider = os.getenv("EMBEDDINGS_PROVIDER", "").strip().lower()
	if not provider:
		if os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_BASE_URL"):
			provider = "ollama"
		elif os.getenv("OPENAI_API_KEY"):
			provider = "openai"
		elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
			provider = "google"
		else:
			provider = "local"

	if provider == "ollama":
		from langchain_ollama import OllamaEmbeddings

		model_name = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
		base_url = os.getenv("OLLAMA_BASE_URL", "").strip()
		kwargs = {"model": model_name}
		if base_url:
			kwargs["base_url"] = base_url
		return OllamaEmbeddings(**kwargs)

	if provider == "google":
		from langchain_google_genai import GoogleGenerativeAIEmbeddings

		# Newer Gemini embedding model name for embedContent.
		model_name = os.getenv("GOOGLE_EMBEDDING_MODEL", "text-embedding-004")
		return GoogleGenerativeAIEmbeddings(model=model_name)
	if provider == "openai":
		from langchain_openai import OpenAIEmbeddings

		return OpenAIEmbeddings(model="text-embedding-3-small")
	# Local fallback (requires sentence-transformers)
	from langchain_community.embeddings import HuggingFaceEmbeddings

	return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def load_and_split_pdf(pdf_path: str) -> List[Document]:
	# PyPDFLoader turns PDF pages into Documents.
	from langchain_community.document_loaders import PyPDFLoader
	from langchain_text_splitters import RecursiveCharacterTextSplitter

	loader = PyPDFLoader(pdf_path)
	docs = loader.load()
	splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
	return splitter.split_documents(docs)


def build_vectorstore(pdf_path: str):
	# Build or rebuild a local Chroma store for the provided PDF.
	from langchain_community.vectorstores import Chroma

	embeddings = get_embeddings()
	docs = load_and_split_pdf(pdf_path)
	persist_dir = os.path.join(os.path.dirname(__file__), "data", "chroma")
	os.makedirs(persist_dir, exist_ok=True)

	# Rebuild to keep the demo simple and reproducible.
	vectorstore = Chroma.from_documents(
		documents=docs,
		embedding=embeddings,
		persist_directory=persist_dir,
	)
	return vectorstore


def format_docs(docs: List[Document]) -> str:
	# Simple helper to show the model short, relevant context.
	return "\n\n".join(d.page_content for d in docs)


def normalize_interrupt_payload(payload):
	# Normalize payloads across LangGraph versions.
	if isinstance(payload, list):
		payload = payload[0] if payload else {}
	if hasattr(payload, "value"):
		payload = payload.value
	if hasattr(payload, "data"):
		payload = payload.data
	if not isinstance(payload, dict):
		payload = {}
	return payload


def answer_query_with_rag(retriever, query: str) -> str:
	# Answer a user query using retrieved context from the PDF.
	docs = retriever.invoke(query)
	context = format_docs(docs)
	prompt = ChatPromptTemplate.from_messages(
		[
			(
				"system",
				"Answer the question using the provided context. "
				"If the answer is not in the context, say you do not know.",
			),
			(
				"human",
				"Question: {question}\n\nContext:\n{context}",
			),
		]
	)
	llm = get_llm()
	messages = prompt.format_messages(question=query, context=context)
	response = llm.invoke(messages)
	return response.content or ""


@tool
def current_datetime() -> str:
	"""Get the current date and time (useful for timely posts)."""
	from datetime import datetime

	return datetime.now().strftime("%Y-%m-%d %H:%M")


@tool
def suggest_hashtags(topic: str) -> str:
	"""Return a short list of simple hashtags for the given topic."""
	base = topic.strip().replace(" ", "")
	return f"#{base} #AI #Productivity #Tech"


TOOLS = [current_datetime, suggest_hashtags]


def ingest_node(state: PostState) -> PostState:
	# Create the vector store from the provided PDF.
	global VECTORSTORE
	VECTORSTORE = build_vectorstore(state["pdf_path"])
	return state


def retrieve_node(state: PostState) -> PostState:
	# Retrieve context relevant to the post topic.
	if VECTORSTORE is None:
		raise ValueError("Vector store is not initialized. Did ingest_node run?")

	retriever = VECTORSTORE.as_retriever(search_kwargs={"k": 4})
	query = f"{state['topic']} | audience: {state['audience']} | tone: {state['tone']}"
	# Newer LangChain retrievers use invoke() instead of get_relevant_documents().
	docs = retriever.invoke(query)
	return {"retrieved_docs": docs}


def draft_node(state: PostState) -> PostState:
	# Draft a social post with citations from retrieved context.
	context = format_docs(state.get("retrieved_docs", []))
	prompt = ChatPromptTemplate.from_messages(
		[
			(
				"system",
				"You are a helpful social media assistant. "
				"Write a short post based on the provided context. "
				"Be concise and include a call-to-action.",
			),
			(
				"human",
				"Topic: {topic}\nAudience: {audience}\nTone: {tone}\n"
				"Constraints: {constraints}\n\nContext:\n{context}",
			),
		]
	)

	llm = get_llm()
	provider = get_llm_provider()
	tools_enabled = os.getenv("TOOLS_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
	if tools_enabled and provider != "ollama":
		llm = llm.bind_tools(TOOLS)
	messages = prompt.format_messages(
		topic=state["topic"],
		audience=state["audience"],
		tone=state["tone"],
		constraints=state["constraints"],
		context=context,
	)
	response = llm.invoke(messages)
	return {"messages": [response], "draft": response.content or ""}


def revise_node(state: PostState) -> PostState:
	# Refine the draft using tool outputs and any human feedback.
	feedback = state.get("human_feedback", "")
	prompt = ChatPromptTemplate.from_messages(
		[
			(
				"system",
				"You refine social posts. Use tool outputs and feedback. "
				"Keep it short and engaging.",
			),
			(
				"human",
				"Current draft:\n{draft}\n\n"
				"Feedback (if any): {feedback}\n\n"
				"Rewrite the post in 3-6 sentences.",
			),
		]
	)

	llm = get_llm()
	messages = prompt.format_messages(draft=state["draft"], feedback=feedback)
	response = llm.invoke(messages)
	return {"messages": [response], "draft": response.content or "", "human_feedback": ""}


def human_review_node(state: PostState) -> PostState:
	# Pause the graph and wait for user approval or edit instructions.
	approval = interrupt(
		{
			"draft": state["draft"],
			"question": "Approve the draft? (approve / edit / reject)",
		}
	)
	# Normalize approval payload across LangGraph versions.
	if isinstance(approval, list):
		approval = approval[0] if approval else {}
	if hasattr(approval, "value"):
		approval = approval.value
	if hasattr(approval, "data"):
		approval = approval.data
	if not isinstance(approval, dict):
		approval = {}

	action = (approval.get("action") or "approve").lower()
	edit_text = approval.get("edit", "")

	if action == "edit" and edit_text:
		return {"approved": False, "human_feedback": edit_text}
	if action == "edit" and not edit_text:
		return {"approved": False, "human_feedback": "Revise the post based on user feedback."}
	if action == "reject":
		return {"approved": False, "human_feedback": "Please improve clarity."}

	return {"approved": True}


def finalize_node(state: PostState) -> PostState:
	# Final output after approval.
	return {"final_post": state["draft"]}


def review_router(state: PostState) -> str:
	# Decide where to go after human review.
	return "finalize" if state.get("approved") else "revise"


def build_graph():
	builder = StateGraph(PostState)

	builder.add_node("ingest", ingest_node)
	builder.add_node("retrieve", retrieve_node)
	builder.add_node("draft", draft_node)
	builder.add_node("tools", ToolNode(TOOLS))
	builder.add_node("revise", revise_node)
	builder.add_node("human_review", human_review_node)
	builder.add_node("finalize", finalize_node)

	builder.set_entry_point("ingest")
	builder.add_edge("ingest", "retrieve")
	builder.add_edge("retrieve", "draft")
	builder.add_conditional_edges(
		"draft",
		tools_condition,
		{"tools": "tools", "__end__": "revise"},
	)
	builder.add_edge("tools", "revise")
	builder.add_edge("revise", "human_review")
	builder.add_conditional_edges("human_review", review_router)
	builder.add_edge("finalize", END)

	memory = MemorySaver()
	return builder.compile(checkpointer=memory)


def run_graph(args) -> None:
	graph = build_graph()
	thread_id = args.thread_id or str(uuid.uuid4())
	config = {"configurable": {"thread_id": thread_id}}

	if args.interactive_qa:
		vectorstore = build_vectorstore(args.pdf)
		retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
		print("\nInteractive RAG QA. Press Enter to exit.\n")
		while True:
			question = input("Ask a question: ").strip()
			if not question:
				break
			answer = answer_query_with_rag(retriever, question)
			print("\nAnswer:\n")
			print(answer)
			print()
		return

	initial_state: PostState = {
		"topic": args.topic,
		"audience": args.audience,
		"tone": args.tone,
		"constraints": args.constraints,
		"pdf_path": args.pdf,
		"messages": [],
		"retrieved_docs": [],
		"draft": "",
		"approved": False,
		"human_feedback": "",
		"final_post": "",
	}

	result = graph.invoke(initial_state, config)

	while "__interrupt__" in result:
		payload = normalize_interrupt_payload(result["__interrupt__"])
		print("\nHuman review needed:")
		print(payload.get("draft", ""))
		print()
		raw = input("Approve / edit / reject (or type your edit): ").strip()
		action = raw.lower() if raw else "approve"
		edit = ""
		if action == "edit":
			edit = input("Write your edits or notes: ").strip()
		elif action not in {"approve", "reject", "edit"}:
			# Treat any free text as edit instructions.
			action = "edit"
			edit = raw

		resume_payload = {"action": action, "edit": edit}
		result = graph.invoke(Command(resume=resume_payload), config)

	print("\nFinal post:\n")
	print(result.get("final_post", ""))


def parse_args():
	parser = argparse.ArgumentParser(description="RAG social post assistant")
	parser.add_argument("--pdf", required=True, help="Path to a PDF file")
	parser.add_argument("--topic", required=True, help="Post topic")
	parser.add_argument("--audience", default="general", help="Target audience")
	parser.add_argument("--tone", default="friendly", help="Tone (e.g., witty, formal)")
	parser.add_argument(
		"--constraints",
		default="Keep it under 120 words.",
		help="Extra constraints for the post",
	)
	parser.add_argument(
		"--interactive-qa",
		action="store_true",
		help="Ask questions interactively using the PDF RAG context",
	)
	parser.add_argument("--thread-id", default="", help="Reuse a thread id")
	return parser.parse_args()


if __name__ == "__main__":
	run_graph(parse_args())
