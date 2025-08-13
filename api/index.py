from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the FastAPI app from backend
from backend.app.main import app as fastapi_app

# Vercel will import this 'app' from api/index.py
app = fastapi_app

# Optionally, you can tweak CORS for Vercel preview domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
