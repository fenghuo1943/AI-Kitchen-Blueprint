from fastapi import FastAPI
from app.api.recipes import router as recipes_router

app = FastAPI(title="AI Kitchen Assistant", version="0.1.0")
app.include_router(recipes_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
