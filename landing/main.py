from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

app = FastAPI()

html = Path("index.html").read_text()

@app.get("/", response_class=HTMLResponse)
def root():
    return html

@app.get("/health")
def health():
    return {"status": "ok"}
