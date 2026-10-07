from src.parser import parse_syllabus
from src.semantic_dependency import find_semantic_dependencies
from src.graph import create_dependency_graph, display_graph
from src.learning_path import generate_learning_path


# Step 1: Read the syllabus
topics = parse_syllabus("data/syllabus.txt")


# Step 2: Find AI-based semantic dependencies
dependencies = find_semantic_dependencies(topics)


# Step 3: Get completed topics from the student
print("\nAvailable Topics:")
print("-----------------")

for index, item in enumerate(topics, start=1):
    print(f"{index}. {item['topic']}")

print("\nEnter the numbers of topics you have already completed.")
print("Example: 1,3,5")

completed_input = input("\nCompleted topic numbers: ")

completed_numbers = [
    int(number.strip())
    for number in completed_input.split(",")
    if number.strip().isdigit()
]

completed_topics = [
    topics[number - 1]["topic"]
    for number in completed_numbers
    if 1 <= number <= len(topics)
]


# Step 4: Generate personalized learning path
learning_path = generate_learning_path(
    dependencies,
    completed_topics
)

print("\nPersonalized Learning Path:")
print("---------------------------")

for topic in learning_path:
    print(f"- {topic}")


# Step 5: Create the AI-based dependency graph
graph = create_dependency_graph(dependencies)


# Step 6: Display the graph
display_graph(graph)