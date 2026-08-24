from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.settings import ALLOWED_ORIGIN

app = FastAPI(title="Sistema de Calificación OMR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def salud() -> dict:
    return {"status": "ok"}
