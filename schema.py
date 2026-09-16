from pydantic import BaseModel, Field
from typing import List
from enum import Enum


# ---------- Model 1: Workflow Understanding ----------

class Task(BaseModel):
    id: str = Field(description="unique task id, e.g. t1, t2")
    name: str = Field(description="short human-readable task name")
    type: str = Field(description="one of: frontend, backend, database, auth, infra, integration, ml")
    description: str = Field(description="one-sentence description of what this task does")
    depends_on: List[str] = Field(default_factory=list, description="ids of tasks that must complete first")


class WorkflowGraph(BaseModel):
    tasks: List[Task]


# ---------- Model 2: Flaw Detection ----------

class FlawType(str, Enum):
    security = "security"
    architecture = "architecture"
    performance = "performance"
    cost = "cost"
    logic = "logic"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Flaw(BaseModel):
    task_ids: List[str] = Field(description="which task(s) this flaw affects")
    type: FlawType
    severity: Severity
    description: str = Field(description="what the problem is")
    suggested_fix: str = Field(description="how to fix it")


class FlawReport(BaseModel):
    flaws: List[Flaw] = Field(default_factory=list)
    is_safe_to_proceed: bool = Field(description="false if any critical/high severity flaw exists")

# Add these to the bottom of schema.py

class StackCategory(str, Enum):
    frontend = "frontend"
    backend = "backend"
    database = "database"
    cache = "cache"
    cloud = "cloud"
    auth_provider = "auth_provider"
    search = "search"
    messaging = "messaging"
    ml_framework = "ml_framework"
    infra = "infra"


# ---------- Stack Recommendation (no stack given) ----------

class StackComponent(BaseModel):
    category: StackCategory
    name: str = Field(description="e.g. React, PostgreSQL, AWS")
    reasoning: str = Field(description="why this fits the given tasks")
    confidence: float = Field(ge=0, le=1, description="0-1, how sure the model is this is the best pick")


class StackRecommendation(BaseModel):
    components: List[StackComponent]
    summary: str = Field(description="one-paragraph overview of the recommended stack")


# ---------- Stack Validation (user already gave a stack) ----------

class StackValidationIssue(BaseModel):
    category: StackCategory
    issue: str
    severity: Severity
    suggested_alternative: str = Field(default="")


class StackValidationReport(BaseModel):
    issues: List[StackValidationIssue] = Field(default_factory=list)
    is_compatible: bool = Field(description="false if any high/critical issue exists")


class AlgorithmCandidate(BaseModel):
    name: str
    pros: str
    cons: str


class AlgorithmDecision(BaseModel):
    task_id: str
    chosen_algorithm: str = Field(description="the recommended approach")
    reasoning: str = Field(description="why this fits the task's actual constraints")
    confidence: float = Field(ge=0, le=1)
    alternatives_considered: List[AlgorithmCandidate]
    requires_human_tiebreak: bool
    assumed_constraints: str = Field(default="")
    problem_type: str = Field(default="", description="only set for ML tasks, e.g. classification_tabular, nlp_classification")
    source: str = Field(default="general", description="'general' or 'ml_benchmark' - set by code, never by the LLM")


class AlgorithmReport(BaseModel):
    decisions: List[AlgorithmDecision] = Field(default_factory=list)


class ModelCandidate(BaseModel):
    name: str
    provider: str
    cost_tier: int = Field(description="1=cheapest, 4=most expensive")
    capability_tier: int = Field(description="1=basic, 3=frontier reasoning")


class ModelSelectionDecision(BaseModel):
    task_id: str
    chosen_model: str
    chosen_provider: str
    required_capability_tier: int
    reasoning: str
    confidence: float = Field(ge=0, le=1)
    alternatives_considered: List[ModelCandidate]
    requires_human_tiebreak: bool
    complexity_breakdown: dict = Field(default_factory=dict, description="the scored signals that led to this decision")


class ModelSelectionReport(BaseModel):
    decisions: List[ModelSelectionDecision]

class RiskPrediction(BaseModel):
    task_id: str
    failure_probability: float = Field(ge=0, le=1)
    risk_factors: List[str] = Field(description="which signals drove this score")
    severity_if_failed: str = Field(description="low, medium, high, critical")
    source: str = Field(default="heuristic", description="'heuristic' (Phase 1) or 'trained_model' (Phase 2)")


class RiskReport(BaseModel):
    predictions: List[RiskPrediction]



class IssueCategory(str, Enum):
    contradiction = "contradiction"
    error = "error"
    policy_violation = "policy_violation"
    security = "security"


class VerificationIssue(BaseModel):
    category: IssueCategory
    description: str
    evidence: str = Field(description="the specific part of the output that triggered this")
    severity: Severity


class VerificationReport(BaseModel):
    task_id: str
    passed: bool
    issues: List[VerificationIssue] = Field(default_factory=list)
    verifier_agreement: float = Field(ge=0, le=1, description="1.0 = both verifiers fully agreed, lower = they disagreed")
    requires_human_review: bool


class ReputationScore(BaseModel):
    model_name: str
    task_type: str
    trust_score: float = Field(ge=0, le=1, description="Bayesian estimate of success probability")
    successes: int
    failures: int
    total_observations: int
    confidence_level: str = Field(description="'unproven' (<5 obs), 'emerging' (5-20), 'established' (20+)")


class ReputationUpdateEvent(BaseModel):
    model_name: str
    task_type: str
    succeeded: bool
    source: str = Field(description="what generated this signal: 'verification', 'human_override', 'human_accept'")
    task_id: str