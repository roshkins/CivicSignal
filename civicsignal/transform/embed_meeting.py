#!/usr/bin/env python3

import html
import html.parser
import http
from os import environ
import os
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from transformers import AutoTokenizer, BertTokenizerFast

from civicsignal.utils import Meeting

class MeetingRAGDb:
    def __init__(self, db_path: Path = Path("sf_meetings_rag_db"), embedding_function = DefaultEmbeddingFunction):
        # TODO: support remote vector db
        self.db = chromadb.PersistentClient(path=db_path)
        self.collection = self.db.get_or_create_collection(name="sf_meetings", embedding_function=embedding_function())

    def embed_meeting(self, meeting: Meeting):
        paragraphs = meeting.transcript
        ids = []
        documents = []
        metadatas = []
        for paragraph in paragraphs:
            ids.append(f"{meeting.date}_{meeting.group}_{paragraph.start_time}_{paragraph.end_time}")
            documents.append(paragraph.text)
            metadata = {
                "start_time": paragraph.start_time,
                "end_time": paragraph.end_time,
                "speaker_id": paragraph.speaker_id,
                "meeting_date": meeting.date.isoformat(),
                "meeting_group": meeting.group,
                "video_url": meeting.video_url,
            }
            metadatas.append(metadata)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search_meetings(self, query: str, n_results: int = 10):
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results