import os
import google.generativeai as genai
from dotenv import load_dotenv
from rag.vector_store import FAISSVectorStore

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


SYSTEM_PROMPT = """You are an assistant helping the Venuebase sales team answer RFP questions.
Your ONLY job is to answer RFP (Request for Proposal) questions using the provided context excerpts from Venuebase' official documentation.
STRICT RULES you must follow without exception:
1. Answer using ONLY the information present in the provided context. Do NOT use any outside knowledge.
2. If the context does not contain enough information to answer the question, you MUST reply with exactly: Not found in references.
3. Do NOT guess, infer, or make assumptions beyond what is explicitly stated in the context.
4. Do NOT say things like "based on general knowledge" or "typically venues...".
5. At the end of every answer that IS found in references, append the source on a new line in this exact format:
   [Source: <filename>]
   If multiple sources were used, list each one separated by a comma.
6. Keep answers concise and factual. Do not add conversational filler.
7. If the question contains multiple parts, answer each part that is supported by the context. Mark any unsupported sub-parts as "Not found in references."
"""

#  SINGLE QUESTION ANSWERING

def answer_question(
    question: str,
    vector_store: FAISSVectorStore,
    top_k: int = 4,
) -> dict:
    retrieved_chunks = vector_store.query(question, top_k=top_k)

    if not retrieved_chunks:
        return _not_found_result(question)
 
    context_parts = []
    seen_sources = set()

    for i, chunk in enumerate(retrieved_chunks):
        context_parts.append(
            f"[Excerpt {i+1} from {chunk['source']}]\n{chunk['text']}"
        )
        seen_sources.add(chunk["source"])

    context_string = "\n\n".join(context_parts)
    top_score = retrieved_chunks[0]["score"] if retrieved_chunks else 0.0

   
    user_message = f"""Here are the relevant excerpts from Venuebase' documentation:

{context_string}

---

Question: {question}

Remember: Answer using ONLY the excerpts above. If the answer is not in the excerpts, reply with exactly: Not found in references."""

 
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(user_message)
        raw_answer = response.text.strip()
    except Exception as e:
        return {
            "question_text": question,
            "ai_answer": f"API error: {e}",
            "citation": "",
            "status": "error",
            "evidence": [c["text"] for c in retrieved_chunks],
            "top_score": top_score,
        }

    return _parse_response(
        question=question,
        raw_answer=raw_answer,
        retrieved_chunks=retrieved_chunks,
        top_score=top_score,
    )



#  BATCH ANSWERING

def answer_all_questions(
    questions: list[dict],
    vector_store: FAISSVectorStore,
    top_k: int = 4,
    progress_callback=None,
) -> list[dict]:
    results = []
    total = len(questions)

    for i, q in enumerate(questions):
        result = answer_question(
            question=q["question_text"],
            vector_store=vector_store,
            top_k=top_k,
        )
        result["question_id"] = q["question_id"]

        results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)

    return results


#  PARTIAL REGENERATION


def regenerate_selected(
    all_results: list[dict],
    selected_ids: list[int],
    vector_store: FAISSVectorStore,
    top_k: int = 4,
) -> list[dict]:
    id_to_index = {r["question_id"]: i for i, r in enumerate(all_results)}

    for q_id in selected_ids:
        if q_id not in id_to_index:
            continue

        idx = id_to_index[q_id]
        original_question_text = all_results[idx]["question_text"]

        new_result = answer_question(
            question=original_question_text,
            vector_store=vector_store,
            top_k=top_k,
        )
        new_result["question_id"] = q_id
        all_results[idx] = new_result

    return all_results


#  INTERNAL HELPERS

def _not_found_result(question: str) -> dict:
    return {
        "question_text": question,
        "ai_answer": "Not found in references.",
        "citation": "",
        "status": "not_found",
        "evidence": [],
        "top_score": 0.0,
    }


def _parse_response(
    question: str,
    raw_answer: str,
    retrieved_chunks: list[dict],
    top_score: float,
) -> dict:
    #  Not found
    if "not found in references" in raw_answer.lower():
        return {
            "question_text": question,
            "ai_answer": "Not found in references.",
            "citation": "",
            "status": "not_found",
            "evidence": [c["text"] for c in retrieved_chunks],
            "top_score": top_score,
        }

    #   Normal answer 
    citation = ""
    answer_text = raw_answer

    lines = raw_answer.strip().splitlines()
    source_lines = []
    answer_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("[source:"):
           
            inner = stripped[stripped.find(":") + 1:].strip().rstrip("]").strip()
            source_lines.append(inner)
        else:
            answer_lines.append(line)

    if source_lines:
        citation = ", ".join(source_lines)
        answer_text = "\n".join(answer_lines).strip()
    else:

        unique_sources = list(dict.fromkeys(c["source"] for c in retrieved_chunks))
        citation = ", ".join(unique_sources[:2])  

    return {
        "question_text": question,
        "ai_answer": answer_text,
        "citation": citation,
        "status": "answered",
        "evidence": [c["text"] for c in retrieved_chunks[:2]], 
        "top_score": top_score,
    }