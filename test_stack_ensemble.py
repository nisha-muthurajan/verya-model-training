from stack_ensemble import STACK_ADVISORS, recommend_stack_ensemble
from schema import Task, StackCategory


def test_stack_recommendation_uses_all_advisor_profiles():
    tasks = [
        Task(id="t1", name="Users", type="database", description="Store users"),
        Task(id="t2", name="Authentication", type="auth", description="Login and signup"),
        Task(id="t3", name="Product Search API", type="backend", description="Search a product catalog"),
        Task(id="t4", name="Frontend", type="frontend", description="Render the store"),
    ]

    recommendation = recommend_stack_ensemble(tasks)
    categories = {component.category for component in recommendation.components}

    assert len(STACK_ADVISORS) == 10
    assert StackCategory.frontend in categories
    assert StackCategory.backend in categories
    assert StackCategory.database in categories
    assert StackCategory.auth_provider in categories
    assert StackCategory.search in categories
    assert StackCategory.cloud in categories
    assert all(0 <= component.confidence <= 1 for component in recommendation.components)
