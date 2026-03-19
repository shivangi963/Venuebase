# Venuebase — RFP Auto-Responder

An AI-powered tool that automatically answers corporate event RFP (Request for Proposal)
questionnaires by retrieving answers strictly from uploaded reference documents —
and never hallucinating answers that aren't there.

---

## Table of Contents

1. [Why This Industry](#why-this-industry)
2. [Problem Statement](#problem-statement)
3. [Live Demo Flow](#live-demo-flow)
4. [Architecture Overview](#architecture-overview)
5. [Tech Stack & Trade-offs](#tech-stack--trade-offs)
6. [Project Structure](#project-structure)
7. [Setup & Installation](#setup--installation)
8. [Feature Breakdown](#feature-breakdown)
9. [The "Not Found" Guarantee](#the-not-found-guarantee)
10. [Database Schema](#database-schema)
11. [RAG Pipeline Deep Dive](#rag-pipeline-deep-dive)
12. [Nice-to-Have Features Implemented](#nice-to-have-features-implemented)
13. [Known Limitations & Future Work](#known-limitations--future-work)
14. [Alignment with Almabase](#alignment-with-almabase)

---

## Why This Industry

I chose the **Corporate Event Management & Hospitality** industry for three reasons:

**1. Direct relevance to Almabase's core domain.**
Almabase is an event management platform. The workflows
here — structured data intake, document grounding, review before publish — mirror the
exact problems Almabase solves for development offices and reunion committees. Building
in this domain lets me demonstrate product thinking that translates directly to your users.

**2. The "Not Found" constraint has real legal stakes.**
In corporate events, an incorrect answer on an RFP (e.g. falsely claiming ADA compliance
or misstating a cancellation policy) can expose a company to contract disputes and
liability claims. This makes the strict grounding requirement non-negotiable — not just
a nice engineering property, but a business-critical correctness guarantee.

**3. The data shape is ideal for RAG.**
Venue documentation is long, structured, and policy-dense. It lives in PDFs and text
files. Clients ask specific, factual questions. This is the canonical RAG use case:
retrieve the right paragraph, generate a grounded answer, cite the source.

---

## Problem Statement

Corporate event planners from companies like Google and Microsoft send 100-question
Excel spreadsheets to venue sales teams. Each question is highly specific:

- *"What is your maximum ballroom capacity?"*
- *"Do you support 1 Gbps dedicated Wi-Fi?"*
- *"What is your cancellation policy at 45 days?"*

The Venuebase GTM team currently answers these **manually** — searching through
floorplan PDFs, catering policy docs, and liability terms — taking 2–3 days per RFP.
Slow turnaround risks losing deals to competitors who respond faster.

**This tool reduces that to minutes.**

---
##  Live Demo
 https://venuebase-jvaehzw7ptfvpcg9mvkehg.streamlit.app/

---

## Live Demo Flow

```
1. Sign up / Log in
        ↓
2. Create a new RFP project (e.g. "Google 2026 Annual Retreat")
        ↓
3. Upload reference documents (PDF / TXT venue policy files)
   Upload questionnaire (CSV / XLSX from the client)
        ↓
4. Click "Generate All Answers"
   → RAG pipeline runs: retrieve → ground → answer → cite
        ↓
5. Review answers in editable table
   → Coverage summary shows: 7 answered, 1 not found
   → Edit "Not found" rows manually
   → View evidence snippets to verify AI reasoning
   → Regenerate specific rows if you updated a document
        ↓
6. Export as CSV or formatted XLSX
   → XLSX is colour-coded, has a Legend sheet, ready to send
```

---

## Tech Stack & Trade-offs

### Frontend: Streamlit
**Why:** Streamlit eliminates the need to build a separate React/Next.js frontend,
allowing 100% of engineering effort to go into the RAG pipeline — which is the
core deliverable being evaluated.

**Trade-off:** A custom React frontend would offer more UI flexibility (drag-and-drop
uploads, richer animations, more granular state management). For this scope, Streamlit's
`st.data_editor` gives us an editable, exportable table with almost zero boilerplate.

**What I'd do at scale:** Decouple into a FastAPI backend + React frontend once the
AI pipeline is stable and the UX requirements are better defined.

---

### AI / LLM: Gemini API(Gemini 2.0 Flash)
**Why:** Gemini's instruction-following on strict constraints ("answer ONLY from context,
output EXACTLY 'Not found in references' otherwise") is exceptionally reliable. The
`gemini 2.0 flash` model balances speed, cost, and accuracy well for this use case.

**Trade-off:** Using the Gemini API introduces a dependency on an external service
and per-token costs. An open-source alternative (e.g. Mistral via Ollama) would be
fully local and free, but would require more prompt engineering to match the
instruction-following quality on the strict "Not found" constraint.

---

### Embeddings: sentence-transformers (all-MiniLM-L6-v2)
**Why:** Runs fully locally with no API key required. Fast, lightweight (80MB model),
and produces 384-dimensional embeddings that are more than adequate for semantic search
over short policy documents.

**Trade-off:** OpenAI's `text-embedding-3-small` would produce higher quality embeddings
for ambiguous queries, but adds API cost and latency. For a corpus of 4 policy documents
with ~40 total chunks, `all-MiniLM-L6-v2` retrieves the right chunks reliably.

---

### Vector Store: FAISS (in-memory)
**Why:** Zero infrastructure overhead. No separate database server to run. The index
is rebuilt from the uploaded documents each session, which is acceptable given the
small corpus size (typically < 100 chunks across 4–6 venue documents).

**Trade-off:** Index is lost when the Streamlit session ends. For a production system
with a large, shared document corpus, I would use a persistent vector store like
Pinecone, Weaviate, or pgvector. The FAISS index could also be serialised to disk
(the `save()` / `load()` methods on `FAISSVectorStore` support this) as a stepping
stone.

---

### Database: MongoDB Atlas
**Why:** Schema-flexible JSON storage is a natural fit for RFP questionnaires, which
vary in structure across clients. Storing each question as a sub-document in an array
allows atomic updates (update one question without rewriting the whole project).
MongoDB Atlas offers a generous free tier for development and review.

**Trade-off:** A relational schema in PostgreSQL would offer stronger referential
integrity (e.g. foreign key from projects to users). For this use case, the flexibility
of MongoDB outweighs the benefit of strict schemas.

---

### Authentication: bcrypt + st.session_state
**Why:** bcrypt is the industry standard for password hashing. `st.session_state`
provides a simple, built-in session mechanism for Streamlit apps without requiring
a cookie library or JWT infrastructure.

**Trade-off:** `st.session_state` is in-process only — it doesn't persist across
browser tabs or server restarts. For production, I would replace this with
`streamlit-authenticator` backed by signed JWT tokens stored in HTTP-only cookies.


## Setup & Installation

### Prerequisites
- Python 3.10 or higher
- A MongoDB Atlas account (free tier works fine)
- An Gemini API key

### Step 1 — Clone and set up environment

```bash
git clone https://github.com/your-username/venue-rfp-responder.git
cd venue-rfp-responder

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Step 2 — Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=sk-ant-your-key-here
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/
MONGODB_DB_NAME=venue_rfp
```

**Getting a MongoDB URI:**
1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → create a free cluster
2. Click **Connect** → **Drivers** → copy the connection string
3. Replace `<password>` with your database user's password

**Getting a Gemini API key:**
1. To get your Gemini key → go to aistudio.google.com → Sign in → click "Get API Key" → "Create API key" → copy it.


### Step 3 — Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

### Step 4 — Test with sample data

1. Sign up for a new account
2. Create a project named *"Google 2026 Retreat RFP"*
3. Upload all four files from `reference_docs/` as reference documents
4. Upload `sample_rfp_questionnaire.csv` as the questionnaire
5. Click **Index Reference Documents**, then **Parse Questionnaire**
6. Click **Generate All Answers**
7. Observe that Q7 (helicopter shuttles) returns `"Not found in references."`
8. Export to XLSX and inspect the colour-coded output

---

## Feature Breakdown

### Phase 1 — Core Workflow (Must Have)

| Requirement | Implementation |
|---|---|
| Sign up and log in | `auth_utils.py` — bcrypt hashing, MongoDB users collection |
| Upload questionnaire (CSV/XLSX) | `document_loader.parse_questionnaire()` — pandas, auto-detects question column |
| Upload reference documents (PDF/TXT) | `document_loader.extract_text()` — pdfplumber + PyPDF2 fallback |
| Generate answers with citations | `answering_engine.answer_all_questions()` — Gemini           RAG pipeline |
| "Not found in references" guard | Strict system prompt + response parser |
| Structured web view (Q / Answer / Citation) | `st.data_editor` with locked and editable columns |
| Persistent storage | MongoDB `rfp_projects` collection — saved after every generation |

### Phase 2 — Review & Export (Must Have) 

| Requirement | Implementation |
|---|---|
| Edit answers before export | `st.data_editor` — AI Answer column is fully editable |
| Downloadable document | CSV via `st.download_button`, XLSX via `utils/export.py` |
| Original question structure preserved | Questions locked in export; answers inserted alongside |
| Citations in export | Citation column included in both CSV and XLSX |
| Same structure as input | Question ID and text order preserved from original upload |

### Nice-to-Have Features 

| Feature | Implementation |
|---|---|
| Coverage Summary | `_render_coverage_summary()` — 4 `st.metric` tiles |
| Evidence Snippets | `_render_evidence_snippets()` — expandable raw chunk viewer |
| Partial Regeneration | Regenerate checkbox column + `regenerate_selected()` in engine |
| Confidence Score | Cosine similarity score mapped to `st.column_config.ProgressColumn` |

---

## The "Not Found" Guarantee

This is the most business-critical feature of the tool. An incorrect answer on a
corporate RFP can expose Venuebase to contract disputes, liability claims, and
reputational damage.

### How it works — three layers of enforcement

**Layer 1 — Retrieval context is explicit and labelled**

Each chunk passed to gemini is prefixed with its source filename:
```
[Excerpt 1 from Cancellation_and_Liability_Terms.txt]
... chunk text ...

[Excerpt 2 from Floorplans_and_AV_Specs.txt]
... chunk text ...
```

This makes it unambiguous to the model where information comes from.

**Layer 2 — System prompt is maximally restrictive**

```
You are a corporate venue compliance assistant for Venuebase.
Answer using ONLY the information present in the provided context.
If the context does not contain enough information to answer the
question, you MUST reply with exactly: Not found in references.
Do NOT guess, infer, or make assumptions beyond what is explicitly
stated in the context.
```

The phrase "you MUST reply with exactly" combined with the exact target string
has been tested to produce reliable refusals on out-of-scope questions.

**Layer 3 — Response parser catches edge cases**

Even if the model produces a variation like *"This information is not found in
the provided references"*, the parser checks for `"not found in references"` as
a case-insensitive substring and normalises it to the canonical string.

### Test case — the trap question

Question 7 in the sample questionnaire deliberately asks:
> *"Do you provide complimentary helicopter shuttle services from the airport?"*

This topic appears nowhere in any reference document. The system correctly returns:
```
Not found in references.
```
No citation is attached. The status column shows `not_found`. The XLSX row is
highlighted orange, signalling to the sales rep that manual input is required.

---

## Database Schema

### `users` collection

```json
{
  "_id": ObjectId("..."),
  "username": "sarah_events",
  "email": "sarah@luminavenues.com",
  "password_hash": "$2b$12$...",
  "created_at": ISODate("2025-01-15T10:30:00Z")
}
```

Indexes: `username` (unique), `email` (unique)

---

### `rfp_projects` collection

```json
{
  "_id": ObjectId("..."),
  "user_id": "64f3a2b1c9e7d80012345678",
  "project_name": "Google 2026 Annual Retreat RFP",
  "created_at": ISODate("2025-01-15T11:00:00Z"),
  "updated_at": ISODate("2025-01-15T11:45:00Z"),
  "status": "completed",
  "questions": [
    {
      "question_id": 1,
      "question_text": "What is the maximum seating capacity of your main ballroom?",
      "ai_answer": "The maximum seating capacity of the main ballroom is 500 persons in banquet-style rounds. Theater-style capacity is 600 persons.",
      "citation": "Floorplans_and_AV_Specs.txt",
      "status": "answered",
      "evidence": ["Chunk text used for retrieval..."],
      "top_score": 0.91
    },
    {
      "question_id": 7,
      "question_text": "Do you provide complimentary helicopter shuttle services from the airport?",
      "ai_answer": "Not found in references.",
      "citation": "",
      "status": "not_found",
      "evidence": [],
      "top_score": 0.21
    }
  ]
}
```

Index: `user_id` (for fast per-user project listing)

---


**Chunk size rationale:** 400 characters (~80 tokens) is small enough that each
chunk covers one policy clause, large enough to contain a complete answer.
The 80-character overlap ensures a sentence split at a chunk boundary is still
captured by the next chunk.

**top_k = 4 rationale:** Retrieves enough context to answer multi-part questions
(e.g. a question about both dietary restrictions and outside catering) while staying
within a context window that gemini processes quickly.

---

## Nice-to-Have Features Implemented

### 1. Coverage Summary
Four `st.metric` tiles rendered at the top of the review section:
- **Total Questions** — total rows in the questionnaire
- **Answered with Citations** — status == "answered"
- **Not Found in References** — status == "not_found"
- **Manually Edited** — status == "manual" (set when user edits a "not_found" row)

The delta values show percentages, giving the sales rep an instant read on
how comprehensively their documentation covers the client's questions.

### 2. Evidence Snippets
An expandable section below the review table shows the raw text chunks that
were retrieved from FAISS for each question. This serves two purposes:
- **Transparency:** The sales rep can verify that the AI's answer matches
  what the source document actually says.
- **Debugging:** If an answer seems wrong, the evidence snippets reveal
  whether the retrieval step or the generation step is at fault.

### 3. Partial Regeneration
A `Regenerate` checkbox column in `st.data_editor` lets the user select
specific rows to re-run. Common use case: a sales manager uploads a corrected
version of the AV spec document and wants to refresh only the AV-related
answers without invalidating the rest of the project.

The `regenerate_selected()` function in `answering_engine.py` accepts the
updated vector store (rebuilt from the new document) and re-runs only the
selected question IDs in-place, preserving all other results.

### 4. Confidence Score
Each answer includes a `top_score` — the cosine similarity between the
question embedding and the best-matching chunk. This is displayed as a
progress bar in the review table. Scores below ~0.4 correlate with lower
retrieval quality and are a useful signal that the answer may need review
even if the AI produced one.

---

## Known Limitations & Future Work

| Limitation | Suggested Fix |
|---|---|
| FAISS index is in-memory only | Serialise to disk with `FAISSVectorStore.save()` between sessions |
| Session state lost on server restart | Replace `st.session_state` auth with JWT + HTTP-only cookies |
| Single-user vector store | Move to a per-project persistent vector store (pgvector or Pinecone) |
| No multi-tenancy for shared document libraries | Add a `shared_docs` collection and per-org document management |
| Excel files with merged cells may mis-parse | Add a pre-processing step to flatten merged headers before pandas reads |
| No rate limiting on API calls | Add exponential backoff + `tenacity` retry decorator to gemini calls |
| Password reset not implemented | Add email-based reset flow using SendGrid or similar |

---

## Alignment with Almabase

Almabase's core product helps institutions manage alumni events, track engagement,
and run fundraising campaigns. The workflows this tool demonstrates map directly:

| This Project | Almabase Equivalent |
|---|---|
| RFP questionnaire upload + parsing | Event registration form ingestion |
| Reference documents as source of truth | Alumni database + giving history as source of truth |
| Grounded AI answers with citations | AI-generated donor outreach grounded in giving history |
| Review before export workflow | Campaign review before email send |
| Coverage summary metrics | Engagement dashboard for development officers |
| "Not found" → manual fallback | Unknown alumni → manual outreach queue |

The underlying pattern — **structured input + grounded AI + human review + export** —
is the same pattern Almabase needs to build trust between AI-generated content and
the development officers who are accountable for every communication they send.

---

## Author
Built by shivangi shukla