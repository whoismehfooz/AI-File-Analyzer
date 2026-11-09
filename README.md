#                                                   📄 AI File Analyzer

> A production-minded FastAPI backend for uploading, validating, and extracting structured content from multiple document formats.

<p align="center">
  📤 Document Upload • 🛡️ File Validation • 📑 Text Extraction • 📊 Structured Metadata • 🧪 142 Passing Tests
</p>

![Python](https://img.shields.io/badge/Python-Backend-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![PyMuPDF](https://img.shields.io/badge/PDF-PyMuPDF-red)
![Tests](https://img.shields.io/badge/Tests-142%20passing-success?logo=pytest&logoColor=white)
![Pydantic](https://img.shields.io/badge/Validation-Pydantic-E92063?logo=pydantic&logoColor=white)

---

## 1. 📌 Introduction

**AI File Analyzer** is a backend application built with Python and FastAPI that accepts document uploads, validates them, and extracts their readable content into a structured format.

The application supports six document formats: TXT, PDF, DOCX, CSV, XLS, and XLSX.

Each uploaded document passes through a dedicated validation service before being processed by the document extraction service. The extracted result includes normalized content, document metadata, and individual content sections.

The project focuses on building a reliable document-processing foundation with structured responses, sensible resource limits, and predictable error handling.

## 2. ⚙️ Core Features & Technologies

### Core Features

- 📤 **Document Upload:** Upload documents through a REST API.
- 🛡️ **File Validation:** Validate filenames, extensions, empty files, and upload sizes.
- 📑 **Multi-format Extraction:** Extract content from TXT, PDF, DOCX, CSV, XLS, and XLSX files.
- 📊 **Structured Output:** Preserve useful information such as PDF page numbers, DOCX paragraph and table details, CSV rows, and Excel sheet metadata.
- 🔒 **Resource Limits:** Apply configurable limits to document extraction and processing.
- ⚠️ **Error Handling:** Handle invalid documents, malformed files, and extraction failures through predictable API responses.
- 🧪 **Automated Testing:** Unit tests and upload endpoint integration tests.

### Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Pydantic | Data validation and response schemas |
| Pydantic Settings | Environment-based configuration |
| PyMuPDF | PDF text extraction |
| python-docx | DOCX document extraction |
| Pandas | Tabular data processing |
| openpyxl | XLSX workbook handling |
| xlrd | XLS workbook handling |
| Pytest | Automated testing |

## 3. 🏗️ Project Architecture

```text
backend/
│
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── document.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── exceptions/
│   │   └── handlers.py
│   │
│   ├── schemas/
│   │   ├── document.py
│   │   └── extracted_document.py
│   │
│   ├── services/
│   │   ├── document_validation_service.py
│   │   └── document_extraction_service.py
│   │
│   └── main.py
│
├── tests/
│   ├── unit/
│   └── api/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### Main Processing Flow

```text
        Client
          │
          ▼
    Upload Endpoint
          │
          ▼
  Document Validation
       Service
          │
          ▼
    Read File Bytes
          │
          ▼
  Document Extraction
       Service
          │
          ▼
   Extracted Document
          │
          ▼
    Structured JSON
       Response
```

## 4. 🚀 Getting Started

Follow these steps to clone, configure, run, and test the application locally.

### Step 1. Clone the Repository

```bash
git clone <repository-url>
```

Navigate into the backend directory:

```bash
cd <repository-folder>/backend
```

### Step 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it:

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows:**

```powershell
.venv\Scripts\activate
```

### Step 3. Install Dependencies

```bash
python -m pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

### Step 4. Configure Environment Variables

Create your local environment file:

```bash
cp .env.example .env
```

Open `.env` and configure the application settings as required.

### Step 5. Start the Application

From the backend directory, run:

```bash
uvicorn app.main:app --reload
```

The application will start locally at:

```text
http://127.0.0.1:8000
```

### Step 6. Open Swagger Documentation

Navigate to:

```text
http://127.0.0.1:8000/docs
```

Swagger UI provides an interactive interface for testing the available API endpoints.

### Step 7. Upload a Document

1. Open the `/documents/upload` endpoint.
2. Click **Try it out**.
3. Select a supported document.
4. Click **Execute**.
5. Inspect the response containing the extracted content, sections, and metadata.

You can also check the application health using:

```text
http://127.0.0.1:8000/health
```

### Step 8. Run the Tests

From the backend directory:

```bash
pytest -q
```

The current test suite contains **142 passing tests**.

## 5. 💡 Final Note

AI File Analyzer is built around a simple principle: reliable AI applications begin with reliable data processing.

**Clean inputs. Structured extraction. Predictable outputs.**
