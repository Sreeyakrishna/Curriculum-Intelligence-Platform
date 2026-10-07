from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# Load the pretrained Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")


def find_semantic_dependencies(topics, threshold=0.50):
    """
    Identify semantically related curriculum topics
    using Sentence Transformer embeddings.
    """

    topic_names = [item["topic"] for item in topics]

    # Generate semantic embeddings
    embeddings = model.encode(topic_names)

    dependencies = []

    # Compare earlier topics with later topics
    # so the earlier topic can act as a prerequisite
    for i in range(len(topic_names)):

        for j in range(i + 1, len(topic_names)):

            similarity = cosine_similarity(
                [embeddings[i]],
                [embeddings[j]]
            )[0][0]

            if similarity >= threshold:

                dependencies.append({
                    "prerequisite": topic_names[i],
                    "topic": topic_names[j],
                    "similarity": round(float(similarity), 3)
                })

    return dependencies