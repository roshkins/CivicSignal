"""Given a topic find similar topics from the archive."""

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from civicsignal.transform.embed_meeting import MeetingRAGDb


def search_for_similar_topics(topic: str, n_results: int = 10):
    # search rag db for similar topics
    rag_db = MeetingRAGDb()
    results = rag_db.search_meetings(topic, n_results)

    # return the similar topics
    return results

if __name__ == "__main__":
    results = search_for_similar_topics("housing", n_results=10)
    print(results)