"""Job management utilities for the TTS FastAPI server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status


JobStatusLiteral = str


@dataclass
class JobState:
    """In-memory representation of a synthesis job."""

    job_id: str
    filename: str
    voice: str
    speed: float
    settings: Dict[str, Any]
    created_at: datetime
    output_dir: Path
    status: JobStatusLiteral = "queued"
    progress: float = 0.0
    message: str = "Queued"
    updated_at: datetime = field(default_factory=datetime.utcnow)
    audio_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "job_id": self.job_id,
            "filename": self.filename,
            "voice": self.voice,
            "speed": self.speed,
            "settings": self.settings,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.audio_path:
            data["audio_path"] = str(self.audio_path)
        if self.subtitle_path:
            data["subtitle_path"] = str(self.subtitle_path)
        if self.error:
            data["error"] = self.error
        return data


class JobManager:
    """Manage job lifecycles and websocket listeners."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobState] = {}
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        job_id: str,
        filename: str,
        voice: str,
        speed: float,
        settings: Dict[str, Any],
        output_dir: Path,
    ) -> JobState:
        state = JobState(
            job_id=job_id,
            filename=filename,
            voice=voice,
            speed=speed,
            settings=settings,
            created_at=datetime.utcnow(),
            output_dir=output_dir,
        )
        async with self._lock:
            self._jobs[job_id] = state
        await self._broadcast(job_id, self._event_payload(state))
        return state

    async def get_job(self, job_id: str) -> JobState:
        async with self._lock:
            state = self._jobs.get(job_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return state

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if job_id not in self._jobs:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            listeners = self._listeners.setdefault(job_id, [])
            listeners.append(queue)
            snapshot = self._event_payload(self._jobs[job_id], event="snapshot")
        await queue.put(snapshot)
        return queue

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            listeners = self._listeners.get(job_id)
            if not listeners:
                return
            if queue in listeners:
                listeners.remove(queue)
            if not listeners:
                self._listeners.pop(job_id, None)

    async def update(
        self,
        job_id: str,
        *,
        status: Optional[JobStatusLiteral] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        audio_path: Optional[Path] = None,
        subtitle_path: Optional[Path] = None,
        error: Optional[str] = None,
    ) -> JobState:
        async with self._lock:
            state = self._jobs.get(job_id)
            if not state:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
            if status is not None:
                state.status = status
            if progress is not None:
                state.progress = progress
            if message is not None:
                state.message = message
            if audio_path is not None:
                state.audio_path = audio_path
            if subtitle_path is not None:
                state.subtitle_path = subtitle_path
            if error is not None:
                state.error = error
            state.updated_at = datetime.utcnow()
            payload = self._event_payload(state)
        await self._broadcast(job_id, payload)
        return state

    async def _broadcast(self, job_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            listeners = list(self._listeners.get(job_id, []))
        if not listeners:
            return
        await asyncio.gather(*(listener.put(payload) for listener in listeners))

    def _event_payload(self, state: JobState, *, event: str = "update") -> Dict[str, Any]:
        payload = state.to_dict()
        payload["event"] = event
        return payload


__all__ = ["JobManager", "JobState"]
