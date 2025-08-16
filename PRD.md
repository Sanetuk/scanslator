### **Product Requirements Document: Lao-Korean Translator v1.0**
#### **1. Objective**

To create a web application that accurately translates text from uploaded PDF documents and image files from Lao to Korean. The system will prioritize a simple user workflow and reliable backend processing.

#### **2. User Stories**

*   **As a user, I want to upload a PDF file containing Lao text to get a Korean translation.**
*   **As a user, I want to upload an image file (JPG, PNG) containing Lao text to get a Korean translation.**
*   **As a user, I want to see the status of my translation job because it may take time to complete.**
*   **As a user, I want to view the original document page and the translated text side-by-side to verify accuracy.**
*   **As a user, I want to copy the full translated text to my clipboard.**
*   **As a user, I want to download the full translation as a single text file.**
*   **As a user, I want to download the full translation as a PDF file.**

#### **3. Functional Requirements**

**3.1. File Input**
*   **FR-1:** The system must accept file uploads via a web interface.
*   **FR-2:** Supported file formats are:
    *   PDF (`.pdf`)
    *   JPEG (`.jpeg`, `.jpg`)
    *   PNG (`.png`)
*   **FR-3:** The UI must provide feedback during the file upload process (e.g., a progress bar).

**3.2. Backend Processing Pipeline**
*   **FR-4:** The backend will assign a unique `task_id` to each upload.
*   **FR-5:** The system must identify the file's MIME type to determine the processing path.
    *   **If PDF:** Convert each page of the PDF into a separate high-resolution PNG image.
    *   **If Image:** Use the uploaded image file directly.
*   **FR-6:** The system must perform Optical Character Recognition (OCR) on each image (from FR-5) to extract Lao text.
    *   **OCR Engine:** Tesseract OCR.
    *   **Language Pack:** Lao (`lao`).
*   **FR-7:** All extracted Lao text from a single job must be concatenated into one string.
*   **FR-8:** The system must use the Gemini API to translate the concatenated Lao text to Korean.
    *   **Prompt:** `Translate the following from Lao to Korean: [Lao text here]`

**3.3. Status and Results**
*   **FR-9:** A REST API endpoint (`GET /api/status/{task_id}`) must provide the status of a processing job.
    *   **Statuses:** `PENDING`, `PROCESSING`, `COMPLETE`, `FAILED`.
*   **FR-10:** The frontend must poll the status endpoint after an upload to provide real-time feedback to the user.
*   **FR-11:** Upon `COMPLETE` status, the results page must display:
    *   The original source image(s).
    *   The final, full Korean translation in a text area.
*   **FR-12:** The UI must include a "Copy to Clipboard" button for the translated text.
*   **FR-13:** The UI must include a "Download" button that saves the full translation as a `.txt` file.
*   **FR-14:** The UI must include a "Download PDF" button that saves the full translation as a `.pdf` file.

#### **4. Non-Functional Requirements**

*   **NFR-1 (Performance):** All file processing (OCR, translation) must be handled asynchronously in the background to prevent UI blocking.
*   **NFR-2 (Usability):** The user interface must be clean, simple, and intuitive.
*   **NFR-3 (Dependencies):**
    *   **Backend Runtime:** Python 3.9+
    *   **Backend Framework:** FastAPI
    *   **Core Libraries:** `pdf2image`, `pytesseract`, `reportlab`
    *   **System-Level:** `poppler`, `Tesseract-OCR` (with `lao` language pack) must be installed on the host machine.

#### **5. System Architecture**

*   **Frontend:** Single Page Application (SPA).
    *   **Technology:** Vue.js.
*   **Backend:** Asynchronous API Server.
    *   **Technology:** Python / FastAPI.
*   **External Services:**
    *   **Translation:** Gemini API.
*   **Data Flow:**
    1.  Client uploads file to Backend.
    2.  Backend returns `task_id`.
    3.  Client polls status endpoint with `task_id`.
    4.  Backend processes file (PDF->Image -> OCR -> Translate -> PDF Generation).
    5.  Client fetches and displays results when status is `COMPLETE`.

#### **6. Future Enhancements (Beyond v1.0)**

*   **Scalability:** Implement a distributed task queue (e.g., Celery, RQ) for background jobs and persistent storage for job states.
*   **File Management:** Integrate with cloud storage (e.g., AWS S3, GCS) for uploaded files and generated PDFs, including lifecycle management.
*   **Robust Error Handling & Logging:** Implement more granular error handling and integrate with a centralized logging system (e.g., Sentry, ELK Stack).
*   **Performance Optimization:** Explore image pre-processing, parallel OCR, and potential GPU acceleration for image/OCR tasks.
*   **Font Management:** Improve font handling for PDF generation (e.g., configurable font paths, support for multiple font styles) and ensure consistent font rendering on the frontend using web fonts.
*   **Security Enhancements:** Implement stricter file upload validation, secure API key management for production, and refine CORS policies.
*   **User Experience Improvements:** Implement real-time progress feedback using WebSockets for long-running tasks.
*   **Expanded Language Support:** Support for additional source and target languages.
*   **User Accounts & History:** Implement user authentication and store translation history.
*   **In-app Editing:** Allow users to edit extracted or translated text directly within the application.
