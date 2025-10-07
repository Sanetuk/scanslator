### **Product Requirements Document: Lao-Korean Translator v1.1**
#### **1. Objective**

Deliver a dependable translation service that converts Lao-language PDFs and images into polished Korean text through a web-based experience. The product must support concurrent users by separating orchestration concerns from the core translation engine so that jobs can be queued, monitored, and completed reliably.

#### **2. User Stories**

* **As a user, I want to upload a PDF containing Lao text and receive a Korean translation.**
* **As a user, I want to upload an image (JPG, JPEG, PNG) containing Lao text and receive a Korean translation.**
* **As a user, I want clear feedback (progress bar + status updates) while my file uploads and processes.**
* **As a user, I want to view the original document pages next to the translated text to verify accuracy.**
* **As a user, I want to copy the translated text to my clipboard.**
* **As a user, I want to download the translated text as `.txt` and `.pdf` artefacts.**

#### **3. Functional Requirements**

**3.1. Job Intake & Upload**
* **FR-1:** The system must accept file uploads through the web interface and stream them to the orchestration layer.
* **FR-2:** Supported file formats: PDF (`.pdf`), JPEG (`.jpeg`, `.jpg`), PNG (`.png`).
* **FR-3:** The UI must display an upload progress indicator while a file is being transferred.
* **FR-4:** Upon successful intake, the orchestrator must return a unique `job_id` and enqueue work for the translation engine.

**3.2. Processing Pipeline**
* **FR-5:** The orchestrator must determine processing steps based on MIME type. PDFs are converted to per-page images; images are used as-is.
* **FR-6:** Each job passes through the translation engine, which performs:
  * Page/image normalization and conversion to PNG.
  * OCR using Tesseract with the Lao (`lao`) language pack.
  * Concatenation of extracted Lao text.
  * Translation to Korean via the Gemini API using curated prompts and a refinement pass.
* **FR-7:** Original page renders must be preserved (base64 PNG) for presentation alongside results.
* **FR-8:** The engine must persist translated text and any generated artefacts (e.g., PDF) to shared storage for later retrieval.

**3.3. Status & Result Delivery**
* **FR-9:** The orchestration API must expose polling endpoints for status (`GET /jobs/{job_id}`) and results (`GET /jobs/{job_id}/result`).
* **FR-10:** Reported statuses must include at minimum: `PENDING`, `QUEUED`, `IMAGE_CONVERSION`, `OCR_PROCESSING`, `TRANSLATION_PROCESSING`, `REFINEMENT_PROCESSING`, `PDF_GENERATION`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
* **FR-11:** The frontend must poll for status changes every 2 seconds and update its display text accordingly.
* **FR-12:** When a job reaches `SUCCEEDED`, the results endpoint must provide:
  * Base64-encoded originals (ordered pages/images).
  * The final Korean translation (Markdown-compatible text).
  * Links or streams for `.txt` and `.pdf` downloads where available.
* **FR-13:** The UI must render translation output with Markdown formatting and offer "Copy", "Download .txt", and "Download .pdf" actions.
* **FR-14:** Users must be able to cancel in-flight jobs (`POST /jobs/{job_id}/cancel`); cancellations surface as `CANCELLED` status within 15 seconds.

#### **4. Non-Functional Requirements**

* **NFR-1 (Scalability):** Orchestration, job persistence, and worker execution must be horizontally scalable; no single instance may hold exclusive state.
* **NFR-2 (Performance):** The upload API must respond with a `job_id` within 2 seconds for files up to 20 MB. Background processing should begin within 5 seconds of enqueueing under nominal load.
* **NFR-3 (Usability):** The web UI must remain responsive, clearly communicating upload/progress states and warning users of failures.
* **NFR-4 (Security):** Secrets (e.g., Gemini API key) must never be logged or stored in source control. Environment configuration must rely on runtime injection.
* **NFR-5 (Reliability):** Orchestrator must persist job metadata and artefact locations durably to allow recovery after crash/restart.
* **NFR-6 (Dependencies):**
  * Backend runtime: Python 3.11+.
  * Backend framework: FastAPI for orchestration API; worker services may reuse FastAPI or lightweight runners.
  * Core libraries: `pdf2image`, `pytesseract`, `google-generativeai`, `reportlab`, `pymupdf`.
  * System-level: `poppler`, `tesseract-ocr`, `tesseract-ocr-lao` installed on worker hosts.

#### **5. System Architecture**

* **Frontend:** Vue.js SPA responsible for file uploads, status polling, and presenting translation results with markdown and image previews.
* **Orchestrator:** FastAPI-based service handling job intake, persistence, and queue interactions. Exposes `/jobs` endpoints to clients and `internal` endpoints (or message topics) to workers.
* **Workers / Translation Engine:** Stateless worker processes that consume jobs from the queue, execute the OCR/translation pipeline, upload artefacts, and signal completion/failure.
* **Shared Infrastructure:**
  * Message queue for job dispatch and cancellation.
  * Object storage for uploads and generated artefacts.
  * Relational or document store for job metadata and progress tracking.
* **Data Flow:**
  1. Client uploads a file to the orchestrator and receives `job_id`.
  2. Orchestrator stores metadata and enqueues work for workers.
  3. Worker pulls the job, runs the translation pipeline, and uploads artefacts.
  4. Worker reports progress and completion; orchestrator updates job status.
  5. Client polls orchestrator for status and fetches results when `SUCCEEDED`.

#### **6. Future Enhancements (Beyond v1.1)**

* **Streaming Feedback:** Upgrade polling to WebSocket push for real-time updates.
* **Advanced Scheduling:** Add per-user quotas, priorities, and reserved worker pools.
* **Extended Artefacts:** Provide side-by-side PDF outputs that embed both original and translated text.
* **User Accounts & History:** Offer authentication, job history, and re-download capabilities.
* **Expanded Language Support:** Generalise the engine for additional language pairs.
* **Observability:** Integrate structured logging, tracing, and metrics dashboards for orchestration and workers.
