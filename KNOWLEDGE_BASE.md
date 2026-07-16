# 🧠 Multi-Tenant Knowledge Base Engine (WhatsApp Sales AI)

This system serves as the core "memory spine" for a fleet of WhatsApp AI Sales Assistants. It allows independent business owners to upload their raw unstructured documents (product catalogs, pricing sheets, return policies, FAQs) and transforms them into secure, verified text chunks. 

When a customer messages a store on WhatsApp, our system instantly retrieves the exact factual context needed to build a hallucination-free, role-isolated answer.

---

## 🏗️ Core System Components

The project layout separates static business documentation assets from the active async processing app:

📂 **`knowledge_base/`** — Static asset directory sandboxed per business tenant
* 📁 `raw_uploads/` : Houses the untouched original documents (`.pdf`, `.docx`, `.xlsx`) uploaded by store owners, organized strictly inside sub-folders by their distinct Business ID (e.g., `business_sarah/`).
* 📁 `clean_wiki/` : Holds the sanitized, standardized Markdown (`.md`) text extracted by our parsing engines, mirrored cleanly using the same sandboxed Business ID structure.
* 📄 `system_prompts/aisha_voice.txt` : The global behavioral rulebook for the AI assistants (defining tone, formatting restrictions, closing rules, and strict instructions to never make up prices).

📂 **`backend/app/knowledge_base/`** — The active processing engine code
* 📄 `tenancy.py` : Enforces absolute directory isolation, ensuring any file upload or read operation is mathematically trapped inside that specific business owner's unique folder path.
* 📄 `security.py` : Sanitizes text inputs, screens uploads, and strips malicious strings or prompt injection attacks out of untrusted source documents.
* 📄 `chunking.py` : The structural engine that converts files to Markdown and slices long files into compact, semantic paragraphs (chunks) based on header formatting.
* 📄 `models.py` : Maps the database schema for the PostgreSQL `wiki_chunks` table, configuring Full-Text Search vectors.
* 📄 `schemas.py` : Governs safe data structures and Pydantic validation shapes to expose only explicit, allow-listed context blocks to the model.
* 📄 `manager.py` : The central coordinator that orchestrates the entire workflow: handles document ingestion, pulls relevant database blocks, and constructs the final prompt payload.

---

.
├── knowledge_base/
│   ├── clean_wiki/                     # Cleaned Markdown policies, one folder per business (by user ID)
│   ├── raw_uploads/                    # Original uploaded files, one folder per business (by user ID)
│   └── system_prompts/
│       └── aisha_voice.txt             # AISHA's shared rulebook — tone, language, safety rules
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py                 # Async SQLAlchemy engine + session setup
│   │   ├── models.py                   # Core app tables: User, Product, Customer, conversion,..
│   │   │
│   │   └── knowledge_base/
│   │       ├── __init__.py
│   │       ├── security.py             # Sanitizes text, scans uploads, fences untrusted content
│   │       ├── chunking.py             # Splits Markdown into sections, normalizes customer queries
│   │       ├── tenancy.py              # Confines every file path to its own business — no crossover
│   │       ├── models.py               # wiki_chunks table (Postgres full-text search, 'simple' config)
│   │       ├── schemas.py              # Safe, allow-listed data shapes used when building a reply
│   │       └── manager.py              # Ties it together: ingests documents, assembles the final prompt
│   │
│   ├── alembic/versions/
│   │   └── xxxx_add_wiki_chunks.py     # Creates wiki_chunks + turns on Row-Level Security
│   │
│   ├── scripts/
│   │   ├── verify_ingestion.py         # Manual test: upload a sample policy, confirm it's stored
│   │   └── verify_prompt_payload.py    # Manual test: print the exact payload AISHA would send
│   │
│   └── tests/
│       ├── conftest.py                 # Test fixtures — seeds two businesses' worth of sample data
│       └── test_rls_isolation.py       # Automated check one business can't read another's rows
│
└── README.md                           # Plain-English explanation of the whole knowledge base

## How the process takes place


[ Raw File Uploaded ] raw_uploads/business_id/
         │
         ▼
[ Step 1: File Type Check ] ➔ Determines path based on format (.txt, .docx, .pdf,markdown)
         │
         ▼
[ Step 2: The Parser / OCR Engine ] 
         ├── Layout Parser ➔ Extracts structural text from digital documents
         └── Optical Character Recognition Engine    ➔ Scans pixel images to detect embedded text characters
         │
         ▼
[ Step 3: Markdown Restructuring ] ➔ Formats headers (#), bullets (-), and tables
         │
         ▼
[ Safe Markdown File Saved ] ➔ Saved securely into clean_wiki/business_id/
         |  
         ▼
[ Step 4  Slicing: Semantic Chunking ] The moment that file successfully writes to the disk,     manager.py instantly calls the chunking module
         │
         ▼
Saved to PostgreSQL Table (wiki_chunks) via Async SQLAlchemy Engine



[ 1. Network Data Arrives via HTTP/Webhook ] 
                    │
                    ▼
[ 2. GATE 1: Pydantic Validation (schemas.py) ] ➔ (Validates UUID shapes & fields in RAM)
                    │
                    ▼
[ 3. LAYER 1: Sandboxed Directory Isolation ]   ➔ (tenancy.py locks down file paths on disk)
                    │
                    ▼
[ 4. SYSTEM FILE TYPE CHECKER ]                 ➔ (Validates extensions: .pdf vs .png)
                    ├─── If Image Canvas ➔ Route to OCR Engine (Pixel Analysis)
                    └─── If Text Stream  ➔ Route to Layout Parser (XML Reading)
                    │
                    ▼
[ 5. RAW TEXT STRIPPED FROM SOURCE ] 
                    │
                    ▼
[ 6. LAYER 2: Input Content Protection ]        ➔ (security.py neutralizes prompt injections)
                    │
                    ▼
[ 7. STANDARD MARKDOWN COMPILATION ]            ➔ (Saved permanently inside clean_wiki/)
                    │
                    ▼
[ 8. CHUNKING ENGINE Lifecycles ]               ➔ (chunking.py slices .md text by headers #)
                    │
                    ▼
[ 9. STORAGE TIER: Database Relational Models ] ➔ (models.py maps records to the database layout)
                    │
                    ▼
[ 10. POSTGRES DRIVE MEMORY BLOCK ]             ➔ (Flushed cleanly to the wiki_chunks table)



### 📸 1. The OCR Engine (Designed for Pixel Matrices)
* **Target Artifacts:** Scanned documents, receipts, screenshots, and image arrays (`.png`, `.jpg`, `.jpeg`, flat flattening `.pdf`).
* **Operational Mechanism:** Images carry zero programmatic text metadata; they are simply configurations of individual pixel color values. The **Optical Character Recognition (OCR)** engine maps these raster grids, executing shape-analysis algorithms to calculate character probabilities. It interprets dark pixel clusters, translating physical shapes into standard text strings (e.g., mapping visual pixel loops into characters like `P-R-I-C-E`).

### 📄 2. The Layout Parser (Designed for Programmatic Code Streams)
* **Target Artifacts:** Native digital text files (`.docx`, `.xlsx`, editable `.pdf`, `.txt`).
* **Operational Mechanism:** Digital files do not contain pixel drawings of text; they store actual strings inside compressed underlying application architectures (like XML schemas inside Word files). The **Layout Parser** opens the internal directory of the file stream, bypasses design tags, and programmatically copies out the strings directly from the source layer. 

---


### Step 1: Secure Ingestion & Guardrails
When a file is uploaded, `tenancy.py` confines the destination to the proper business directory while `security.py` runs validation sweeps.

### Step 2: Extraction & OCR Parsing
If the document is a digital document (`.docx`, native `.pdf`), our layout parser extracts strings and structure directly out of the XML text layer. If the document is a image scan or a flat image, an **OCR (Optical Character Recognition)** engine reads the file pixel-by-pixel, grouping character clusters to extract raw hidden text.

### Step 3: Markdown Compilation
The raw unformatted string output from the parsing/OCR engine is passed through regex patterns and text heuristics that map font sizes and indentations into pure **Markdown (`.md`)**. This file is written directly into `clean_wiki/`.

### Step 4: Semantic Chunking & Storage
`chunking.py` reads the markdown file and cuts it into sequential paragraphs (chunks). It saves these rows to PostgreSQL via `database.py`. An Alembic migration script turns on database-level **Row-Level Security (RLS)**, making it impossible for one business to query another business's text rows.

---

## 📊 Why Use Markdown for AI Systems?

Markdown is the industry-standard choice for Retrieval-Augmented Generation (RAG) architectures for four primary reasons:
1. **Retains Structural Meaning without Document Bloat:** Large Language Models (LLMs) cannot understand messy PDF or Word styling code. Markdown strips away all design bloat but uses lightweight text symbols (`#` for headers, `-` for lists) to tell the AI exactly how information is grouped.
2. **Enables Smart Semantic Chunking:** Normal text splitters cut paragraphs blindly based on character limits, which can slice a pricing table or a sentences directly in half. By using Markdown headers, our `chunking.py` engine cuts text at logical topic changes.
3. **Preserves Data Relationship Context:** Tables inside Markdown are formatted cleanly using simple pipelines (`|`). When the database passes this block to the AI assistant, the LLM reads the neat matrix easily, allowing it to give pinpoint accurate pricing responses.
4. **Lightweight and Inexpensively Parsable:** Markdown files are simple plain text. They consume minimal disk storage space, enable sub-millisecond database text-query speeds, and do not cause database bloat.

---

## 💬 Live WhatsApp Execution Loop

When a customer sends a message to an AI assistant over WhatsApp, our runtime engine processes the request in milliseconds:

1. **Tenant Identification:** The webhook reads the target phone number to isolate the incoming request to a specific `business_id`.
2. **Full-Text Database Search:** The application coordinates an asynchronous search across the `wiki_chunks` PostgreSQL table. Because of **Row-Level Security (RLS)**, the database isolates search parameters to matching rows belonging *only* to that specific store ID.
3. **Prompt Construction:** `manager.py` combines the global assistant voice (`aisha_voice.txt`), the fetched matching Markdown fact chunks, and the customer's text question into a safe context-gated payload.
4. **Flawless Output Generation:** The model reads the structured prompt block and streams a factually accurate, beautifully formatted answer straight back to the user on WhatsApp.


 ## The Parallel Pipeline: Text vs. Images
 When a business user uploads a document that contains both text and images (like a PDF with charts or a Word document with screenshots), the system splits them into two distinct tracks:

                      ┌──► [ Text Track ]  ──► Markdown Chunks ──► PostgreSQL (wiki_chunks)
                      │
[ Raw Uploaded PDF ] ─┤
                      │
                      └──► [ Image Track ] ──► Extracted Binaries ──► Object Storage (S3 / Cloud)

##  When the document is a markdown

- So, while a PDF goes through a massive Extraction + Parsing phase, your clean Markdown file just goes through a light Sanitization phase.

[ Messy PDF ] ──────► [ Parser / OCR ] ──┐
                                         ▼
[ Messy Markdown ] ────────────────► [ Sanitizer / Cleaner ] ──► [ Optimized AI Context ]
                                    (Fixes spaces, trims junk)



 ## Why do we keep the master file in clean_wiki/ if it's already in the database?

### Keeping the full Markdown file inside clean_wiki/ permanently is a vital software engineering design choice for three reasons:

- **The Ultimate Audit Trail**:** If the AI gives a weird answer, you don't have to read hundreds of scrambled database rows to find the problem. You can open clean_wiki/business_sarah/catalog.md in VS Code and read it in plain English to see exactly what the store owner typed.

- **Easy Deletions & Re-Indexing**: If Sarah updates her price list and uploads a brand-new file, your code runs a fast clean-up: it deletes all old database rows matching business_sarah, deletes the old markdown file, saves the new markdown file, and triggers chunking again. It is incredibly clean

- **Emergency Backup**: If your PostgreSQL database ever crashes or gets corrupted, your system can restore its entire search memory in seconds by simply looping through the files in clean_wiki/ and re-running the chunking trigger!


## 🛡️ Multi-Tenant Architecture & Data Isolation

This system is engineered as a highly scalable **Shared-Database, Isolated-Schema SaaS (Software as a Service) platform**. Multiple independent business owners share the exact same hardware infrastructure, core application files, and database tables, yet their private data is completely invisible to one another. 

Data privacy boundaries are strictly enforced across three distinct structural layers:

### 1. Database Tier: Kernel-Level Row-Level Security (RLS)
* **Enforcement Point:** `backend/alembic/versions/xxxx_add_wiki_chunks.py`
* **Mechanism:** Every single paragraph slice across all businesses is stored in the **exact same table** named `wiki_chunks`. However, every single row is strictly tagged with a unique `business_id` UUID column.
* **Security Guardrail:** Rather than relying on developers to manually type filters into the Python code, we execute raw SQL to activate **PostgreSQL Row-Level Security (RLS)**:
  ```sql
  ALTER TABLE wiki_chunks ENABLE ROW LEVEL SECURITY;
  CREATE POLICY tenant_isolation_policy ON wiki_chunks 
  USING (business_id = current_setting('app.current_business_id'));
  ```
  PostgreSQL intercepts every query at the storage engine level. If a bug or human error happens in the application code, the database kernel itself physically filters the rows, blinding the system from reading data belonging to any other store ID.

### 2. Storage Tier: Path Sandboxing & Directory Isolation
* **Enforcement Point:** `backend/app/knowledge_base/tenancy.py`
* **Mechanism:** Documents inside `raw_uploads/` and `clean_wiki/` are never dumped together into a shared directory. `tenancy.py` programmatically intercepts all file operations and wraps them inside an explicit, sandboxed path function:
  ```python
  def get_secure_upload_path(business_id: str, filename: str) -> str:
      safe_filename = secure_filename(filename) 
      return f"knowledge_base/clean_wiki/{business_id}/{safe_filename}"
  ```
  This creates an architectural cage. It is structurally impossible for an operating system file pointer to traverse outside its specific folder boundaries, preventing cross-tenant data corruption or directory traversal attacks.

### 3. Operational Tier: Dynamic Runtime Context Binding
* **Enforcement Point:** `backend/app/knowledge_base/manager.py`
* **Mechanism:** When a customer texts the bot via the WhatsApp API webhook, the stateless network request contains only a phone number and a message string. 
* **Security Guardrail:** `manager.py` instantly queries core tables, maps the incoming phone line to its proper `business_id` context token, and hooks that token into the active async database session pool. Throughout the entire retrieval loop, all metadata processing (operating hours, delivery limits, support routes) is completely fenced within that active tenant's memory block.

---

### 📊 Multi-Tenant Architectural Benefits
- **Zero-Latency Scaling:** Onboarding a brand-new boutique store does not require spinning up expensive separate cloud instances or creating new database clusters. The platform scales dynamically with zero configuration overhead.
- **Elimination of Human-Error Leaks:** Moving the isolation boundary from the mutable application code level down to the immutable file path constraints and low-level PostgreSQL storage engine layer guarantees total data isolation security.


## How It Works (End-to-End)

## Phase 1: Upload & Parsing


- Business owner uploads a PDF/document via dashboard
- Document lands in knowledge_base/raw_uploads/{user_id}/
- Backend parsing script converts it to clean Markdown
- Cleaned Markdown saved to knowledge_base/clean_wiki/{user_id}/


## Phase 2: Indexing


- KnowledgeBaseManager.ingest_document() reads the Markdown file
- File is scanned for suspicious content (flag_suspicious_upload())
- Document is split into semantic chunks by Markdown section headers (e.g., "## Shipping", "## Returns")
- Each chunk inserted into wiki_chunks table with:

- user_id (which business)
- source_file (which document)
- section_path (e.g., "Shipping")
- content (the actual text)
- search_vector (Postgres full-text tsvector, 'simple' config)





## Phase 3: Retrieval


- Customer sends WhatsApp message: "Je, mnasafirisha nje ya Nairobi?"
- Webhook handler receives message, identifies business (user_id)
- Message normalized: normalize_query_for_retrieval() expands numerics ("4k" → "4000")
- KnowledgeBaseManager.build_prompt_payload() constructs the full prompt:

- SYSTEM RULES (from aisha_voice.txt)
- MERCHANT PROFILE (business name from database)
- STORE POLICY CONTEXT (retrieved chunks, fenced with random tag)
- LIVE INVENTORY (fresh from products table)
- RECENT CONVERSATION (from conversations table)
- CUSTOMER MESSAGE (the actual query)



Payload sent to Claude API
Response relayed back to customer via Twilio WhatsApp