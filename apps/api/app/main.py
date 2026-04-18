from __future__ import annotations

import threading

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from app.config import Settings, get_settings
from app.media import MediaComposer
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CardChatRequest,
    CardChatResponse,
    CreateEntryRequest,
    CreateEntryResponse,
    EntryStatus,
    MissionLogCreate,
    UploadResponse,
)
from app.openai_service import OpenAIService
from app.pipeline import AnalysisPipeline
from app.store import LocalStore


def get_store(settings: Settings = Depends(get_settings)) -> LocalStore:
    return LocalStore(settings)


def get_ai(settings: Settings = Depends(get_settings)) -> OpenAIService:
    return OpenAIService(settings)


def get_pipeline(
    store: LocalStore = Depends(get_store),
    ai: OpenAIService = Depends(get_ai),
    settings: Settings = Depends(get_settings),
) -> AnalysisPipeline:
    return AnalysisPipeline(store, ai, MediaComposer(settings, store))


settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.cors_origin,
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4175",
        "https://diary-app.summit1123.co.kr",
        "https://app.summit1123.co.kr",
    ],
    allow_origin_regex=r"https?://((localhost|127\.0\.0\.1)(:\d+)?|([a-z0-9-]+\.)?summit1123\.co\.kr)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=settings.media_mount_dir), name="media")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/entries", response_model=CreateEntryResponse)
def create_entry(
    payload: CreateEntryRequest,
    store: LocalStore = Depends(get_store),
) -> CreateEntryResponse:
    entry = store.create_entry(payload.inputType)
    return CreateEntryResponse(entryId=entry.id, status=entry.status)


@app.get("/api/v1/entries")
def list_entries(store: LocalStore = Depends(get_store)) -> list[dict]:
    return [item.model_dump(mode="json") for item in store.list_entries()]


@app.post("/api/v1/entries/{entry_id}/upload", response_model=UploadResponse)
async def upload_entry_file(
    entry_id: str,
    file: UploadFile = File(...),
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    store: LocalStore = Depends(get_store),
) -> UploadResponse:
    try:
        entry = store.load_entry(entry_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file")

    entry.originalFilename = file.filename or "upload.bin"
    entry.originalFileUrl = store.save_upload(entry.id, entry.originalFilename, content)
    entry.status = EntryStatus.CREATED
    store.save_entry(entry)
    entry = pipeline.parse_upload(entry)

    return UploadResponse(
        entryId=entry.id,
        status=entry.status,
        rawText=entry.rawText,
        normalizedText=entry.normalizedText,
        parseWarnings=entry.parseWarnings,
        originalFileUrl=entry.originalFileUrl or "",
    )


@app.post("/api/v1/entries/{entry_id}/analyze", response_model=AnalyzeResponse)
def analyze_entry(
    entry_id: str,
    payload: AnalyzeRequest,
    pipeline: AnalysisPipeline = Depends(get_pipeline),
    store: LocalStore = Depends(get_store),
) -> AnalyzeResponse:
    try:
        entry = store.load_entry(entry_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc

    entry.normalizedText = payload.normalizedText
    entry.preferredModeId = payload.preferredModeId
    entry.status = EntryStatus.QUEUED
    store.save_entry(entry)

    job_id = store.next_job_id()
    threading.Thread(
        target=pipeline.run_analysis,
        args=(entry.id,),
        name=f"analysis-{entry.id}",
        daemon=False,
    ).start()

    return AnalyzeResponse(entryId=entry.id, jobId=job_id, status=entry.status)


@app.get("/api/v1/entries/{entry_id}")
def get_entry_status(entry_id: str, store: LocalStore = Depends(get_store)) -> dict:
    try:
        return store.status_response(entry_id).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc


@app.get("/api/v1/entries/{entry_id}/result")
def get_entry_result(entry_id: str, store: LocalStore = Depends(get_store)) -> dict:
    if not store.has_result(entry_id):
        raise HTTPException(status_code=404, detail="result not ready")
    return store.load_result(entry_id).model_dump(mode="json")


@app.post("/api/v1/entries/{entry_id}/cards/chat", response_model=CardChatResponse)
def chat_about_result_card(
    entry_id: str,
    payload: CardChatRequest,
    store: LocalStore = Depends(get_store),
    ai: OpenAIService = Depends(get_ai),
) -> CardChatResponse:
    try:
        entry = store.load_entry(entry_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="entry not found") from exc

    if not store.has_result(entry_id):
        raise HTTPException(status_code=404, detail="result not ready")

    result = store.load_result(entry_id)
    reply = ai.answer_card_chat(
        entry.normalizedText or entry.rawText,
        result,
        payload.cardKind,
        payload.message,
        payload.history,
    )
    return CardChatResponse(cardKind=payload.cardKind, reply=reply)


@app.post("/api/v1/entries/{entry_id}/mission-log")
def create_mission_log(
    entry_id: str,
    payload: MissionLogCreate,
    pipeline: AnalysisPipeline = Depends(get_pipeline),
) -> dict:
    mission = pipeline.create_mission_log(entry_id, payload.observationData, payload.reflection)
    return mission.model_dump(mode="json")


@app.get("/api/v1/entries/{entry_id}/mission-log")
def list_mission_logs(entry_id: str, store: LocalStore = Depends(get_store)) -> list[dict]:
    return [item.model_dump(mode="json") for item in store.list_mission_logs(entry_id)]


@app.exception_handler(FileNotFoundError)
def file_not_found_handler(_: Request, __: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "resource not found"})
