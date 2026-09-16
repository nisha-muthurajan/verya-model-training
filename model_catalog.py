MODEL_CATALOG = [
    {"name": "llama-3.1-8b-instant", "provider": "groq", "cost_tier": 1, "capability_tier": 1,
     "good_for": ["simple formatting", "boilerplate", "short classification", "simple lookups"]},
    {"name": "llama-3.3-70b-versatile", "provider": "groq", "cost_tier": 2, "capability_tier": 2,
     "good_for": ["general reasoning", "multi-step tasks", "moderate complexity code/logic"]},
    {"name": "gemini-2.5-flash", "provider": "gemini", "cost_tier": 2, "capability_tier": 2,
     "good_for": ["fast structured output", "moderate reasoning", "cheap at scale"]},
    {"name": "llama-3.1-405b-reasoning", "provider": "groq", "cost_tier": 2, "capability_tier": 3,
     "good_for": ["complex reasoning", "high-stakes accuracy", "near-frontier capability at free-tier cost"]},
    {"name": "gemini-2.5-pro", "provider": "gemini", "cost_tier": 4, "capability_tier": 3,
     "good_for": ["complex reasoning", "long context", "when Groq rate limits are a concern"]},
]


def get_catalog():
    return MODEL_CATALOG