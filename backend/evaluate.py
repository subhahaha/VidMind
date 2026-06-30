"""
evaluate.py — Answer quality evaluator for VidMind
Uses LLM-as-a-judge to score the RAG pipeline's answers.

Run with:
    python evaluate.py --url "https://youtube.com/watch?v=..."

Output:
    - Score for each question (1-5)
    - Average score
    - Per-question feedback
    - Results saved to eval_results.json
"""

import json
import argparse
import requests
import time
from rag_engine import RAGEngine

# ── Config ──────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# ── Test questions (used for every video) ───────────────────────
TEST_QUESTIONS = [
    "What is this video about?",
    "What are the key points covered?",
    "Explain the most important concept mentioned.",
    "What examples were given?",
    "What are the main takeaways?",
]


# ── LLM judge ───────────────────────────────────────────────────
def judge_answer(question: str, answer: str, context: str) -> dict:
    """Ask the LLM to score the answer 1-5 and explain why."""
    prompt = f"""You are an expert evaluator assessing the quality of an AI assistant's answer.

Score the answer from 1 to 5 using these criteria:
5 - Perfect: specific, accurate, directly answers the question using the context
4 - Good: mostly accurate and relevant, minor gaps
3 - Okay: partially answers the question but misses key details
2 - Poor: vague or generic, not grounded in the context
1 - Bad: wrong, irrelevant, or completely made up

QUESTION: {question}

CONTEXT (what the AI had access to):
{context}

AI ANSWER: {answer}

Respond ONLY in this exact JSON format, nothing else:
{{
  "score": <number 1-5>,
  "reason": "<one sentence explanation>",
  "specific": <true if answer uses specific details from context, false if generic>
}}"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 150}
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=60)
        raw = r.json().get("response", "").strip()
        # Clean up in case model adds extra text
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(raw[start:end])
    except Exception as e:
        print(f"  Judge error: {e}")
    return {"score": 0, "reason": "Evaluation failed", "specific": False}


# ── Get answer from RAG ─────────────────────────────────────────
def get_answer(rag: RAGEngine, question: str) -> tuple[str, str]:
    """Get answer and the context that was retrieved."""
    # Get context
    search_query = rag._build_search_query(question, [])
    context = rag._retrieve(search_query)

    # Get full answer (non-streaming for evaluation)
    full_answer = ""
    for token in rag.query_stream(question, []):
        full_answer += token

    return full_answer.strip(), context


# ── Main evaluation loop ─────────────────────────────────────────
def evaluate(url: str):
    print(f"\n{'='*60}")
    print("VidMind — RAG Evaluation")
    print(f"{'='*60}")
    print(f"Video: {url}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Questions: {len(TEST_QUESTIONS)}")
    print(f"{'='*60}\n")

    # Load video
    print("Loading video...")
    rag = RAGEngine()

    # Extract video ID
    import re
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]
    video_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break

    if not video_id:
        print("Could not extract video ID from URL")
        return

    num_chunks = rag.load_video(video_id)
    print(f"Video loaded — {num_chunks} chunks indexed\n")

    results = []
    total_score = 0

    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"Q{i}: {question}")

        # Get answer
        answer, context = get_answer(rag, question)
        print(f"Answer: {answer[:150]}{'...' if len(answer) > 150 else ''}")

        # Judge it
        evaluation = judge_answer(question, answer, context)
        score    = evaluation.get("score", 0)
        reason   = evaluation.get("reason", "")
        specific = evaluation.get("specific", False)

        total_score += score

        # Print result
        stars = "⭐" * score
        print(f"Score:  {score}/5 {stars}")
        print(f"Reason: {reason}")
        print(f"Specific to video: {'Yes' if specific else 'No (generic)'}")
        print()

        results.append({
            "question": question,
            "answer": answer,
            "score": score,
            "reason": reason,
            "specific": specific,
        })

        time.sleep(1)  # small pause between calls

    # ── Summary ─────────────────────────────────────────────────
    avg = total_score / len(TEST_QUESTIONS)
    print(f"{'='*60}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Average score:  {avg:.1f} / 5.0")
    print(f"Total score:    {total_score} / {len(TEST_QUESTIONS) * 5}")

    if avg >= 4.5:
        grade = "Excellent "
    elif avg >= 3.5:
        grade = "Good "
    elif avg >= 2.5:
        grade = "Average "
    else:
        grade = "Needs improvement "

    print(f"Grade:          {grade}")
    print(f"{'='*60}\n")

    # ── Save results ─────────────────────────────────────────────
    output = {
        "video_url": url,
        "video_id": video_id,
        "model": OLLAMA_MODEL,
        "average_score": round(avg, 2),
        "grade": grade,
        "results": results,
    }

    with open("eval_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("Results saved to eval_results.json")


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate VidMind answer quality")
    parser.add_argument("--url", required=True, help="YouTube video URL to evaluate")
    args = parser.parse_args()
    evaluate(args.url)