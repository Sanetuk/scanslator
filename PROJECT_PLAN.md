# Project Plan: Lao-Korean Translator

This document outlines the development plan and tracks the progress for building the Lao-Korean Translator application.

## Phase 1: Backend (FastAPI)

- [x] Setup FastAPI environment and `requirements.txt`.
- [x] Implement `POST /upload` endpoint to receive files and start a background task.
- [x] Implement `GET /api/status/{task_id}` to track job progress.
- [x] Implement `GET /api/result/{task_id}` to fetch the final translation.
- [x] Implement core processing logic:
    - [x] PDF/Image to Image conversion.
    - [x] OCR with Tesseract for Lao text extraction.
    - [x] Translation with the Gemini API.
- [x] Add CORS middleware to allow requests from the frontend.
- [x] Refine error handling for processing failures.
- [x] Ensure the Gemini API key is loaded securely (e.g., from an environment variable).

## Phase 2: Frontend (Vue.js)

- [x] Scaffold Vue.js 3 project using `npm create vue@latest`.
- [x] Install `axios` for API communication.
- [x] Create the main UI component (`App.vue`).
- [x] Implement the file upload interface.
- [x] Implement logic to call the `/upload` endpoint.
- [x] Implement status polling to the `/api/status/{task_id}` endpoint.
- [x] Implement the results display area for original images and translated text.
- [x] Implement "Copy to Clipboard" and "Download" functionality.
- [x] Implement PDF download functionality.
- [x] Improve UI/UX styling for a more polished and user-friendly interface.

## Phase 3: Testing & Documentation

- [ ] Perform end-to-end testing of the full user workflow.
- [ ] Update `README.md` with clear instructions on:
    - [x] System dependencies (Tesseract, Poppler).
    - [ ] How to set up the environment and API key.
    - [ ] How to run the backend and frontend servers.

## Phase 4: Future Enhancements & System Hardening

- [ ] **Scalability:** Implement a distributed task queue (e.g., Celery, RQ) for background jobs and persistent storage for job states.
- [ ] **File Management:** Integrate with cloud storage (e.g., AWS S3, GCS) for uploaded files and generated PDFs, including lifecycle management.
- [ ] **Robust Error Handling & Logging:** Implement more granular error handling and integrate with a centralized logging system (e.g., Sentry, ELK Stack).
- [ ] **Performance Optimization:** Explore image pre-processing, parallel OCR, and potential GPU acceleration for image/OCR tasks.
- [ ] **Font Management:** Improve font handling for PDF generation (e.g., configurable font paths, support for multiple font styles) and ensure consistent font rendering on the frontend using web fonts.
- [ ] **Security Enhancements:** Implement stricter file upload validation, secure API key management for production, and refine CORS policies.
- [ ] **User Experience Improvements:** Implement real-time progress feedback using WebSockets for long-running tasks.