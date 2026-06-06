# First Project: RAG Social Post Assistant

This project builds a beginner-friendly RAG pipeline that generates social media posts from a PDF. It includes:

- PDF ingestion and automatic vector store creation
- RAG retrieval (most important part)
- LangGraph state machine
- Human-in-the-loop approval
- Checkpointer for state
- Tools (date/time + hashtag helper)

## How it works (code workflow)

1. **Ingest PDF**
   - Load and split the PDF into chunks.
   - Build a local Chroma vector store.

2. **Retrieve context (RAG)**
   - Use the topic, audience, and tone as the query.
   - Fetch the top relevant chunks from the vector store.

3. **Draft a post**
   - LLM writes a short post using retrieved context.
   - The model can call tools (date/time + hashtags).

4. **Tools**
   - Tool outputs are added to the conversation state.
   - The draft is revised using tool output.

5. **Human in the loop**
   - The graph pauses and asks you to approve, edit, or reject.
   - You can provide edits or feedback.
   - If you edit, the assistant rewrites the post.

6. **Finalize**
   - Once approved, the final post is printed.

## Project workflow (big picture)

- Provide a PDF.
- The agent builds a vector store.
- The agent retrieves relevant context.
- The agent drafts a post with the context.
- You approve or edit the draft.
- The final post is produced.

## How to attach a PDF

Put your PDF anywhere you want, then pass the path to the script:

```bash
python app.py --pdf ./docs/my_file.pdf --topic "AI productivity tips"
```

If the file is in the same folder as the script:

```bash
python app.py --pdf ./my_file.pdf --topic "AI productivity tips"
```

## Setup

1. Activate your venv:

```bash
source /home/asad/LangChain/venv/bin/activate
```

2. Install dependencies (pick the embeddings provider you will use):

```bash
pip install langchain-core langgraph langchain-community langchain-text-splitters python-dotenv langchain-ollama chromadb pypdf
```

Optional embeddings:

- Google embeddings:
  ```bash
  pip install langchain-google-genai
  ```
- OpenAI embeddings:
  ```bash
  pip install langchain-openai
  ```
- Local embeddings:
  ```bash
  pip install sentence-transformers
  ```

3. Set environment variables (example for Groq):

```bash
export GROQ_API_KEY="your_key_here"
```

Optional:

```bash
export GROQ_MODEL="llama-3.1-8b-instant"
```

Ollama setup (recommended for local use):

```bash
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="gemma3:270m"
export EMBEDDINGS_PROVIDER="ollama"
export OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
```

Note: Some small Ollama models do not support tool calls. If you see a tools error,
disable tools with:

```bash
export TOOLS_ENABLED="false"
```

Make sure the models exist locally:

```bash
ollama pull gemma3:270m
ollama pull nomic-embed-text
```

4. Choose embeddings provider (optional but recommended):

- Use local embeddings (no external API key needed):
   ```bash
   export EMBEDDINGS_PROVIDER="local"
   ```
- Use Ollama embeddings:
   ```bash
   export EMBEDDINGS_PROVIDER="ollama"
   export OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
   ```
- Use OpenAI embeddings:
   ```bash
   export EMBEDDINGS_PROVIDER="openai"
   ```
- Use Google embeddings:
   ```bash
   export EMBEDDINGS_PROVIDER="google"
   export GOOGLE_EMBEDDING_MODEL="text-embedding-004"
   ```

## Run

```bash
python app.py --pdf ./docs/my_file.pdf --topic "AI productivity tips" --audience "founders" --tone "friendly"
```

## Interactive RAG Q&A (manual queries)

Ask your own questions against the PDF embeddings directly from the terminal:

```bash
python app.py --pdf ./docs/my_file.pdf --topic "AI" --interactive-qa
```

If you see a human review prompt, type:

- `approve`
- `edit` and then provide edits
- `reject` for a rewrite

## Notes

- The vector store is saved under `data/chroma` in this folder.
- If you change the PDF, the script rebuilds the vector store automatically.
- If you want to reuse a session, pass `--thread-id`.
