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

## Deployment & Environment Setup

### Current Progress (as of 2025-08-16)

- [x] **Frontend Deployment Configuration:**
    - Configured frontend to use `VITE_APP_BACKEND_API_URL` environment variable for backend communication.
    - Updated `frontend/Dockerfile` to a multi-stage build for Docker-based frontend deployment.
    - Instructed on setting `VITE_APP_BACKEND_API_URL` in Render's static site environment variables.
    - Instructed on deploying frontend as a static site on Render (Build Command: `yarn install && yarn build`, Publish Directory: `frontend/dist`).

- [x] **Backend Deployment & Runtime Fixes:**
    - Identified and fixed CORS issue: Implemented a maintainable solution using `ALLOWED_FRONTEND_ORIGIN` environment variable in `backend/main.py` for dynamic origin allowance.
    - Fixed Poppler issue: Removed explicit `poppler_path` from `backend/main.py`, allowing `pdf2image` to find system-installed Poppler.
    - Fixed Tesseract issue: Removed explicit `pytesseract.pytesseract.tesseract_cmd` from `backend/main.py`, allowing `pytesseract` to find system-installed Tesseract.
    - Instructed on setting `ALLOWED_FRONTEND_ORIGIN` in Render's backend service environment variables.
    - Instructed on redeploying backend after each code change.

- [x] **Local Docker Development Environment Setup:**
    - Created `frontend/Dockerfile` for multi-stage build of the frontend.
    - Created `docker-compose.yml` to orchestrate local Docker deployment of both frontend and backend services.
    - Provided instructions for running the project locally using `docker compose up --build`, including `GEMINI_API_KEY` setup.
    - Clarified that local Docker setup resolves pathing issues and provides a consistent environment with Render.

### Next Steps

- [ ] **Verify Full Translation Flow on Render:** Confirm that the entire translation process (upload, OCR, Gemini translation, result display) works correctly on the Render-deployed services.
- [ ] **Test Local Docker Setup:** Fully test the project running locally via `docker compose` to ensure all functionalities are working as expected.
- [ ] **Update `README.md`:**
    - Add detailed instructions for local Docker setup.
    - Update system dependencies section to reflect Docker-based approach vs. local installation.
    - Provide clear guidance on environment variable management for both local and Render deployments.
