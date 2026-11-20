# Stabilis Local Intelligence v0.1

Private, local operational intelligence for Stabilis Ops Group.

## Architecture

Stabilis knowledge documents
→ Nomic local embeddings
→ semantic retrieval
→ Qwen3 4B
→ grounded answer with source citation

## Models

- Generation: `qwen3:4b`
- Embeddings: `hf.co/nomic-ai/nomic-embed-text-v1.5-GGUF:Q4_K_M`

Both run locally through Ollama.

## Guardrails

The engine is instructed to:

- answer only from retrieved Stabilis evidence;
- not invent facts;
- not use outside knowledge;
- cite supporting Stabilis source files;
- separate documented facts from reasonable interpretation;
- refuse unsupported questions with:
  `I don't have enough information in the Stabilis knowledge base.`

## Run

Make sure Ollama is running and the required models are installed.

From the repository root:

```bash
python3 local-intelligence/console.py
