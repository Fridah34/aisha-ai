from fastapi import FastAPI
from app.database import engine, Base
import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI (
    title = "AISHA AI",
    description = "AI-powered Whatsapp sales assistant for African SMBs",
    version ="1.0.0"
)

@app.get("/")
def root():
    return{ "message": "AISHA AI backend is running"}