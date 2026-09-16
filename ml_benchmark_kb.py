ML_KNOWLEDGE_BASE = {
    "classification_tabular": [
        {"name": "XGBoost", "accuracy": "high", "train_time": "fast", "inference": "very fast", "memory": "low", "notes": "Best general-purpose choice for structured/tabular data"},
        {"name": "Random Forest", "accuracy": "high", "train_time": "moderate", "inference": "fast", "memory": "moderate", "notes": "Robust, less tuning needed, slightly slower inference than XGBoost"},
        {"name": "Logistic Regression", "accuracy": "moderate", "train_time": "very fast", "inference": "instant", "memory": "very low", "notes": "Best when interpretability or extreme low latency matters more than peak accuracy"},
        {"name": "LightGBM", "accuracy": "high", "train_time": "very fast", "inference": "very fast", "memory": "low", "notes": "Best for very large tabular datasets, faster training than XGBoost"},
    ],
    "regression_tabular": [
        {"name": "XGBoost Regressor", "accuracy": "high", "train_time": "fast", "inference": "very fast", "memory": "low", "notes": "Strong default for structured numeric prediction"},
        {"name": "Linear Regression", "accuracy": "moderate", "train_time": "very fast", "inference": "instant", "memory": "very low", "notes": "Best for interpretability and very low latency"},
        {"name": "LightGBM Regressor", "accuracy": "high", "train_time": "very fast", "inference": "very fast", "memory": "low", "notes": "Best for large datasets"},
    ],
    "nlp_classification": [
        {"name": "DistilBERT", "accuracy": "good", "train_time": "moderate", "inference": "fast", "memory": "low", "notes": "Best balance of speed and accuracy for most NLP classification"},
        {"name": "BERT-base", "accuracy": "high", "train_time": "slow", "inference": "moderate", "memory": "high", "notes": "Higher accuracy ceiling, costlier to serve"},
        {"name": "MiniLM", "accuracy": "moderate", "train_time": "fast", "inference": "very fast", "memory": "very low", "notes": "Best for tight latency/memory budgets"},
    ],
    "computer_vision": [
        {"name": "MobileNet", "accuracy": "moderate", "train_time": "fast", "inference": "very fast", "memory": "very low", "notes": "Best for edge/mobile/CPU-constrained deployment"},
        {"name": "EfficientNet", "accuracy": "high", "train_time": "moderate", "inference": "fast", "memory": "moderate", "notes": "Good accuracy-to-cost ratio"},
        {"name": "ResNet-50", "accuracy": "high", "train_time": "slow", "inference": "moderate", "memory": "high", "notes": "Strong baseline, heavier to serve"},
    ],
    "embeddings": [
        {"name": "MiniLM (sentence-transformers)", "accuracy": "good", "inference": "very fast", "memory": "very low", "notes": "Best default for semantic search/embeddings at low cost"},
        {"name": "BGE-large", "accuracy": "high", "inference": "moderate", "memory": "moderate", "notes": "Higher retrieval accuracy, costlier per query"},
        {"name": "E5-base", "accuracy": "high", "inference": "fast", "memory": "low", "notes": "Strong middle ground"},
    ],
}

def get_relevant_benchmarks(problem_type: str) -> list[dict]:
    return ML_KNOWLEDGE_BASE.get(problem_type, [])