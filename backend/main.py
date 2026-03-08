from fastapi import FastAPI
from api import ticker

app = FastAPI(title="Stock Sentiment Analysis API")

app.include_router(ticker.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Sentiment Analysis API"}
