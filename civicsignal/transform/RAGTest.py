#!/usr/bin/env python3

import datetime
import os

# --- Clean version: Use paragraphs and sentences, add topics as metadata, and chunk by token limit ---
import json
import chromadb
import chromadb.config
from transformers import AutoTokenizer

transcript_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "transcript.txt")

persist_directory = "chroma_persist"
chroma_client = chromadb.Client(chromadb.config.Settings(persist_directory=persist_directory))

# Load tokenizer for sentence-transformers/all-MiniLM-L6-v2
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
TOKEN_LIMIT = 512

transcript_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "transcript.txt")
with open(transcript_json_path, "r", encoding="utf-8") as f:
    transcript_data = json.load(f)

paragraphs = paragraphs = (
    transcript_data.get("channels", [{}])[0]
    .get("alternatives", [{}])[0]
    .get("paragraphs", {})
    .get("paragraphs", [])
)

chunks = []
chunk_metadatas = []
current_chunk = []
current_metadata = []
current_token_count = 0

for para_idx, paragraph in enumerate(paragraphs):
    para_topics = paragraph.get("topics", [])
    speaker = paragraph.get("speaker", 0)
    num_words = paragraph.get("num_words")
    for sent_idx, sentence in enumerate(paragraph.get("sentences", [])):
        text = sentence.get("text", "")
        sent_start = sentence.get("start")
        sent_end = sentence.get("end")
        tokens = tokenizer.encode(text, add_special_tokens=False)
        if current_token_count + len(tokens) > TOKEN_LIMIT and current_chunk:
            # Commit current chunk
            chunks.append(" ".join(current_chunk))
            chunk_metadatas.append({"sentences": json.dumps(current_metadata)})
            current_chunk = []
            current_metadata = []
            current_token_count = 0
        current_chunk.append(text)
        current_metadata.append({
            "start": sent_start,
            "end": sent_end,
            "speaker": speaker,
            "num_words": num_words,
            "topics": para_topics,
            "para_idx": para_idx,
            "sent_idx": sent_idx
        })
        current_token_count += len(tokens)
# Add any remaining chunk
if current_chunk:
    chunks.append(" ".join(current_chunk))
    chunk_metadatas.append({"sentences": json.dumps(current_metadata)})

chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]

collection = chroma_client.create_collection(name="my_collection")
collection.upsert(
    ids=chunk_ids,
    documents=chunks,
    metadatas=chunk_metadatas
)

# Example query
results = collection.query(
    query_texts=["What votes were cast?"],
    n_results=10
)
print(results)
