import os
import re
import pdfplumber
import PyPDF2
from pathlib import Path

#  RAW TEXT EXTRACTION

def extract_text_from_pdf(file_obj) -> str:
    text = ""

    try:
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception:
        text = ""

    # Fallback to PyPDF2
    if not text.strip():
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            reader = PyPDF2.PdfReader(file_obj)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            raise ValueError(f"Could not extract text from PDF: {e}")

    return text.strip()


def extract_text_from_txt(file_obj) -> str:
    if isinstance(file_obj, (str, Path)):
        with open(file_obj, "r", encoding="utf-8") as f:
            return f.read().strip()

    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8").strip()
        return raw.strip()

    raise ValueError("Unsupported file object type for TXT extraction.")


def extract_text(file_obj, filename: str) -> str:
    name = filename.lower()

    if name.endswith(".pdf"):
        return extract_text_from_pdf(file_obj)
    elif name.endswith(".txt"):
        return extract_text_from_txt(file_obj)
    else:
        raise ValueError(
            f"Unsupported file type: '{filename}'. "
            "Only .pdf and .txt reference documents are supported."
        )


#  TEXT CHUNKING

def chunk_text(
    text: str,
    source_name: str,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[dict]:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            boundary = max(
                text.rfind(".", start, end),
                text.rfind("\n", start, end),
                text.rfind("?", start, end),
            )
            if boundary != -1 and boundary > start + (chunk_size // 2):
                end = boundary + 1   # include the punctuation

        chunk_text_slice = text[start:end].strip()

        if chunk_text_slice:
            chunks.append({
                "text": chunk_text_slice,
                "source": source_name,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        start = end - overlap

    return chunks

#  LOAD ALL REFERENCE DOCS FROM A FOLDER

def load_reference_docs_from_folder(folder_path: str) -> list[dict]:
    folder = Path(folder_path)
    all_chunks = []

    for file_path in sorted(folder.iterdir()):
        if file_path.suffix.lower() not in (".pdf", ".txt"):
            continue
        try:
            text = extract_text(str(file_path), file_path.name)
            chunks = chunk_text(text, source_name=file_path.name)
            all_chunks.extend(chunks)
            print(f"  Loaded '{file_path.name}' → {len(chunks)} chunks")
        except Exception as e:
            print(f"  WARNING: Skipping '{file_path.name}': {e}")

    return all_chunks



#  QUESTIONNAIRE PARSING

def parse_questionnaire(file_obj, filename: str) -> list[dict]:
    import pandas as pd
    import io

    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        file_like = io.BytesIO(raw)
    else:
        file_like = file_obj

    name = filename.lower()

    if name.endswith(".csv"):
        df = pd.read_csv(file_like)
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(file_like)
    else:
        raise ValueError(
            f"Unsupported questionnaire format: '{filename}'. "
            "Please upload a .csv or .xlsx file."
        )

    question_col = None
    for col in df.columns:
        if col.strip().lower() in (
            "question", "questions", "question text",
            "question_text", "query", "queries", "rfp question"
        ):
            question_col = col
            break

    if question_col is None:
        question_col = df.columns[-1]

    id_col = None
    for col in df.columns:
        if col.strip().lower() in (
            "id", "question id", "question_id", "no", "number", "#"
        ):
            id_col = col
            break

    questions = []
    for i, row in df.iterrows():
        q_text = str(row[question_col]).strip()
        if not q_text or q_text.lower() in ("nan", "none", ""):
            continue

        q_id = int(row[id_col]) if id_col and pd.notna(row[id_col]) else i + 1

        questions.append({
            "question_id": q_id,
            "question_text": q_text,
        })

    if not questions:
        raise ValueError(
            "No questions found in the uploaded file. "
            "Please check that your file has a recognisable question column."
        )

    return questions