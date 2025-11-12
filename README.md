# IngestionFlow - PDF Document Processing & Embedding System

## 📋 Overview

The `IngestionFlow` class is a comprehensive document ingestion pipeline that processes PDF/DOCX documents, extracts text (including OCR for image-based pages), generates embeddings using Google's Vertex AI, and stores them in BigQuery Vector Store for semantic search capabilities.

## 🎯 Key Features

- **PDF/DOCX Text Extraction**: Extracts text, tables (markdown format), and images from PDFs/DOCX
- **Intelligent OCR Processing**: Automatically detects pages with insufficient text and applies OCR
- **Image-to-Text Conversion**: Uses Google's Gemini Vision model for image content extraction
- **Concurrent Processing**: Multi-threaded image processing for improved performance
- **Adaptive Batch Processing**: Automatically adjusts batch sizes based on token limits
- **Retry Mechanism**: Smart retry logic with exponential backoff for API overload scenarios
- **Vector Embedding Storage**: Stores embeddings in BigQuery for semantic search
- **Document Versioning**: Supports re-embedding with automatic deactivation of old versions

---

## 🏗️ Architecture Flow

```
PDF/DOCX Document (GCS)
    ↓
Download to Local Temp
    ↓
Text Extraction (PyMuPDF)
    ↓
[Decision: Page has text?]
    ↓ NO                           ↓ YES
OCR Processing              Direct Text Use
(Gemini Vision)
    ↓                               ↓
Text Extracted ←────────────────────┘
    ↓
Batch Documents
    ↓
Generate Embeddings (Vertex AI)
    ↓
Store in BigQuery Vector Store
    ↓
Update Metadata
    ↓
Complete
```

---

## 🔧 Class Structure

### Constructor

```python
IngestionFlow(company_id, doc_id, service_credentials, active_flag="Y")
```

**Parameters:**
- `company_id`: Company identifier for multi-tenant systems
- `doc_id`: Unique document identifier
- `service_credentials`: GCP service account JSON key (as dictionary)
- `active_flag`: Document status flag ("Y" for active, "N" for inactive)

---

## 📚 Core Methods

### 1. `pdf_to_text_image_information_extraction()`

**Purpose**: Main extraction method that processes PDF and extracts text/images

**Process:**
1. Downloads PDF from Google Cloud Storage
2. Uses PyMuPDFLoader to extract text, tables, and images
3. Determines which pages need OCR (based on character count threshold)
4. Processes pages concurrently using ThreadPoolExecutor
5. Combines OCR results with directly extracted text
6. Returns list of Document objects

**Key Features:**
- **Retry Logic**: Handles API overload with exponential backoff
- **Dual Path Processing**: 
  - Pages with sufficient text → Direct extraction
  - Pages with insufficient text → OCR via Gemini Vision
- **Image Saving**: Saves page images to `image_test2/` for debugging

**Environment Variables:**
- `page_to_image_convert`: Enable/disable OCR processing ("true"/"false")
- `pdf_page_char_len`: Minimum character count threshold (default: 0)

---

### 2. `embed_using_service_account_dict()`

**Purpose**: Creates Vertex AI embedding client

**Returns**: `VertexAIEmbeddings` object configured with service account credentials

---

### 3. `bqvectore_store()`

**Purpose**: Initializes BigQuery Vector Store client

**Parameters:**
- `dataset_id`: BigQuery dataset name
- `table_id`: BigQuery table name
- `REGION`: GCP region (e.g., "us-central1")
- `embedding`: Embedding model instance

**Configuration:**
- Distance metric: COSINE similarity
- Document ID field: `unique_id`

---

### 4. `deactivate_old_embeddings()`

**Purpose**: Sets `active_flag = 'N'` for existing embeddings of the same document

**Use Case**: Re-embedding scenarios where old versions should be deactivated

---

### 5. `updated_doc_data()`

**Purpose**: Updates metadata fields (`company_id`, `doc_id`, `active_flag`) in BigQuery

---

### 6. `batch_pages()`

**Purpose**: Intelligent batching with dual constraints

**Constraints:**
- Maximum pages per batch: 20 (configurable)
- Maximum tokens per batch: 19,000

**Token Estimation**: ~4 characters = 1 token (with 2048 token cap per input)

---

### 7. `_insert_batch_with_adaptive_retry()`

**Purpose**: Inserts batches with automatic page reduction on token errors

**Adaptive Strategy:**
1. Start with initial batch size
2. If token limit error occurs → Reduce pages by 1
3. Retry up to `max_retries` times (default: 10)
4. If still failing → Fall back to page-by-page insertion

**Error Detection**: Identifies token limit errors by keywords:
- "token", "limit", "400", "exceed", "supports up to", "input token count"

---

### 8. `final_ingestion()` ⭐ **Main Entry Point**

**Purpose**: Orchestrates the entire ingestion pipeline

**Parameters:**
```python
final_ingestion(
    google_model_api,      # Gemini API key
    model,                 # Model name (e.g., "gemini-1.5-flash")
    gs_location,           # GCS path: gs://bucket/path/file.pdf
    embedding_model,       # Vertex AI embedding model
    dataset_id,            # BigQuery dataset
    table_id,              # BigQuery table
    REGION,                # GCP region
    is_reembed=False,      # Re-embedding flag
    max_pages_per_batch=20,      # Initial batch size
    max_retry_attempts=10        # Max adaptive retries
)
```

**Execution Steps:**

1. **Deactivate Old Embeddings** (if `is_reembed=True`)
2. **Extract Documents** from PDF
3. **Create Batches** (token-aware)
4. **Generate Embeddings** (Vertex AI)
5. **Insert into BigQuery** (with adaptive retry)
6. **Update Metadata**
7. **Return Summary**

**Output:**
- Total pages processed
- Successfully inserted count
- Failed pages count
- Success rate percentage
- Timing statistics

---

## 🚀 Usage Example

### Step-by-Step Implementation

#### Step 1: Prepare Environment Variables

```python
import os

# Set up API keys and model names
os.environ["gemini_api"] = "YOUR_GEMINI_API_KEY"
os.environ["model_lite"] = "gemini-1.5-flash"
os.environ["embedding_model"] = "text-embedding-004"
os.environ["pvt_data_emb_table"] = "document_embeddings"

# Optional: OCR configuration
os.environ["page_to_image_convert"] = "true"
os.environ["pdf_page_char_len"] = "50"  # Minimum characters to skip OCR
```

#### Step 2: Prepare GCP Credentials

```python
# Load service account JSON key
import json

with open('path/to/service-account-key.json', 'r') as f:
    service_credentials = json.load(f)

# OR provide directly as dictionary
service_credentials = {
    "type": "service_account",
    "project_id": "your-project-id",
    "private_key_id": "...",
    "private_key": "...",
    "client_email": "...",
    # ... other fields
}
```

#### Step 3: Define Document Parameters

```python
# Document identification
company_id = "company_abc_123"
doc_id = "invoice_2024_001"

# GCS location of PDF
gs_location = "gs://my-bucket/documents/invoice.pdf"

# BigQuery configuration
dataset_id = "knowledge_base"
table_id = os.environ["pvt_data_emb_table"]  # "document_embeddings"
REGION = "us-central1"
```

#### Step 4: Initialize and Run Ingestion

```python
from ingestion_flow import IngestionFlow

# Create ingestion object
obj = IngestionFlow(
    company_id=company_id,
    doc_id=doc_id,
    service_credentials=service_credentials,
    active_flag="Y"
)

# Run ingestion pipeline
result = obj.final_ingestion(
    google_model_api=os.environ["gemini_api"],
    model=os.environ["model_lite"],
    gs_location=gs_location,
    embedding_model=os.environ["embedding_model"],
    dataset_id=dataset_id,
    table_id=table_id,
    REGION=REGION,
    is_reembed=False  # Set to True if re-processing existing document
)

print(result)
```

#### Example Output

```
Downloaded documents/invoice.pdf to tmp/invoice.pdf
Processing 15 pages with OCR using 2 workers

======================================================================
Processing 23 pages for ingestion
Initial batch size: 20 pages/batch
Auto-retry enabled: Up to 10 attempts with adaptive page reduction
======================================================================

Created 2 initial batches

--- Batch 1/2 (20 pages) ---
  → Attempt 1: Trying 20 pages (limit: 20 pages/batch)
  ✓ Successfully inserted 20 pages
Batch 1 complete: 20/20 pages inserted
Running total: 20/23 pages

--- Batch 2/2 (3 pages) ---
  → Attempt 1: Trying 3 pages (limit: 20 pages/batch)
  ✓ Successfully inserted 3 pages
Batch 2 complete: 3/3 pages inserted
Running total: 23/23 pages

======================================================================
INGESTION SUMMARY
======================================================================
Total pages processed: 23
Successfully inserted: 23
Failed pages: 0
Success rate: 100.0%
Embedding and insertion time: 45.32 seconds
======================================================================

Metadata update result: Successfully updated data.

Total ingestion time: 78.51 seconds

Ingestion completed successfully. Inserted 23/23 pages.
```

---

## 🔄 Re-embedding Workflow

When updating an existing document:

```python
# Set is_reembed=True to deactivate old versions
result = obj.final_ingestion(
    # ... same parameters ...
    is_reembed=True  # ← This deactivates old embeddings first
)
```

**What happens:**
1. Old embeddings with same `doc_id` are set to `active_flag='N'`
2. New embeddings are inserted with `active_flag='Y'`
3. Metadata is updated with new version

---

## ⚙️ Configuration Guide

### OCR Processing

Control OCR behavior with environment variables:

```python
# Enable OCR for pages with low text content
os.environ["page_to_image_convert"] = "true"

# Set character threshold (pages below this trigger OCR)
os.environ["pdf_page_char_len"] = "100"
```

### Batch Size Tuning

Adjust for your document characteristics:

```python
result = obj.final_ingestion(
    # ...
    max_pages_per_batch=15,      # Reduce if hitting token limits
    max_retry_attempts=15        # Increase for more retries
)
```

**Recommendations:**
- **Dense text documents**: Reduce `max_pages_per_batch` to 10-15
- **Image-heavy documents**: Can use 20-25
- **Mixed content**: Start with default 20

### Threading

OCR processing uses concurrent threads:

```python
max_workers = min(2, len(pages_needing_ocr))
```

- Default: Maximum 2 concurrent workers
- Prevents API rate limiting
- Modify in source code if needed

---

## 🛡️ Error Handling

### Retry Mechanisms

1. **API Overload (503 errors)**
   - Exponential backoff: 2s, 4s, 8s
   - Max 3 retries

2. **Token Limit Errors**
   - Automatic page reduction
   - Falls back to single-page insertion
   - Max 10 adaptive attempts

3. **Image Processing Errors**
   - Graceful degradation
   - Placeholder text: `[Error extracting text from page N]`
   - Continues with remaining pages

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| Model overloaded (503) | API rate limit | Automatic retry with backoff |
| Token limit exceeded | Page too large | Automatic batch reduction |
| Permission denied | Invalid credentials | Check service account permissions |
| File not found (GCS) | Wrong path | Verify `gs_location` |
| Empty page_content | Extraction failed | Check PDF format, enable OCR |

---

## 📊 Performance Optimization

### Speed Improvements

1. **Increase concurrent workers** (if API quota allows):
   ```python
   max_workers = min(4, len(pages_needing_ocr))  # Change from 2 to 4
   ```

2. **Batch size tuning**:
   - Larger batches = Fewer API calls
   - Smaller batches = Better error recovery

3. **Skip OCR for text-heavy PDFs**:
   ```python
   os.environ["page_to_image_convert"] = "false"
   ```

### Memory Considerations

- Temp files stored in `tmp/` directory
- Images cleaned up after processing
- Consider disk space for large PDFs

---

## 🔐 Required GCP Permissions

Service account must have:

- **Cloud Storage**: `storage.objects.get` (read PDFs)
- **Vertex AI**: `aiplatform.endpoints.predict` (embeddings)
- **BigQuery**: 
  - `bigquery.tables.updateData` (insert embeddings)
  - `bigquery.tables.update` (update metadata)
  - `bigquery.jobs.create` (run queries)

---

## 📝 BigQuery Schema

Expected table structure:

```sql
CREATE TABLE `project.dataset.table` (
  unique_id STRING,
  content STRING,
  embedding ARRAY<FLOAT64>,
  metadata JSON,
  company_id STRING,
  doc_id STRING,
  active_flag STRING,
  -- Additional metadata fields
)
```

---

## 🐛 Debugging

### Enable Debug Images

Images are automatically saved to `image_test2/` directory:

```python
test_image_path = os.path.join('image_test2', f"test_page_{i + 1}.png")
```

Check these images if OCR results are unexpected.

### Verbose Logging

The code includes extensive print statements for tracking:
- Download progress
- OCR page identification
- Batch processing status
- Insertion success/failure
- Timing statistics

---

## 📦 Dependencies

Required libraries:

```python
# Core
import fitz  # PyMuPDF
from pathlib import Path
import asyncio
import time
import os
import json

# Google Cloud
from google.cloud import storage
from google.oauth2 import service_account
import google.oauth2.service_account

# LangChain
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.parsers import LLMImageBlobParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_google_community import BigQueryVectorStore
from langchain.schema import Document

# Utilities
from concurrent.futures import ThreadPoolExecutor, as_completed

# Custom modules
from image_summary import extract_text_from_image
from bq_utill import BigQueryUtils
```

Install with:
```bash
pip install pymupdf langchain langchain-community langchain-google-genai \
            langchain-google-vertexai google-cloud-storage google-cloud-bigquery
```

---

## 🎓 Best Practices

1. **Always use unique `doc_id`**: Prevents accidental overwrites
2. **Enable re-embed for updates**: Use `is_reembed=True` when reprocessing
3. **Monitor batch sizes**: Check logs for adaptive retry patterns
4. **Test with small PDFs first**: Verify configuration before large batches
5. **Use descriptive company_id**: Enables multi-tenant filtering
6. **Clean up temp files**: The code handles this, but verify `tmp/` directory
7. **Set appropriate thresholds**: Tune `pdf_page_char_len` based on content

---

## 🔮 Future Enhancements

Potential improvements:
- Support for DOCX, images, other formats
- Parallel document processing
- Webhook notifications on completion
- Metadata extraction (author, date, etc.)
- Custom chunking strategies
- Vector search interface

---

## 📞 Support

For issues or questions:
- Check logs for detailed error messages
- Verify GCP permissions and quotas
- Test API keys separately
- Review BigQuery table schema
- Ensure sufficient disk space for temp files

---

## ✅ Summary Checklist

Before running ingestion:

- [ ] GCP service account JSON key ready
- [ ] Gemini API key configured
- [ ] PDF exists in GCS at correct path
- [ ] BigQuery dataset and table exist
- [ ] Service account has required permissions
- [ ] Environment variables set
- [ ] Unique `doc_id` chosen
- [ ] `company_id` assigned
- [ ] Region matches BigQuery dataset location
- [ ] OCR settings configured (if needed)

---

