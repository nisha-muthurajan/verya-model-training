MODEL_CATALOG = [
    {"name": "deepseek-chat", "provider": "deepseek", "cost_tier": 1, "capability_tier": 2,
     "good_for": ["coding", "automation", "multi-step workflows"]},
    {"name": "kimi-k2", "provider": "moonshot", "cost_tier": 2, "capability_tier": 3,
     "good_for": ["agentic workflows", "tool use", "long context"]},
    {"name": "glm-4.5", "provider": "zai", "cost_tier": 2, "capability_tier": 3,
     "good_for": ["reasoning", "routing", "structured workflows"]},
    {"name": "Qwen3-235B-A22B", "provider": "qwen", "cost_tier": 2, "capability_tier": 3,
     "good_for": ["multilingual", "enterprise workflows", "long context"]},
    {"name": "Llama-4-Scout", "provider": "meta", "cost_tier": 1, "capability_tier": 2,
     "good_for": ["long documents", "RAG", "general workflows"]},
    {"name": "mistral-large-latest", "provider": "mistral", "cost_tier": 2, "capability_tier": 3,
     "good_for": ["business workflows", "European deployments", "reasoning"]},
    {"name": "claude-sonnet", "provider": "anthropic", "cost_tier": 3, "capability_tier": 3,
     "good_for": ["workflow analysis", "clear explanations", "complex reasoning"]},
]


def get_catalog():
    return MODEL_CATALOG