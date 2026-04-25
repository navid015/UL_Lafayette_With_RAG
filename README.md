# 🎓 UL Lafayette RAG Assistant

> An AI-powered **Retrieval-Augmented Generation (RAG)** chatbot for the **University of Louisiana at Lafayette** — built with OpenAI, ChromaDB, and Gradio 6.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Gradio](https://img.shields.io/badge/Gradio-6.0%2B-orange?style=flat-square)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1--nano-412991?style=flat-square&logo=openai)
![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-blueviolet?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [RAG Pipeline](#rag-pipeline)
- [Knowledge Base](#knowledge-base)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Running Evaluations](#running-evaluations)
- [UI Overview](#ui-overview)
- [Tech Stack](#tech-stack)

---

## Overview

The **UL Lafayette RAG Assistant** is a conversational AI chatbot that answers questions about the University of Louisiana at Lafayette using a curated knowledge base scraped from the university's official websites. It uses a **multi-stage RAG pipeline** — query rewriting, dual embedding retrieval, merging, and LLM-based reranking — to ground every answer in real source documents, showing users exactly which files were retrieved to generate each response.

The app features a fully branded **UL Lafayette UI** styled with the university's official colors: Vermilion Red `#CC0000`, Gold `#F0A500`, and Navy `#0A1628`.

---

## Features

- 🔍 **Multi-Stage RAG Pipeline** — query rewriting → dual retrieval → deduplication → LLM reranking → generation
- 💬 **Conversational Memory** — maintains full multi-turn history across a session
- 📚 **Source Transparency** — displays retrieved knowledge base documents alongside every answer
- 🎨 **UL Lafayette Branded UI** — official university colors, stats bar, and footer
- ⚡ **Quick Question Chips** — 5 pre-loaded one-click shortcuts for common queries
- 📊 **Evaluation Dashboard** — Gradio-based evaluator with MRR, nDCG, and LLM-as-judge scoring
- 🧹 **Clear Conversation** — reset button to start fresh at any time
- 🔄 **Auto-Ingestion** — vector database is built automatically on first run if missing

---

## Project Structure

```
UL_Lafayette_With_RAG/
│
├── app.py                          # Gradio 6 UI (UL Lafayette branded)
├── evaluator.py                    # Gradio evaluation dashboard
├── requirements.txt                # Python dependencies
├── .env                            # API keys (not committed)
├── .gitignore
│
├── evaluation/
│   ├── __init__.py
│   ├── eval.py                     # MRR, nDCG, LLM-as-judge scoring
│   ├── test.py                     # TestQuestion model + load_tests()
│   └── ull_tests.jsonl             # 133 RAG evaluation test cases
│
├── knowledge-base/
│   ├── overview_&_history/
│   │   ├── university_overview.md
│   │   ├── university_history.md
│   │   ├── rankings_and_recognition.md
│   │   └── leadership_and_administration.md
│   │
│   ├── admission_&_scholarship/
│   │   ├── scholarships_and_financial_aid.md
│   │   ├── admissions_academics_student_life.md
│   │   ├── majors_minors_concentrations.md
│   │   └── admissions_costs_and_academic_policies.md
│   │
│   ├── department_&_faculty/
│   │   ├── colleges_and_departments.md
│   │   ├── faculty_education_nursing_computing.md
│   │   ├── faculty_engineering_liberalarts.md
│   │   ├── faculty_arts_business_library.md
│   │   ├── faculty_sciences_biology_chemistry_math_physics.md
│   │   ├── faculty_chemical_electrical_petroleum_engineering.md
│   │   ├── faculty_criminaljustice_psychology_history_philosophy.md
│   │   ├── faculty_communication_languages_sociology.md
│   │   ├── faculty_polisci_communicative_disorders_civil_engineering.md
│   │   └── faculty_architecture_design_graduate_school.md
│   │
│   ├── research/
│   │   └── research_centers_and_faculty_research.md
│   │
│   └── student_experience/
│       └── student_experience_housing_dining_campus_life.md
│
├── preprocessed_db/                # ChromaDB vector store (auto-generated)
│
└── pro_implementation/
    ├── __init__.py
    ├── answer.py                   # Full RAG pipeline: rewrite → retrieve → rerank → generate
    └── ingest.py                   # Document loading, chunking, embedding, ChromaDB ingestion
```

---

## RAG Pipeline

The pipeline in `pro_implementation/answer.py` implements a production-grade multi-stage RAG strategy:

```
User Question
      │
      ▼
┌──────────────────────┐
│  1. Query Rewriting  │  gpt-4.1-nano rewrites the question for better
│                      │  semantic retrieval using conversation history
└──────────┬───────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌─────────┐
│ Embed   │  │ Embed   │  text-embedding-3-large
│ Original│  │Rewritten│  k=8 results each
└────┬────┘  └────┬────┘
     └──────┬─────┘
            ▼
┌───────────────────────┐
│  3. Merge & Deduplicate│  Union of both result sets,
│                        │  deduped by page_content
└───────────┬────────────┘
            ▼
┌───────────────────────┐
│  4. LLM Reranking     │  gpt-4.1-nano scores and reorders
│                        │  merged chunks by relevance → top-5
└───────────┬────────────┘
            ▼
┌───────────────────────┐
│  5. RAG Generation    │  gpt-4.1-nano generates the final answer
│                        │  from top-5 chunks + conversation history
└───────────┬────────────┘
            ▼
   Answer + Retrieved Chunks
```

### Key Parameters

**`answer.py`**

| Parameter | Value | Description |
|---|---|---|
| `MODEL` | `gpt-4.1-nano` | LLM for query rewriting, reranking, and generation |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `RETRIEVAL_K` | `8` | Chunks retrieved per query (×2 = up to 16 before dedup) |
| `FINAL_K` | `5` | Top chunks passed to the generator after reranking |

**`ingest.py`**

| Parameter | Value | Description |
|---|---|---|
| `CHUNK_SIZE` | `1200` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `COLLECTION_NAME` | `docs` | ChromaDB collection name |
| `DB_NAME` | `preprocessed_db/` | ChromaDB persistent storage path |

Each chunk is prepended with `Source: <path>` and `Type: <folder>` metadata before embedding, so source attribution is baked into every retrieved chunk.

---

## Knowledge Base

**20 markdown files** scraped from [louisiana.edu](https://louisiana.edu) and its department subsites, organized into 5 thematic folders:

| Folder | Files | Content |
|---|---|---|
| `overview_&_history/` | 4 | University quick facts, full history (1898–present), all national rankings, complete leadership directory with all deans and VP contacts |
| `admission_&_scholarship/` | 4 | All scholarships (Live Oak, Magnolia, Cypress, TOPS, transfer, international), admissions process, 240+ majors & minors listing, costs, FAFSA, academic policies |
| `department_&_faculty/` | 10 | All 9 colleges, 41 departments — full faculty directories with name, title, office, phone, email, research areas for every department |
| `research/` | 1 | Every research center, institute, and lab with faculty research specializations |
| `student_experience/` | 1 | Housing (3,723 beds, 9 halls, all types), dining, health services, clubs, campus traditions, Lafayette city guide |

---

## Installation

### Prerequisites
- Python 3.10 or higher
- An OpenAI API key

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/UL_Lafayette_With_RAG.git
cd UL_Lafayette_With_RAG

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

> **Note:** The `.env` file is already in `.gitignore`. Never commit API keys.

---

## Running the App

```bash
source venv/bin/activate
python app.py
```

The app opens automatically in your browser at `http://127.0.0.1:7860`.

**First run:** if `preprocessed_db/` does not exist, the ingestion pipeline runs automatically — this embeds all 20 knowledge base files into ChromaDB before the UI loads. To trigger ingestion manually:

```bash
python pro_implementation/ingest.py
```

---

## Running Evaluations

### Evaluation Dashboard

A Gradio-based dashboard with two independent evaluation sections:

```bash
python evaluator.py
```

**Retrieval Evaluation** — measures vector store retrieval quality using the keywords in each test case:

| Metric | Description | Threshold |
|---|---|---|
| **MRR** | Mean Reciprocal Rank — average position of first relevant chunk | 🟢 ≥ 0.90 · 🟡 ≥ 0.75 · 🔴 below |
| **nDCG** | Normalized Discounted Cumulative Gain (binary relevance) | 🟢 ≥ 0.90 · 🟡 ≥ 0.75 · 🔴 below |
| **Keyword Coverage** | % of expected keywords found in top-k results | 🟢 ≥ 90% · 🟡 ≥ 75% · 🔴 below |

**Answer Evaluation** — `gpt-4.1-nano` judges each generated answer against the reference answer:

| Metric | Scale | Description | Threshold |
|---|---|---|---|
| **Accuracy** | 1–5 | Factual correctness; any wrong answer scores 1 | 🟢 ≥ 4.5 · 🟡 ≥ 4.0 · 🔴 below |
| **Completeness** | 1–5 | Coverage of all information in the reference answer | 🟢 ≥ 4.5 · 🟡 ≥ 4.0 · 🔴 below |
| **Relevance** | 1–5 | How directly the answer addresses the question | 🟢 ≥ 4.5 · 🟡 ≥ 4.0 · 🔴 below |

Results are shown as color-coded metric cards plus a bar chart broken down by question category.

### CLI Evaluation

Run and print detailed results for a single test case by its row number (0-indexed):

```bash
python evaluation/eval.py 0     # test case #0
python evaluation/eval.py 42    # test case #42
```

Output includes: retrieval MRR, nDCG, keyword coverage, the generated answer, LLM feedback, and scores for accuracy / completeness / relevance.

### Test Dataset — `evaluation/ull_tests.jsonl`

133 test cases across 6 categories:

| Category | Count | Description |
|---|---|---|
| `direct_fact` | 60 | Single-fact lookups — names, emails, phones, addresses, titles |
| `numerical` | 19 | Numeric answers — enrollment, scholarship amounts, counts, rankings |
| `temporal` | 12 | Date-based questions — when things happened or were founded |
| `relationship` | 17 | Connections between people, departments, buildings, and programs |
| `holistic` | 15 | Multi-part synthesis requiring several facts combined into one answer |
| `spanning` | 10 | Cross-document questions requiring information from multiple files |

Each record format:
```json
{
  "question": "Who is the President of UL Lafayette?",
  "keywords": ["Ramesh", "Kolluru", "President"],
  "reference_answer": "Dr. Ramesh Kolluru serves as the President of UL Lafayette.",
  "category": "direct_fact"
}
```

---

## UI Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🎓 UL Lafayette RAG Assistant                     [POWERED BY AI]       │
│  Your intelligent guide to UL Lafayette                                   │
│  (Red gradient header · Gold left border · Gold badge)                   │
├────────────┬───────────┬──────────┬──────────┬──────────┬───────────────┤
│  16,100+   │   240+    │   45+    │   $4.4B  │    R1    │     20+       │
│  Students  │  Majors   │ Grad Prgs│  Impact  │Carnegie  │  KB Files     │
│                  (Gold numbers on Navy background)                        │
├───────────────────────────────────┬──────────────────────────────────────┤
│ 💬 Conversation                   │ 📚 Knowledge Base Context            │
│ (Red panel header · Red dot)      │ (Red panel header · Red dot)         │
│                                   │                                      │
│  ╔══════════════════════╗         │  📁 Source 1: filename.md            │
│  ║ User message bubble  ║         │  ▏Retrieved document text...         │
│  ║ (Vermilion Red)      ║         │  ▏(left-bordered, styled)            │
│  ╚══════════════════════╝         │                                      │
│                                   │  ──────────────────────────          │
│  ╔══════════════════════╗         │                                      │
│  ║ Bot response bubble  ║         │  📁 Source 2: filename.md            │
│  ║ (Dark Navy)          ║         │  ▏...                                │
│  ╚══════════════════════╝         │                                      │
│                                   │                                      │
│  ⚡ QUICK QUESTIONS               │                                      │
│  [Chip][Chip][Chip][Chip][Chip]  │                                      │
│                                   │                                      │
│  ┌──────────────────┐  [Send ➤]  │                                      │
│  │ Ask anything...  │             │                                      │
│  └──────────────────┘             │                                      │
│  [🗑️  Clear Conversation]        │                                      │
├───────────────────────────────────┴──────────────────────────────────────┤
│  🏛️ louisiana.edu  ·  104 E. University Circle  ·  (337) 482-1000        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Notes |
|---|---|---|
| **LLM** | OpenAI `gpt-4.1-nano` | Query rewriting, chunk reranking, answer generation |
| **Embeddings** | OpenAI `text-embedding-3-large` | Semantic vector embeddings for retrieval |
| **Vector Store** | ChromaDB (persistent) | Local store at `preprocessed_db/`; auto-built on first run |
| **UI** | Gradio 6.0 | Custom CSS with UL Lafayette brand colors |
| **Retry Logic** | tenacity | Exponential backoff on all OpenAI API calls |
| **Evaluation LLM** | litellm → `gpt-4.1-nano` | Structured JSON outputs via pydantic `BaseModel` |
| **Data Validation** | pydantic v2 | `TestQuestion`, `RetrievalEval`, `AnswerEval`, `RankOrder` models |
| **Environment** | python-dotenv | `.env` file for `OPENAI_API_KEY` |
| **Knowledge Base** | 20 Markdown files | Scraped from louisiana.edu and all department subsites |
| **Test Dataset** | JSONL (133 questions) | 6 categories: direct_fact, numerical, temporal, relationship, holistic, spanning |

---

## About UL Lafayette

The **University of Louisiana at Lafayette** is a Carnegie R1 research university founded in 1898, located in Lafayette, Louisiana. It is the largest institution in the University of Louisiana System with 16,100+ enrolled students, 240+ academic programs, 45+ graduate degrees, and a $4.4 billion annual economic impact on Louisiana.

- 🌐 [louisiana.edu](https://louisiana.edu)
- 📍 104 E. University Circle, Lafayette, LA 70503
- 📞 (337) 482-1000
- 📧 contact@louisiana.edu

---

*Built for the Ragin' Cajuns community. Geaux Cajuns! 🔴⚡*
