from schema import Task, WorkflowGraph
from validate import validate_graph


def test_valid_dependency_graph_is_accepted():
    graph = WorkflowGraph(tasks=[
        Task(id="t1", name="Users", type="database", description="Store users"),
        Task(id="t2", name="API", type="backend", description="Serve users", depends_on=["t1"]),
    ])

    assert validate_graph(graph) == []


def test_empty_unknown_and_cyclic_graphs_are_rejected():
    assert validate_graph(WorkflowGraph(tasks=[])) == ["workflow graph must contain at least one task"]
    unknown = WorkflowGraph(tasks=[Task(id="t1", name="API", type="backend", description="Serve", depends_on=["t9"])])
    assert validate_graph(unknown) == ["task t1 depends on unknown task t9"]
    cycle = WorkflowGraph(tasks=[
        Task(id="t1", name="One", type="backend", description="One", depends_on=["t2"]),
        Task(id="t2", name="Two", type="backend", description="Two", depends_on=["t1"]),
    ])
    assert validate_graph(cycle) == ["dependency cycle detected"]