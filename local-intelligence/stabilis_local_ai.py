#!/usr/bin/env python3

import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LIST = Path(__file__).with_name("sources.txt")

OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "hf.co/nomic-ai/nomic-embed-text-v1.5-GGUF:Q4_K_M"
CHAT_MODEL = "qwen3:4b"

CHUNK_SIZE = 1400
OVERLAP = 250
TOP_K = 5


def ollama(path, payload):
    req = urllib.request.Request(
        OLLAMA + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)


def embed(text):
    result = ollama(
        "/api/embed",
        {"model": EMBED_MODEL, "input": text},
    )
    return result["embeddings"][0]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def chunks(text):
    text = text.strip()
    out = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        piece = text[start:end].strip()

        if piece:
            out.append(piece)

        if end == len(text):
            break

        start = max(end - OVERLAP, start + 1)

    return out


def load_knowledge():
    records = []

    for raw in SOURCE_LIST.read_text().splitlines():
        relative = raw.strip()

        if not relative:
            continue

        path = ROOT / relative

        if not path.is_file():
            print(f"WARNING: missing {relative}")
            continue

        for number, text in enumerate(
            chunks(path.read_text(errors="ignore")), 1
        ):
            records.append(
                {
                    "source": relative,
                    "chunk": number,
                    "text": text,
                }
            )

    return records


def retrieve(question, records):
    q = embed(question)

    for record in records:
        if "embedding" not in record:
            record["embedding"] = embed(record["text"])

        record["score"] = cosine(q, record["embedding"])

    return sorted(
        records,
        key=lambda item: item["score"],
        reverse=True,
    )[:TOP_K]


def answer(question, evidence):
    context = "\n\n".join(
        f"[SOURCE: {item['source']} | CHUNK {item['chunk']}]\n"
        f"{item['text']}"
        for item in evidence
    )

    prompt = f"""
You are Stabilis Local Intelligence.

Answer ONLY from the supplied Stabilis evidence.

Rules:
- Do not invent facts.
- /no_think

Do not use outside knowledge.
- If the evidence is insufficient, explicitly say:
  "I don't have enough information in the Stabilis knowledge base."
- Cite supporting source filenames in the answer.
- Separate documented facts from reasonable interpretation.
- Keep the response operational and concise.

QUESTION:
{question}

STABILIS EVIDENCE:
{context}
"""

    result = ollama(
        "/api/generate",
        {
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 180,
                "temperature": 0.1
            },
        },
    )

    return result["response"]


def main():
    question = " ".join(sys.argv[1:]).strip()

    if not question:
        question = input("Ask Stabilis: ").strip()

    if not question:
        raise SystemExit("No question supplied.")

    print("\nLoading Stabilis knowledge...")
    records = load_knowledge()
    print(f"Loaded {len(records)} knowledge chunks.")

    print("Retrieving relevant evidence...")
    evidence = retrieve(question, records)

    print("\n=== RETRIEVED EVIDENCE ===")
    for item in evidence:
        print(
            f"{item['score']:.3f} | "
            f"{item['source']} | chunk {item['chunk']}"
        )

    print("\n=== STABILIS LOCAL INTELLIGENCE ===\n")
    print(answer(question, evidence))


if __name__ == "__main__":
    main()
