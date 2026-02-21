import tiktoken

# Pricing per token (as of 2025)
MODEL_PRICING = {
    "llama3-70b-groq": {
        "input": 0.00000059,   # $0.59 per million tokens
        "output": 0.00000079   # $0.79 per million tokens
    },
    "gpt-4o": {
        "input": 0.0000025,
        "output": 0.000010
    },
    "gpt-4o-mini": {
        "input": 0.00000015,
        "output": 0.0000006
    }
}

def count_tokens(text: str) -> int:
    """Count tokens in a string"""
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))

def count_messages_tokens(messages: list) -> int:
    """Count total tokens in a list of messages"""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
        total += 4  # overhead per message
    return total

def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "llama3-70b-groq"
) -> dict:
    """Calculate actual cost and naive cost"""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["llama3-70b-groq"])
    
    actual_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "actual_cost": round(actual_cost, 8)
    }