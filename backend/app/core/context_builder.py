"""
Context builder (§6.4): assembles 2-4 sub-queries for the RAG engine.

Three query types:
  1. Skill-overlap  — goes deeper on what the candidate claims to know.
  2. Gap-coverage   — role fundamentals not evident in the resume.
  3. Follow-up      — adaptive; based on the topic + score of the last answer.
"""
import random

# Per-role fundamental topics — used to detect coverage gaps
_ROLE_FUNDAMENTALS: dict[str, list[str]] = {
    "AI/ML Engineer": [
        "gradient descent optimization",
        "neural network backpropagation",
        "model evaluation metrics",
        "regularization techniques",
        "transformer attention mechanism",
        "convolutional neural networks",
        "feature engineering",
        "bias-variance tradeoff",
        "ensemble methods random forests",
        "unsupervised learning clustering",
    ],
    "Data Science / Applied ML": [
        "data preprocessing and feature engineering",
        "supervised learning classification regression",
        "model selection and cross-validation",
        "decision trees and ensemble methods",
        "dimensionality reduction PCA",
        "clustering algorithms k-means",
        "gradient boosting XGBoost",
        "evaluation metrics precision recall",
        "linear regression logistic regression",
        "support vector machines SVM",
    ],
}

_DEFAULT_FUNDAMENTALS = ["core concepts", "fundamentals", "best practices"]


def build_queries(
    profile_summary: str,
    skills: list[str],
    technologies: list[str],
    role_name: str,
    session_history: list[dict],  # [{topic, score, difficulty}]
) -> list[str]:
    """
    Return 2-3 sub-queries for the RAG engine.

    session_history items: {topic: str, score: int, difficulty: str}
    """
    queries: list[str] = []
    fundamentals = _ROLE_FUNDAMENTALS.get(role_name, _DEFAULT_FUNDAMENTALS)
    covered_topics = {h["topic"].lower() for h in session_history}

    # 1. Skill-overlap query
    all_known = skills + technologies
    if all_known:
        skill_sample = random.choice(all_known[:8])
        queries.append(f"{skill_sample} concepts and applications for {role_name}")

    # 2. Gap-coverage query — pick an uncovered fundamental
    uncovered = [f for f in fundamentals if not any(c in f for c in covered_topics)]
    if uncovered:
        queries.append(random.choice(uncovered))
    else:
        # All fundamentals covered — pick a random one to go deeper
        queries.append(random.choice(fundamentals))

    # 3. Follow-up query (from Q2 onward)
    if session_history:
        last = session_history[-1]
        topic = last["topic"]
        score = last["score"]
        if score <= 2:
            # Weak — probe simpler / foundational aspect of same topic
            queries.append(f"introduction basics {topic}")
        elif score >= 4:
            # Strong — go deeper or to an advanced adjacent topic
            queries.append(f"advanced {topic} techniques edge cases")
        else:
            # Adequate — move breadth
            remaining = [f for f in fundamentals if f not in covered_topics and topic.lower() not in f]
            if remaining:
                queries.append(random.choice(remaining))

    return queries[:3]  # cap at 3


def primary_query_string(queries: list[str]) -> str:
    """Combine queries into one retrieval_query string for traceability storage."""
    return " | ".join(queries)
