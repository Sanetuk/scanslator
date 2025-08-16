<template>
  <div id="app">
    <header class="header">
      <h1>Lao-Korean Translator</h1>
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
          <span v-else>Processing...</span>
        </button>
      </div>

      <div v-if="task_id" class="status-section">
        <div :class="['status-card', status.toLowerCase()]">
          <p><strong>Status:</strong> {{ status }}</p>
          <div v-if="isLoading" class="loader"></div>
        </div>
      </div>

      <div v-if="status === 'COMPLETE'" class="results-section">
        <div class="result-panel">
          <h2>Korean Translation</h2>
          <div class="markdown-output" v-html="renderedTranslatedText"></div>
          <div class="button-group">
            <button @click="copyToClipboard">Copy Text</button>
            <button @click="downloadTranslation">Download .txt</button>
            <button @click="downloadPdf">Download .pdf</button>
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
      translated_text: `# 이것은 **굵은** 텍스트입니다. 그리고 *기울임꼴* 입니다.

# 제목입니다.

- 목록 1
- 목록 2`,
      polling: null,
    };

  },
  computed: {
    isLoading() {
      return this.status === 'PENDING' || this.status === 'PROCESSING';
    },
    renderedTranslatedText() {
      return marked(this.translated_text);
    }
  },
  methods: {
    handleFileUpload(event) {
      this.file = event.target.files[0];
      this.resetState();
    },
    async submitFile() {
      const formData = new FormData();
      formData.append('file', this.file);

      try {
        const response = await axios.post(`${import.meta.env.VITE_APP_BACKEND_API_URL}/upload/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        this.task_id = response.data.task_id;
        this.status = 'PENDING';
        this.pollStatus();
      } catch (error) {
        console.error('Error uploading file:', error);
        this.status = 'FAILED';
      }
    },
    pollStatus() {
      this.polling = setInterval(async () => {
        try {
          const response = await axios.get(`${import.meta.env.VITE_APP_BACKEND_API_URL}/api/status/${this.task_id}`);
          this.status = response.data.status;
          if (this.status === 'COMPLETE') {
            clearInterval(this.polling);
            this.fetchResults();
          } else if (this.status === 'FAILED') {
            clearInterval(this.polling);
          }
        } catch (error) {
          console.error('Error polling status:', error);
          this.status = 'FAILED';
          clearInterval(this.polling);
        }
      }, 2000);
    },
    async fetchResults() {
      console.log('Fetching translation results...');
      try {
        const response = await axios.get(`${import.meta.env.VITE_APP_BACKEND_API_URL}/api/result/${this.task_id}`);
        console.log('Received results response:', response.data);
        this.translated_text = response.data.translated_text;
        console.log('translated_text after assignment (first 100 chars):', this.translated_text.substring(0, 100));
      } catch (error) {
        console.error('Error fetching results:', error);
        this.status = 'FAILED';
      }
    },
    copyToClipboard() {
      navigator.clipboard.writeText(this.translated_text).then(() => {
        alert('Copied to clipboard!');
      });
    },
    downloadTranslation() {
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
          responseType: 'blob' // Important: responseType must be 'blob' for binary data
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
    resetState() {
        this.task_id = null;
        this.status = null;
        this.translated_text = '';
        if (this.polling) {
            clearInterval(this.polling);
        }
    }
  },
  beforeUnmount() {
    clearInterval(this.polling);
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
  flex-direction: column;
  align-items: center;
}

input[type="file"] {
  display: none;
}

.file-label {
  border: 2px dashed var(--primary-color);
  border-radius: var(--border-radius);
  padding: 1.5rem 2rem;
  cursor: pointer;
  transition: var(--transition-speed);
  width: 80%;
  text-align: center;
  font-size: 1.1rem;
  color: var(--light-text-color);
}

.file-label:hover {
  background-color: #e8f5e9;
  border-color: var(--secondary-color);
}

.translate-button {
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 1rem 2.5rem;
  border-radius: var(--border-radius);
  font-size: 1.2rem;
  cursor: pointer;
  transition: var(--transition-speed);
  box-shadow: var(--box-shadow);
}

.translate-button:disabled {
  background-color: #a5d6a7;
  cursor: not-allowed;
  box-shadow: none;
}

.translate-button:hover:not(:disabled) {
  background-color: #43A047;
  transform: translateY(-2px);
}

.status-section {
  margin-top: 1rem;
}

.status-card {
  background-color: var(--card-background);
  padding: 1.5rem;
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  display: flex;
  align-items: center;
  gap: 1rem;
  border-left: 5px solid var(--primary-color);
}

.status-card.failed {
  border-left-color: #e57373; /* Red for failed */
}

.loader {
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.results-section {
  display: grid;
  grid-template-columns: 1fr; /* Always single column */
  gap: 2rem;
}



.result-panel {
  background-color: var(--card-background);
  padding: 1.5rem;
  border-radius: var(--border-radius);
  box-shadow: var(--box-shadow);
  display: flex;
  flex-direction: column;
}

.result-panel h2 {
  color: var(--secondary-color);
  margin-top: 0;
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
}

.image-gallery {
  flex-grow: 1;
  max-height: 500px; /* Limit height for scrollability */
  overflow-y: auto;
  padding-right: 5px; /* Space for scrollbar */
}

.image-gallery img {
  width: 100%;
  height: auto;
  display: block; /* Prevents extra space below images */
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
  font-weight: bold; /* Ensure headings are bold */
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
  justify-content: flex-end; /* Align buttons to the right */
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
