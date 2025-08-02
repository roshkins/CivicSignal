
from os import environ
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
chroma_client = chromadb.Client()

CEREBRAS_API_KEY = environ.get("CEREBRAS_API_KEY")
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=CEREBRAS_API_KEY,
                api_base=" https://api.cerebras.ai/v1",
                model_name="qwen-3-235b-a22b-instruct-2507"
            )

collection = chroma_client.create_collection(name="my_collection")
collection.upsert(
    ids=["id1", "id2"],
    documents=[
        "This is a document about pineapple",
        "This is a document about oranges"
    ]
)
results = collection.query(
    query_texts=["This is a query document about hawaii"], # Chroma will embed this for you
    n_results=2 # how many results to return
)
print(results)
