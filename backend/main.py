from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import ticker

app = FastAPI(title="Stock Sentiment Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ticker.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Sentiment Analysis API"}

@app.get("/health")
def healthcheck():
    return {"status": "ok"}
