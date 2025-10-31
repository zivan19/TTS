# TTS Demo FastAPI Server

This repository contains a minimal FastAPI application that exposes a web UI to upload text files, configure synthesis options, and download generated audio/subtitles. The included synthesizer is a lightweight placeholder that simulates audio output so the full stack can be exercised without heavyweight model dependencies.

## Getting started

1. Install dependencies (consider using a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

2. Launch the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

3. Open <http://localhost:8000> in your browser. Use the form to upload a UTF-8 text file, choose a voice, and adjust the speaking speed.

## API overview

- `POST /api/jobs` – Upload a text file and start a synthesis job. Returns a `job_id`.
- `GET /api/jobs/{job_id}` – Retrieve the latest job metadata.
- `GET /api/jobs/{job_id}/result/audio` – Download the generated MP3.
- `GET /api/jobs/{job_id}/result/subtitles` – Download the generated SRT subtitles.
- `GET /api/voices` – List available voices exposed by the synthesizer.
- `WS /api/jobs/{job_id}/events` – Subscribe to live progress updates.

The included UI uses these endpoints to show progress in real time and reveal download links when synthesis completes.
