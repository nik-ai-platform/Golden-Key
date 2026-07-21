from fastapi import FastAPI

app = FastAPI(title="Golden Key API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
