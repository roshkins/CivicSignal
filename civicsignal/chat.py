#!/usr/bin/env python3
"""
Chat interface for CivicSignal using Cerebras SDK.
Provides an interactive chat experience with similar topics search functionality.
"""

import json
import datetime
import os
import sys
from functools import partial
from typing import List, Dict, Any, Optional, Callable, Literal
from pathlib import Path
from dataclasses import dataclass


import marimo as mo
from cerebras.cloud.sdk import Client as CerebrasCloudClient
from cerebras.cloud.sdk.types.chat.chat_completion import ChatCompletionResponseChoiceMessage as CerebrasChatMessage

from civicsignal.output.similar_topics import search_for_similar_topics
from civicsignal.utils import Paragraph

class ChatMessage(CerebrasChatMessage, mo.ai.ChatMessage):
    """Chat message class that combines Cerebras and Marimo chat message classes.
    They largely already overlap, so we just inherit from both."""
    pass

class CivicSignalChat:
    """Interactive chat interface for CivicSignal using Cerebras SDK."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the chat interface.
        
        Args:
            api_key: Cerebras API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Cerebras API key not found. Please set CEREBRAS_API_KEY environment variable "
                "or pass it to the constructor."
            )
        
        self.client = CerebrasCloudClient(api_key=self.api_key)
        self.create_completion = partial(self.client.chat.completions.create, model="qwen-3-32b")
        self.conversation_history: List[ChatMessage] = []

        # store the reference video url for the last message, used in UI
        self._reference_video_url = None
        self._reference_video_start_timestamp = None
        self._reference_video_end_timestamp = None
        
    def _format_similar_topics(self, results: Dict[str, Any]) -> str:
        """Format similar topics results for display."""
        if not results or not results.get('documents'):
            return "No similar topics found."
        
        formatted_results = []
        documents = results['documents'][0]  # First query results
        metadatas = results['metadatas'][0]  # First query metadata
        distances = results['distances'][0]  # First query distances
        
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances), 1):
            similarity_score = 1 - distance  # Convert distance to similarity
            start_time = float(metadata.get('start_time', 0))
            end_time = float(metadata.get('end_time', 0))
            start_time_str = Paragraph._time_to_str(start_time)
            end_time_str = Paragraph._time_to_str(end_time)
            formatted_results.append(
                f"{i}. **Similarity: {similarity_score:.2%}**\n"
                f"   **Time:** {start_time_str} - {end_time_str} ({start_time} - {end_time} seconds)\n"
                f"   **Speaker:** {metadata.get('speaker_id', 'Unknown')}\n"
                f"   **Content:** {doc[:200]}{'...' if len(doc) > 200 else ''}\n"
                f"   **Video URL:** {metadata.get('video_url', 'N/A')}\n"
            )
        
        return "\n".join(formatted_results)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the chat interface."""
        today = datetime.date.today().isoformat()
        return f"""You are CivicSignal, an AI assistant that helps users understand civic meetings and government proceedings in San Francisco. 

Today's date is {today}.

Your capabilities:
1. Answer questions about civic meetings, government processes, and local issues
2. Search for similar topics from archived meeting transcripts
3. Provide context and insights about government discussions

When a user asks about a specific topic, you can search for similar discussions in the meeting archives. Always be helpful, accurate, and provide relevant context from the civic domain.

Format your responses clearly and use markdown when appropriate."""
    

    def _build_tools(self) -> List[Dict[str, Any]]:
        """Build the tools for the chat interface."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_database",
                    "strict": True,
                    "description": "Search for information from archived meeting transcripts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search for"
                            },
                            "n_results": {
                                "type": "integer",
                                "description": "The number of results to return"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "display_video",
                    "strict": True,
                    "description": "Display the relevant video for the last message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL of the video to display"
                            },
                            "start_time": {
                                "type": "number",
                                "description": "The start time of the video to display"
                            },
                            "end_time": {
                                "type": "number",
                                "description": "The end time of the video to display"
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        ]
        return tools

    @property
    def reference_video_url(self) -> Optional[str]:
        """Get the reference video URL for a query."""
        if not self.conversation_history:
            return None
        return self._reference_video_url

    def _display_video(self, url: str, start_time: Optional[float] = None, end_time: Optional[float] = None):
        """Display the video for the last message."""
        if start_time or end_time:
            url += "?"
            params = []
            if start_time:
                params.append(f"entertime={start_time}")
            if end_time:
                params.append(f"stoptime={end_time}")
            url += "&".join(params)
        self._reference_video_url = url
        self._reference_video_start_timestamp = start_time
        self._reference_video_end_timestamp = end_time
        return f"Displaying video for {url}"
    
    def _get_cerebras_response(self, messages: List[ChatMessage]) -> ChatMessage:
        """Get response from Cerebras model."""
        try:
            # Use Cerebras Cloud API to generate response
            response = self.create_completion(
                messages=messages,
                max_tokens=5000,
                temperature=0.7,
                stream=False,
                tools=self._build_tools(),
                parallel_tool_calls=False,
            )

            # if response.tool_calls:
            #     for tool_call in response.tool_calls:
            #         self._handle_tool_call(tool_call, messages)
            
            return response.choices[0].message
            
        except Exception as e:
            return ChatMessage(role="system", content=f"Error generating response: {str(e)}")

    def _add_tool_message(self, content: str, tool_call_id: str, messages: List[ChatMessage]) -> str:
        """Add a tool message to the conversation history."""
        tool_message = ChatMessage(
            role="tool",
            content=content,
            tool_call_id=tool_call_id
        )
        new_messages = [tool_message]
        response = self._get_cerebras_response(messages=messages + new_messages)
        # get final response from model
        if response:
            new_messages.append(ChatMessage(role="assistant", content=response.content))
        return new_messages

    def _handle_tool_call(self, tool_call: Any, messages: List[ChatMessage]) -> str:
        """Handle a tool call."""
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        new_messages = []
        if tool_name == "search_database":
            similar_topics = search_for_similar_topics(tool_args["query"], tool_args.get("n_results", 10))
            similar_topics_formatted = self._format_similar_topics(similar_topics)
            new_messages = self._add_tool_message(similar_topics_formatted, tool_call.id, messages)
        # elif tool_name == "search_for_video":
        elif tool_name == "display_video":
            self._display_video(tool_args["url"], tool_args.get("start_time", None), tool_args.get("end_time", None))
            new_messages = self._add_tool_message(f"Displaying video for {tool_args['url']}", tool_call.id, messages)

        self.conversation_history.extend(new_messages)
        return messages + new_messages
        
    
    def chat(self, user_input: str) -> str:
        """
        Process a user input and return a response.
        
        Args:
            user_input: The user's question or input
            
        Returns:
            The AI's response
        """
        
        # Build conversation messages
        messages = [
            ChatMessage(
                role="system",
                content=self._build_system_prompt()
            ),
        ]
        
        # Add conversation history for context
        for msg in self.conversation_history[-4:]:  # Keep last 4 messages for context
            messages.append(msg)

        messages.append(ChatMessage(role="user", content=user_input))

        self.conversation_history.append(ChatMessage(role="user", content=user_input))

        # Get response from Cerebras
        response = self._get_cerebras_response(messages)
        self.conversation_history.append(ChatMessage(role="assistant", content=response.content))

        if response.tool_calls:
            for tool_call in response.tool_calls:
                self._handle_tool_call(tool_call, messages)
        
        return response

    # def _messages_for_marimo(self) -> List[ChatMessage]:
    #     """Convert conversation history to Marimo messages."""
    #     return [
    #         ChatMessage(
    #             role=msg.role if msg.role != "tool" else "system", # marimo doesn't support tool messages
    #             content=msg.content,
    #         ) for msg in self.conversation_history]
    
    
    def interactive_chat(self):
        """Start an interactive chat session."""
        print("🤖 Welcome to CivicSignal Chat!")
        print("I can help you explore civic meetings and government discussions in San Francisco.")
        print("Type 'quit', 'exit', or 'bye' to end the session.\n")
        
        while True:
            try:
                user_input = input("👤 Citizen: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                    print("🤖 Thanks for using CivicSignal Chat! Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Thinking...")
                response = self.chat(user_input)
                print(f"🤖 CivicSignal: {response.content}\n")
                
            except KeyboardInterrupt:
                print("\n🤖 Chat session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"🤖 Error: {str(e)}\n")
    
    def __call__(self, messages: List[ChatMessage], config: Dict[str, Any] = {}) -> str:
        """Chat interface for OOP usage.
        Compatible with Marimo's ai.chat interface.
        
        Args:
            messages: List of ChatMessage objects
            config: Dictionary of configuration options
            
        Returns:
            The AI's response
        """
        self.chat(messages[-1].content)
        return self.conversation_history[-1].content

def main():
    """Main entry point for the chat interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CivicSignal Chat Interface")
    parser.add_argument(
        "--api-key", 
        help="Cerebras API key (or set CEREBRAS_API_KEY environment variable)"
    )
    parser.add_argument(
        "--query", 
        help="Single query to process (non-interactive mode)"
    )
    
    args = parser.parse_args()
    
    try:
        chat = CivicSignalChat(api_key=args.api_key)
        
        if args.query:
            # Single query mode
            response = chat.chat(args.query)
            print(f"Query: {args.query}")
            print(f"Response: {response}")
        else:
            # Interactive mode
            chat.interactive_chat()
            
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
