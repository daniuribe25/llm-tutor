from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import chat, conversations

app = FastAPI(title="LLM Tutor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://llm-tutor-web-336010927888.southamerica-east1.run.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(conversations.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
