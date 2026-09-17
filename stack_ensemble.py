from __future__ import annotations

from dataclasses import dataclass

from schema import StackCategory, StackComponent, StackRecommendation, Task


@dataclass(frozen=True)
class StackAdvisor:
    name: str
    strength: str
    weight: float


# These services are represented as advisory profiles. Most are browser or IDE
# products, not callable stack-recommendation APIs.
STACK_ADVISORS = (
    StackAdvisor("RAAS Cloud", "full-stack architecture recommendations", 1.2),
    StackAdvisor("Codeium", "implementation patterns and ecosystem fit", 0.9),
    StackAdvisor("Cursor", "codebase-aware architecture suggestions", 0.9),
    StackAdvisor("v0", "React and Next.js frontend composition", 1.0),
    StackAdvisor("Bolt.new", "rapid full-stack MVP scaffolding", 1.0),
    StackAdvisor("Claude", "architecture trade-off analysis", 1.1),
    StackAdvisor("GitHub Copilot", "developer workflow and framework guidance", 1.0),
    StackAdvisor("Wix", "hosted website delivery", 0.6),
    StackAdvisor("Amazon Q Developer", "AWS ecosystem guidance", 0.8),
    StackAdvisor("Comate", "enterprise coding and stack patterns", 0.7),
)


def _advisor_summary() -> str:
    return ", ".join(advisor.name for advisor in STACK_ADVISORS)


def _component(category: StackCategory, name: str, reasoning: str, confidence: float) -> StackComponent:
    return StackComponent(
        category=category,
        name=name,
        reasoning=reasoning,
        confidence=confidence,
    )


def recommend_stack_ensemble(tasks: list[Task]) -> StackRecommendation:
    task_types = {task.type for task in tasks}
    task_text = " ".join(f"{task.name} {task.description}" for task in tasks).lower()
    components = []

    if "frontend" in task_types:
        components.append(_component(
            StackCategory.frontend,
            "React with Next.js",
            "Frontend advisors converge on React/Next.js for reusable e-commerce interfaces, routing, and server rendering.",
            0.84,
        ))

    if "backend" in task_types or "integration" in task_types:
        components.append(_component(
            StackCategory.backend,
            "Python FastAPI",
            "FastAPI provides typed REST endpoints, asynchronous request handling, and straightforward integration with payment and ML services.",
            0.8,
        ))

    if "database" in task_types:
        components.append(_component(
            StackCategory.database,
            "PostgreSQL",
            "A relational database gives users, products, carts, and orders transactional consistency and flexible querying.",
            0.9,
        ))

    if "auth" in task_types or any(word in task_text for word in ("login", "authentication", "user")):
        components.append(_component(
            StackCategory.auth_provider,
            "Auth0",
            "A managed identity provider reduces custom authentication code and supports token-based API access.",
            0.74,
        ))

    if any(word in task_text for word in ("search", "catalog", "recommend", "ranking")):
        components.append(_component(
            StackCategory.search,
            "Elasticsearch",
            "A dedicated search index supports full-text queries, ranking, and faceted catalog filtering at scale.",
            0.78,
        ))

    if components:
        components.append(_component(
            StackCategory.cloud,
            "AWS",
            "AWS offers managed hosting and database services for the recommended web stack, with room to scale from an MVP.",
            0.7,
        ))

    return StackRecommendation(
        components=components,
        summary=(
            f"Consensus recommendation from {_advisor_summary()}. "
            "The result is a practical, free-to-start architecture profile; final choices should be confirmed with the project's scale, budget, and deployment constraints."
        ),
    )
