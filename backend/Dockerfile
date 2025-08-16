# 1. Base Image
FROM python:3.11-slim

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set Working Directory
WORKDIR /app

# 4. Install System Dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-lao \
    poppler-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 5. Copy Application Files
COPY . .

# 6. Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Expose Port
EXPOSE 8000

# 8. Run Application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
