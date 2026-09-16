def classify_ml_problem_type(task_name: str, task_description: str, original_requirement: str) -> str:
    text = f"{task_name} {task_description} {original_requirement}".lower()

    if any(k in text for k in ["image", "photo", "vision", "detect object", "classify image"]):
        return "computer_vision"
    if any(k in text for k in ["text", "sentiment", "nlp", "language", "chat", "review classification"]):
        return "nlp_classification"
    if any(k in text for k in ["embedding", "semantic search", "similarity", "vector search"]):
        return "embeddings"
    if any(k in text for k in ["predict a number", "regression", "forecast", "price prediction", "estimate"]):
        return "regression_tabular"

    return "classification_tabular"  # sensible default for recommendation/scoring-type ML tasks