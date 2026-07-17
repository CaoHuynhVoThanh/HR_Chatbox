"""FastAPI integration point for the next phase.

No routes are exposed during the terminal-demo phase. The future API should create
one CVChatService session per authenticated user and enforce one uploaded CV.
"""

from fastapi import FastAPI

app = FastAPI(title="HR CV Chatbot", docs_url=None, redoc_url=None)

