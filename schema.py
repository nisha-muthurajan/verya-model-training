from pydantic import BaseModel, Field, model_validator
from typing import List
from enum import Enum


# ---------- Model 1: Workflow Understanding ----------

class Task(BaseModel):
    id: str = Field(pattern=r"^t[1-9][0-9]*$", description="unique task id, e.g. t1, t2")
    name: str = Field(min_length=1, max_length=200, description="short human-readable task name")
    type: str = Field(description="one of: frontend, backend, database, auth, infra, integration, ml")
    description: str = Field(min_length=1, max_length=2000, description="one-sentence description of what this task does")
    depends_on: List[str] = Field(default_factory=list, min_length=0, description="ids of tasks that must complete first")

    @model_validator(mode="after")
    def validate_dependencies(self):
        if any(not dependency.strip() for dependency in self.depends_on):
            raise ValueError("dependency ids must not be blank")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("dependency ids must be unique")
        if self.id in self.depends_on:
            raise ValueError("a task cannot depend on itself")
        return self


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

    @model_validator(mode="after")
    def validate_safety_consistency(self):
        expected = not any(flaw.severity in (Severity.high, Severity.critical) for flaw in self.flaws)
        if self.is_safe_to_proceed != expected:
            raise ValueError("is_safe_to_proceed must match high or critical flaws")
        return self

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

    @model_validator(mode="after")
    def validate_compatibility_consistency(self):
        expected = not any(issue.severity in (Severity.high, Severity.critical) for issue in self.issues)
        if self.is_compatible != expected:
            raise ValueError("is_compatible must match high or critical issues")
        return self


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
    source: str = Field(default="general", description="'ensemble' or legacy source values - set by code")


class AlgorithmReport(BaseModel):
    decisions: List[AlgorithmDecision] = Field(default_factory=list)


class ModelCandidate(BaseModel):
    name: str
    provider: str
    cost_tier: int = Field(ge=1, le=4, description="1=cheapest, 4=most expensive")
    capability_tier: int = Field(ge=1, le=3, description="1=basic, 3=frontier reasoning")


class ModelSelectionDecision(BaseModel):
    task_id: str
    chosen_model: str
    chosen_provider: str
    required_capability_tier: int = Field(ge=1, le=3)
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

    @model_validator(mode="after")
    def validate_pass_consistency(self):
        expected = not any(issue.severity in (Severity.high, Severity.critical) for issue in self.issues)
        if self.passed != expected:
            raise ValueError("passed must be false when high or critical issues exist")
        return self


class ReputationScore(BaseModel):
    model_name: str
    task_type: str
    trust_score: float = Field(ge=0, le=1, description="Bayesian estimate of success probability")
    successes: int = Field(ge=0)
    failures: int = Field(ge=0)
    total_observations: int = Field(ge=0)
    confidence_level: str = Field(description="'unproven' (<5 obs), 'emerging' (5-20), 'established' (20+)")

    @model_validator(mode="after")
    def validate_observation_total(self):
        if self.total_observations != self.successes + self.failures:
            raise ValueError("total_observations must equal successes plus failures")
        return self


class ReputationUpdateEvent(BaseModel):
    model_name: str
    task_type: str
    succeeded: bool
    source: str = Field(description="what generated this signal: 'verification', 'human_override', 'human_accept'")
    task_id: str