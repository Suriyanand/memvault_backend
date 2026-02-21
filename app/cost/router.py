import re

COMPLEX_PATTERNS = [
    r'\b(explain|analyze|compare|evaluate|implement|architect|design|optimize)\b',
    r'\b(write|create|build|generate|develop)\b.{10,}',
    r'\b(why|how does|how do|what are the implications|how would)\b',
    r'\bcode\b|\bprogram\b|\balgorithm\b|\bfunction\b|\bclass\b',
    r'\b(pros and cons|advantages|disadvantages|tradeoffs|difference between)\b',
    r'\b(research|thesis|essay|report|architecture|system design)\b',
    r'\b(transformer|neural network|machine learning|deep learning|llm|gpt)\b',
    r'\b(fastapi|react|nextjs|database|redis|postgresql|docker)\b',
    r'\b(step by step|in detail|comprehensive|thorough|detailed)\b',
]

SIMPLE_PATTERNS = [
    r'^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|bye|sure|great|cool|nice|got it)[\s!.?]*$',
    r'^what is (a |an |the )?\w+\?*$',
    r'^who is \w+\?*$',
    r'^when (was|is|did) .{0,20}\?*$',
    r'^define \w+\?*$',
]

MODEL_CONFIG = {
    "simple": {
        "model_id":    "llama-3.1-8b-instant",
        "label":       "Groq Llama 3.1 8B",
        "cost_input":  0.00000005,
        "cost_output": 0.00000008,
        "max_tokens":  512,
    },
    "medium": {
        "model_id":    "llama-3.3-70b-versatile",
        "label":       "Groq Llama 3.3 70B",
        "cost_input":  0.00000059,
        "cost_output": 0.00000079,
        "max_tokens":  1000,
    },
    "complex": {
        "model_id":    "llama-3.3-70b-versatile",
        "label":       "Groq Llama 3.3 70B (Complex)",
        "cost_input":  0.00000059,
        "cost_output": 0.00000079,
        "max_tokens":  2000,
    },
}

def classify_query(message: str) -> str:
    """Classify query complexity — simple / medium / complex"""
    msg_lower  = message.lower().strip()
    word_count = len(msg_lower.split())

    # ── Rule 1: Very short one-word / greeting → always simple
    if word_count <= 3:
        return "simple"

    # ── Rule 2: Explicit simple pattern match (strict anchored regex)
    for p in SIMPLE_PATTERNS:
        if re.match(p, msg_lower):
            return "simple"

    # ── Rule 3: Complex pattern match — takes priority over word count
    complex_score = sum(1 for p in COMPLEX_PATTERNS if re.search(p, msg_lower))

    # Code blocks / technical syntax → always complex
    if '```' in message or 'def ' in message or 'class ' in message or '->' in message:
        complex_score += 3

    # Long message → bump complexity
    if word_count >= 20:
        complex_score += 2
    elif word_count >= 10:
        complex_score += 1

    # Multiple questions → complex
    question_count = message.count('?')
    if question_count >= 2:
        complex_score += 1

    # ── Decision
    if complex_score >= 2:
        return "complex"
    if complex_score == 1:
        return "medium"

    # ── Rule 4: Fallback by word count
    if word_count <= 6:
        return "simple"
    if word_count <= 15:
        return "medium"
    return "complex"


def get_model_for_query(message: str) -> dict:
    complexity = classify_query(message)
    config = MODEL_CONFIG[complexity].copy()
    config["complexity"] = complexity
    return config


def calculate_routing_savings(
    message: str,
    input_tokens: int,
    output_tokens: int,
    model_used: str
) -> dict:
    complexity      = classify_query(message)
    config          = MODEL_CONFIG[complexity]
    actual          = (input_tokens * config["cost_input"]) + (output_tokens * config["cost_output"])
    baseline_config = MODEL_CONFIG["complex"]
    baseline        = (input_tokens * baseline_config["cost_input"]) + (output_tokens * baseline_config["cost_output"])
    saved           = max(0, baseline - actual)
    savings_pct     = (saved / baseline * 100) if baseline > 0 else 0
    return {
        "complexity":            complexity,
        "model_used":            model_used,
        "actual_cost":           round(actual,   8),
        "baseline_cost":         round(baseline, 8),
        "routing_saved":         round(saved,    8),
        "routing_savings_pct":   round(savings_pct, 2),
    }