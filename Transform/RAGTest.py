import html
import html.parser
import http
from os import environ
import os
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import httptools
import httpx
from bs4 import BeautifulSoup
from transformers import AutoTokenizer

chroma_client = chromadb.Client()

qwen_embedding_function = embedding_functions.DefaultEmbeddingFunction()
file_path = "transcript1.html"

transcript1 = ""
if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        transcript1 = f.read()
else:
    transcript1_req = httpx.get("https://sanfrancisco.granicus.com/TranscriptViewer.php?view_id=10&clip_id=50523", timeout=30).iter_text()

    for part in transcript1_req:
        transcript1 += part
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(transcript1)

beautiful_soup = BeautifulSoup(transcript1, "html.parser")
transcript1 = beautiful_soup.get_text(separator="\n", strip=True)

tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2") 

tokens = tokenizer(transcript1)

token_count = len(tokens['input_ids'])
print(f"There are {token_count} tokens")

token_limit = 512

# Split transcript into chunks that fit within the token limit
transcript_chunks = []
current_chunk = []
current_length = 0

for token in tokens['input_ids']:
    current_chunk.append(token)
    current_length += 1
    if current_length >= token_limit:
        transcript_chunks.append(current_chunk)
        current_chunk = []
        current_length = 0

if current_chunk:
    transcript_chunks.append(current_chunk)
docs=[
        "This is a document about pineapple",
        "This is a document about oranges",
    ]

transcript_chunks.extend([tokenizer(doc)['input_ids'] for doc in docs])

# Embed each chunk for adding to rag
snippets = tokenizer.batch_decode(transcript_chunks, skip_special_tokens=False)

collection = chroma_client.create_collection(name="my_collection", embedding_function=qwen_embedding_function)
collection.upsert(
    ids=[*["transcript_chunk_" + str(i) for i in range(len(transcript_chunks))]],
    documents=snippets
)
# "This is a query document about hawaii",
results = collection.query(
    query_texts=[ "What votes were cast?"], # Chroma will embed this for you
    n_results=10 # how many results to return
)
print(results)
