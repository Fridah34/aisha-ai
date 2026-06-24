import app.models
from app.conversations.router import router as conversations_router
from app.database import Base, engine

#from app.auth.knowledge_base import router as knowledge_base_router
from app.products.router import router as products_router
from app.routes.auth import router as auth_router
from app.settings.router import router as settings_router
from app.webhook.router import router as webhook_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI (
    title = "AISHA AI",
    description = "AI-powered Whatsapp sales assistant for African SMBs",
    version ="1.0.0"

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#==========ROUTES===============

app.include_router(webhook_router)
#app.include_router(knowledge_base_router)
app.include_router(products_router)
app.include_router(conversations_router)
app.include_router(settings_router)
app.include_router(auth_router)
 
#========ROOT ENDPOINT=============

@app.get("/", tags=["Info"])
def root():
    return {
        "message": "AISHA AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        }

@app.get("/health", tags=["Info"])
def health():
    return {"status": "healthy"}
    
# Local execution

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        reload=True,
        port=8000,
    )


