from schema import Task, AlgorithmDecision
from algorithm_ensemble import recommend_ml_algorithm as recommend_ensemble_ml_algorithm

def recommend_ml_algorithm(task_id: str, task_description: str, problem_type: str, constraints: str = "") -> AlgorithmDecision:
  """Compatibility wrapper for the data-free ensemble ML selector."""
  task = Task(
    id=task_id,
    name="ML task",
    type="ml",
    description=task_description,
    )
  return recommend_ensemble_ml_algorithm(task, problem_type, constraints)