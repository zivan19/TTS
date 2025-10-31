"""FastAPI application exposing a minimal TTS web UI."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import WebSocket, WebSocketDisconnect
from starlette.requests import Request

from .config import Settings, get_settings
from .core import DummySynthesizer, SynthesisPipeline
from .jobs import JobManager


settings = get_settings()
app = FastAPI(title=settings.ui_title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

job_manager = JobManager()
synthesizer = DummySynthesizer()
pipeline = SynthesisPipeline(job_manager, synthesizer=synthesizer)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, settings: Settings = Depends(get_settings)) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "title": settings.ui_title})


@app.get("/api/voices")
async def list_voices() -> Dict[str, List[Dict[str, str]]]:
    return {"voices": [{"id": voice, "label": voice.title()} for voice in synthesizer.available_voices()]}


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    text_file: UploadFile = File(...),
    voice: str = Form("neutral"),
    speed: float = Form(1.0),
    energy: Optional[float] = Form(None),
) -> JSONResponse:
    contents = await text_file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Unable to decode file as UTF-8") from exc

    segments = [line.strip() for line in decoded.splitlines() if line.strip()]
    if not segments:
        raise HTTPException(status_code=400, detail="The uploaded file does not contain any text")

    job_id = secrets.token_hex(8)
    output_dir = settings.jobs_dir / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    state = await job_manager.create_job(
        job_id,
        filename=text_file.filename or "input.txt",
        voice=voice,
        speed=speed,
        settings={"energy": energy},
        output_dir=output_dir,
    )

    background_tasks.add_task(_run_pipeline, state.job_id, segments, voice, speed)

    return JSONResponse({"job_id": state.job_id})


async def _run_pipeline(job_id: str, segments: list[str], voice: str, speed: float) -> None:
    try:
        await pipeline.run(job_id, segments, voice, speed)
    except Exception as exc:  # pragma: no cover - logging/propagation only
        await job_manager.update(job_id, status="failed", message="Job failed", error=str(exc))


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str) -> Dict[str, str]:
    state = await job_manager.get_job(job_id)
    return state.to_dict()


@app.get("/api/jobs/{job_id}/result/audio")
async def download_audio(job_id: str) -> FileResponse:
    state = await job_manager.get_job(job_id)
    if state.status != "completed" or not state.audio_path:
        raise HTTPException(status_code=404, detail="Audio not available yet")
    return FileResponse(state.audio_path, media_type="audio/mpeg", filename=f"{job_id}.mp3")


@app.get("/api/jobs/{job_id}/result/subtitles")
async def download_subtitles(job_id: str) -> FileResponse:
    state = await job_manager.get_job(job_id)
    if state.status != "completed" or not state.subtitle_path:
        raise HTTPException(status_code=404, detail="Subtitles not available yet")
    return FileResponse(state.subtitle_path, media_type="application/x-subrip", filename=f"{job_id}.srt")


@app.websocket("/api/jobs/{job_id}/events")
async def job_events(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    queue = None
    try:
        queue = await job_manager.subscribe(job_id)
    except HTTPException as exc:
        await websocket.send_json({"event": "error", "detail": exc.detail})
        await websocket.close(code=1008)
        return

    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("status") in {"completed", "failed"}:
                await websocket.close(code=1000)
                break
    except WebSocketDisconnect:
        pass
    finally:
        if queue is not None:
            await job_manager.unsubscribe(job_id, queue)


__all__ = ["app"]
