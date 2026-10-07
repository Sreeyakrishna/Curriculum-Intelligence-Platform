import networkx as nx


def generate_learning_path(dependencies, completed_topics=None):
    if completed_topics is None:
        completed_topics = []

    graph = nx.DiGraph()

    # Add prerequisite relationships
    for dependency in dependencies:
        prerequisite = dependency["prerequisite"]
        topic = dependency["topic"]

        graph.add_edge(prerequisite, topic)

    # Remove topics already completed
    remaining_topics = [
        topic for topic in graph.nodes
        if topic not in completed_topics
    ]

    # Find topics whose prerequisites are completed
    recommended_topics = []

    for topic in remaining_topics:
        prerequisites = list(graph.predecessors(topic))

        if all(
            prerequisite in completed_topics
            for prerequisite in prerequisites
        ):
            recommended_topics.append(topic)

    return recommended_topics


if __name__ == "__main__":
    print("Personalized Learning Path Module")