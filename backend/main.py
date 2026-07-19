import app.models
from app.config import settings
from app.database import Base, engine
from app.routes.auth import router as auth_router
from app.conversations.router import router as conversations_router
from app.knowledge_base.router import router as knowledge_base_router
from app.products.router import router as products_router
from app.categories.router import router as categories_router
from app.orders.router import router as orders_router
from app.webhook.router import router as webhook_router
from app.settings.router import router as settings_router
from app.websocket.router import router as websocket_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# --- APPLICATION SETUP ---
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AISHA AI",
    description="AI-powered Whatsapp sales assistant for African SMBs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads/products", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- ROUTE REGISTRATION ---
app.include_router(websocket_router)
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(categories_router)
app.include_router(conversations_router)
app.include_router(orders_router)
app.include_router(settings_router)
app.include_router(knowledge_base_router)


@app.get("/")
def root():
    return {"message": "AISHA AI backend is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        reload=True,
        port=8000,
    )
