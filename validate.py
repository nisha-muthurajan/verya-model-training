import networkx as nx
from schema import WorkflowGraph


def validate_graph(graph: WorkflowGraph) -> list[str]:
    """Returns a list of problems found. Empty list = valid."""
    errors = []
    ids = [t.id for t in graph.tasks]

    if len(ids) != len(set(ids)):
        errors.append("duplicate task ids found")

    id_set = set(ids)
    for t in graph.tasks:
        for dep in t.depends_on:
            if dep not in id_set:
                errors.append(f"task {t.id} depends on unknown task {dep}")

    g = nx.DiGraph()
    for t in graph.tasks:
        g.add_node(t.id)
        for dep in t.depends_on:
            g.add_edge(dep, t.id)
    if not nx.is_directed_acyclic_graph(g):
        errors.append("dependency cycle detected")

    return errors