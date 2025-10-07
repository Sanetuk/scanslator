<template>
  <div id="app">
    <header class="header">
      <h1>Logos</h1>
      <p>Upload a PDF or Image to translate Lao text to Korean</p>
    </header>

    <main class="main-content">
      <div class="upload-section">
        <div class="file-input-wrapper">
          <label for="file-upload" class="file-label">
            <span v-if="!file">Choose File</span>
            <span v-else>{{ file.name }}</span>
          </label>
          <input id="file-upload" type="file" @change="handleFileUpload" accept=".pdf,.jpg,.jpeg,.png">
        </div>
        <button @click="submitFile" :disabled="!file || isLoading" class="translate-button">
          <span v-if="!isLoading">Upload and Translate</span>
          <span v-else>{{ isUploading ? 'Uploading...' : 'Processing...' }}</span>
        </button>
        <div v-if="isUploading" class="progress-container">
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
          <span class="progress-label">{{ uploadProgress }}%</span>
        </div>
      </div>

      <div v-if="task_id || isUploading" class="status-section">
        <div :class="['status-card', status ? status.toLowerCase() : '']">
          <p><strong>Status:</strong> {{ displayStatus }}</p>
          <div v-if="isLoading && !isUploading" class="loader"></div>
        </div>
      </div>

      <div v-if="status === 'COMPLETE'" class="results-section">
        <div class="result-panel translation-panel">
          <h2>Korean Translation</h2>
          <div class="markdown-output" v-html="renderedTranslatedText"></div>
          <div class="button-group">
            <button @click="copyToClipboard">Copy Text</button>
            <button @click="downloadTranslation">Download .txt</button>
            <button @click="downloadPdf">Download .pdf</button>
          </div>
        </div>
        <div v-if="originalImages.length" class="result-panel images-panel">
          <h2>Original Document</h2>
          <div class="image-gallery">
            <img
              v-for="(image, index) in originalImages"
              :key="index"
              :src="`data:image/png;base64,${image}`"
              :alt="`Original page ${index + 1}`"
            >
          </div>
        </div>
      </div>

      <div v-if="status === 'FAILED'" class="error-section">
        <p>Translation failed. Please try again or use a different file.</p>
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
import { marked } from 'marked';

// Configure marked to use GitHub Flavored Markdown (GFM)
marked.setOptions({
  gfm: true,
  breaks: true, // Enable GFM line breaks
});

export default {
  data() {
    return {
      file: null,
      task_id: null,
      status: null,
      translated_text: '',
      originalImages: [],
      polling: null,
      uploadProgress: 0,
      isUploading: false,
    };

  },
  computed: {
    isLoading() {
      return this.isUploading || this.status === 'PENDING' || this.status === 'PROCESSING' ||
             this.status === 'IMAGE_CONVERSION' || this.status === 'OCR_PROCESSING' ||
             this.status === 'TRANSLATION_PROCESSING' || this.status === 'REFINEMENT_PROCESSING' ||
             this.status === 'PDF_GENERATION';
    },
    renderedTranslatedText() {
      return marked(this.translated_text || '');
    },
    displayStatus() {
      if (this.isUploading) {
        return 'Uploading file...';
      }
      switch (this.status) {
        case 'PENDING':
          return 'Job queued...';
        case 'PROCESSING':
          return 'Processing...';
        case 'IMAGE_CONVERSION':
          return 'Converting images...';
        case 'OCR_PROCESSING':
          return 'Running OCR...';
        case 'TRANSLATION_PROCESSING':
          return 'Translating text...';
        case 'REFINEMENT_PROCESSING':
          return 'Refining translation...';
        case 'PDF_GENERATION':
          return 'Preparing PDF...';
        case 'COMPLETE':
          return 'Translation complete!';
        case 'FAILED':
          return 'Translation failed.';
        default:
          return 'Waiting...';
      }
    }
  },
  methods: {
    handleFileUpload(event) {
      this.file = event.target.files[0] || null;
      this.resetState(true);
    },
    async submitFile() {
      if (!this.file || this.isUploading) {
        return;
      }

      const formData = new FormData();
      formData.append('file', this.file);

      this.isUploading = true;
      this.uploadProgress = 0;
      this.status = null;
      this.translated_text = '';
      this.originalImages = [];

      try {
        const response = await axios.post(`${import.meta.env.VITE_APP_BACKEND_API_URL}/upload/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (event) => {
            if (event.total) {
              this.uploadProgress = Math.round((event.loaded / event.total) * 100);
            } else {
              this.uploadProgress = Math.min(99, this.uploadProgress + 1);
            }
          },
        });
        this.task_id = response.data.task_id;
        this.status = 'PENDING';
        this.pollStatus();
        this.uploadProgress = 100;
      } catch (error) {
        console.error('Error uploading file:', error);
        this.status = 'FAILED';
      } finally {
        this.isUploading = false;
      }
    },
    pollStatus() {
      if (this.polling) {
        clearInterval(this.polling);
      }
      this.polling = setInterval(async () => {
        try {
          const response = await axios.get(`${import.meta.env.VITE_APP_BACKEND_API_URL}/api/status/${this.task_id}`);
          this.status = response.data.status;
          if (this.status === 'COMPLETE') {
            clearInterval(this.polling);
            this.polling = null;
            this.fetchResults();
          } else if (this.status === 'FAILED') {
            clearInterval(this.polling);
            this.polling = null;
          }
        } catch (error) {
          console.error('Error polling status:', error);
          this.status = 'FAILED';
          clearInterval(this.polling);
          this.polling = null;
        }
      }, 2000);
    },
    async fetchResults() {
      try {
        const response = await axios.get(`${import.meta.env.VITE_APP_BACKEND_API_URL}/api/result/${this.task_id}`);
        this.translated_text = response.data.translated_text || '';
        this.originalImages = Array.isArray(response.data.original_images) ? response.data.original_images : [];
      } catch (error) {
        console.error('Error fetching results:', error);
        this.status = 'FAILED';
      }
    },
    copyToClipboard() {
      if (!this.translated_text) {
        return;
      }
      navigator.clipboard.writeText(this.translated_text).then(() => {
        alert('Copied to clipboard!');
      });
    },
    downloadTranslation() {
      if (!this.translated_text) {
        return;
      }
      const blob = new Blob([this.translated_text], { type: 'text/plain' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `translation-${this.task_id}.txt`;
      link.click();
      URL.revokeObjectURL(link.href);
    },
    async downloadPdf() {
      try {
        const response = await axios.get(`${import.meta.env.VITE_APP_BACKEND_API_URL}/api/result/${this.task_id}?format=pdf`, {
          responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `translation-${this.task_id}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error('Error downloading PDF:', error);
        alert('Failed to download PDF. Please try again.');
      }
    },
    resetState(preserveFile = false) {
      if (!preserveFile) {
        this.file = null;
      }
      this.task_id = null;
      this.status = null;
      this.translated_text = '';
      this.originalImages = [];
      this.uploadProgress = 0;
      this.isUploading = false;
      if (this.polling) {
        clearInterval(this.polling);
      }
      this.polling = null;
    },
  },
  beforeUnmount() {
    if (this.polling) {
      clearInterval(this.polling);
    }
  },
};
</script>

<style>
:root {
  --primary-color: #4CAF50; /* Green */
  --secondary-color: #3F51B5; /* Indigo */
  --accent-color: #FFC107; /* Amber */
  --background-color: #e8eaf6; /* Light Indigo */
  --card-background: #ffffff;
  --text-color: #212121;
  --light-text-color: #757575;
  --border-radius: 8px;
  --box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  --transition-speed: 0.3s ease;
}

body {
  font-family: 'Roboto', sans-serif; /* Using a common, clean font */
  background-color: var(--background-color);
  color: var(--text-color);
  margin: 0;
  padding: 0;
  line-height: 1.6;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  background-color: var(--secondary-color);
  color: white;
  padding: 2rem 1rem;
  text-align: center;
  box-shadow: var(--box-shadow);
}

.header h1 {
  margin: 0;
  font-size: 2.8rem;
}

.header p {
  margin-top: 0.5rem;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.8);
}

.main-content {
  flex-grow: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 2rem auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.upload-section {
  background-color: var(--card-background);
  padding: 2.5rem;
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}

.file-input-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.file-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px dashed var(--secondary-color);
  border-radius: var(--border-radius);
  color: var(--secondary-color);
  cursor: pointer;
  transition: var(--transition-speed);
  width: 100%;
  max-width: 400px;
  text-align: center;
  font-weight: 600;
  background-color: rgba(63, 81, 181, 0.05);
}

.file-label:hover {
  background-color: rgba(63, 81, 181, 0.1);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

#file-upload {
  display: none;
}

.translate-button {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: var(--transition-speed);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 220px;
}

.translate-button:hover {
  background-color: #43a047;
  transform: translateY(-1px);
}

.translate-button:disabled {
  background-color: #B0BEC5;
  cursor: not-allowed;
  transform: none;
}

.progress-container {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-track {
  flex: 1;
  height: 0.5rem;
  background-color: #e0e0e0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--secondary-color);
  border-radius: 999px;
  transition: width 0.2s ease;
}

.progress-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--light-text-color);
  min-width: 3rem;
  text-align: right;
}

.status-section {
  display: flex;
  justify-content: center;
}

.status-card {
  background-color: var(--card-background);
  padding: 1.5rem 2rem;
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  min-width: 320px;
  text-align: center;
  position: relative;
}

.status-card p {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.loader {
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  width: 36px;
  height: 36px;
  animation: spin 1s linear infinite;
  margin: 1rem auto 0;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.results-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 2rem;
}

.result-panel {
  background-color: var(--card-background);
  padding: 1.5rem;
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.result-panel h2 {
  color: var(--secondary-color);
  margin-top: 0;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
  margin-bottom: 0.5rem;
}

.image-gallery {
  flex-grow: 1;
  max-height: 500px;
  overflow-y: auto;
  padding-right: 5px;
}

.image-gallery img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--border-radius);
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.markdown-output {
  flex-grow: 1;
  min-height: 300px;
  border: 1px solid #e0e0e0;
  border-radius: var(--border-radius);
  padding: 1rem;
  font-size: 1rem;
  line-height: 1.8;
  overflow-y: auto;
  background-color: #fdfdfd;
}

.markdown-output h1, .markdown-output h2, .markdown-output h3, .markdown-output h4, .markdown-output h5, .markdown-output h6 {
  color: var(--secondary-color);
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.markdown-output h1 { font-size: 2em; }
.markdown-output h2 { font-size: 1.75em; }
.markdown-output h3 { font-size: 1.5em; }
.markdown-output h4 { font-size: 1.25em; }
.markdown-output h5 { font-size: 1em; }
.markdown-output h6 { font-size: 0.875em; }

.markdown-output p {
  margin-bottom: 1em;
}

.markdown-output a {
  color: var(--primary-color);
  text-decoration: none;
}

.markdown-output a:hover {
  text-decoration: underline;
}

.markdown-output strong, .markdown-output b {
  font-weight: bold;
}

.markdown-output em, .markdown-output i {
  font-style: italic;
}

.markdown-output ul, .markdown-output ol {
  margin-left: 1.5em;
  margin-bottom: 1em;
  padding-left: 0;
}

.markdown-output ul li, .markdown-output ol li {
  margin-bottom: 0.5em;
}

.markdown-output ul {
  list-style-type: disc;
}

.markdown-output ol {
  list-style-type: decimal;
}

.markdown-output pre {
  background-color: #eeeeee;
  padding: 0.8rem;
  border-radius: 4px;
  overflow-x: auto;
}

.markdown-output code {
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  background-color: #f0f0f0;
  padding: 0.2em 0.4em;
  border-radius: 3px;
}

.markdown-output pre code {
  background-color: transparent;
  padding: 0;
}

.markdown-output blockquote {
  border-left: 4px solid var(--accent-color);
  padding-left: 1em;
  margin-left: 0;
  color: var(--light-text-color);
}

.markdown-output table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1em;
}

.markdown-output th, .markdown-output td {
  border: 1px solid #ddd;
  padding: 0.8em;
  text-align: left;
}

.markdown-output th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  justify-content: flex-end;
}

.button-group button {
  background-color: var(--secondary-color);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: var(--transition-speed);
  font-size: 1rem;
}

.button-group button:hover {
  background-color: #303F9F;
  transform: translateY(-1px);
}

.error-section {
  background-color: #ffebee;
  color: #c62828;
  padding: 1.5rem;
  border-radius: var(--border-radius);
  text-align: center;
  font-weight: bold;
  box-shadow: var(--box-shadow);
}

</style>
