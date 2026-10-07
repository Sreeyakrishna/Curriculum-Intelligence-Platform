import networkx as nx
import matplotlib.pyplot as plt


def create_dependency_graph(dependencies):
    graph = nx.DiGraph()

    for dependency in dependencies:
        prerequisite = dependency["prerequisite"]
        topic = dependency["topic"]

        graph.add_edge(prerequisite, topic)

    return graph


def display_graph(graph):
    plt.figure(figsize=(14, 9))

    position = nx.spring_layout(graph, seed=42)

    nx.draw(
        graph,
        position,
        with_labels=True,
        node_size=3000,
        node_color="lightblue",
        font_size=9,
        arrows=True,
        edge_color="gray"
    )

    plt.title("AI-Based Curriculum Dependency Graph")
    plt.tight_layout()
    plt.show()