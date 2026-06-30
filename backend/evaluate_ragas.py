import json
import argparse
import re
import math
import os
import numpy as np
import faiss
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_utilization,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_groq import ChatGroq
from langchain_community.embeddings import OllamaEmbeddings


from rag_engine import RAGEngine

# ── Load environment variables ────────────────────────────────────
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found! Create a .env file in the backend folder "
        "with: GROQ_API_KEY=your_key_here"
    )

# ── Config ──────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2"          # used for generating the actual answers
GROQ_MODEL   = "llama-3.1-8b-instant"  # used as the fast RAGAS judge

TEST_DATA = [
    {
        "question":  "What is this video about?",
        "reference": "A general overview of the main topic covered in the video."
    },
    {
        "question":  "What are the key points covered in this video?",
        "reference": "The main concepts, ideas, and topics discussed throughout the video."
    },
    {
        "question":  "What examples or demonstrations were shown?",
        "reference": "Specific examples, demos, or illustrations used to explain concepts."
    },
    {
        "question":  "What are the main takeaways from this video?",
        "reference": "The most important lessons or conclusions from the video."
    },
    {
        "question":  "How does the speaker explain the core concept?",
        "reference": "The explanation and methodology used to describe the main concept."
    },
]


def is_nan(value):
    try:
        return math.isnan(float(value))
    except:
        return True


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID from URL")


def get_answer_and_contexts(rag: RAGEngine, question: str) -> tuple[str, list[str]]:
    search_query = rag._build_search_query(question, [])
    q_emb = rag.embedder.encode([search_query], show_progress_bar=False)
    q_emb = np.array(q_emb, dtype="float32")
    faiss.normalize_L2(q_emb)
    _, indices = rag.index.search(q_emb, 6)
    contexts = [rag.chunks[i] for i in indices[0] if i < len(rag.chunks)]
    full_answer = ""
    for token in rag.query_stream(question, []):
        full_answer += token
    return full_answer.strip(), contexts


def evaluate_ragas(url: str):
    print(f"\n{'='*60}")
    print("VidMind — RAGAS Evaluation (Groq-powered)")
    print(f"{'='*60}")
    print(f"Video:       {url}")
    print(f"Answer model: {OLLAMA_MODEL} (local)")
    print(f"Judge model:  {GROQ_MODEL} (Groq — fast cloud inference)")
    print(f"{'='*60}\n")

    print("Loading video...")
    rag = RAGEngine()
    video_id = extract_video_id(url)
    num_chunks = rag.load_video(video_id)
    print(f"✅ Video loaded — {num_chunks} chunks indexed\n")

    print("Generating answers (using local Ollama)...")
    questions, answers, contexts, references = [], [], [], []

    for item in TEST_DATA:
        print(f"  → {item['question']}")
        answer, ctx = get_answer_and_contexts(rag, item["question"])
        questions.append(item["question"])
        answers.append(answer)
        contexts.append(ctx)
        references.append(item["reference"])

    dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": references,
    })

    print("\nRunning RAGAS evaluation with Groq (should take under a minute)...\n")

    llm        = LangchainLLMWrapper(ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OllamaEmbeddings(model=OLLAMA_MODEL))

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_utilization,
            context_recall,
        ],
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )

    print(f"\n{'='*60}")
    print("RAGAS RESULTS")
    print(f"{'='*60}")

    scores = result.to_pandas()

    metrics = {
        "faithfulness":        "Is the answer grounded in the retrieved context?",
        "answer_relevancy":    "Does the answer actually address the question?",
        "context_utilization": "Were the retrieved chunks actually used?",
        "context_recall":      "Did we miss any important chunks?",
    }

    avg_scores = {}
    valid_scores = []

    for metric, description in metrics.items():
        if metric in scores.columns:
            avg = scores[metric].mean()
            if is_nan(avg):
                print(f"\n{metric.upper()}: N/A")
                print(f"  {description}")
            else:
                val = round(float(avg), 3)
                avg_scores[metric] = val
                valid_scores.append(val)
                bar = "█" * int(avg * 10) + "░" * (10 - int(avg * 10))
                print(f"\n{metric.upper()}: {val:.3f} [{bar}]")
                print(f"  {description}")

    print(f"\n{'='*60}")

    if valid_scores:
        overall = round(sum(valid_scores) / len(valid_scores), 3)
        if overall >= 0.8:   grade = "Excellent ✅"
        elif overall >= 0.6: grade = "Good 👍"
        elif overall >= 0.4: grade = "Average ⚠️"
        else:                grade = "Needs improvement ❌"
        print(f"OVERALL RAGAS SCORE: {overall} / 1.0")
        print(f"GRADE: {grade}")
    else:
        overall = None
        grade   = "Could not evaluate"
        print("⚠️  No metrics computed.")

    print(f"{'='*60}\n")

    try:
        per_q = []
        for record in scores.to_dict(orient="records"):
            clean = {}
            for k, v in record.items():
                if isinstance(v, float) and math.isnan(v):
                    clean[k] = None
                elif isinstance(v, np.ndarray):
                    clean[k] = v.tolist()
                elif isinstance(v, (np.floating,)):
                    clean[k] = float(v)
                elif isinstance(v, (np.integer,)):
                    clean[k] = int(v)
                else:
                    clean[k] = v
            per_q.append(clean)

        output = {
            "video_url":     url,
            "video_id":      video_id,
            "answer_model":  OLLAMA_MODEL,
            "judge_model":   GROQ_MODEL,
            "num_chunks":    num_chunks,
            "overall_score": overall,
            "grade":         grade,
            "metrics":       avg_scores,
            "per_question":  per_q,
        }

        with open("eval_ragas_results.json", "w") as f:
            json.dump(output, f, indent=2)

        print("Results saved to eval_ragas_results.json")

    except Exception as e:
        print(f"⚠️  Could not save JSON: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAGAS evaluation for VidMind (Groq-powered)")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    args = parser.parse_args()
    evaluate_ragas(args.url)