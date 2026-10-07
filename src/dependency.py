import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .parser import parse_syllabus


# =========================================================
# AI MODEL
# =========================================================

model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================================================
# TEXT UTILITIES
# =========================================================

STOP_WORDS = {
    "the", "and", "for", "with", "from",
    "into", "using", "based", "data",
    "advanced"
}


def clean_topic_name(topic):
    """Clean a syllabus topic name."""

    topic = str(topic).strip()

    topic = re.sub(
        r"^[\-\•\●\▪\◦\*]+\s*",
        "",
        topic
    )

    topic = re.sub(
        r"\s+",
        " ",
        topic
    )

    return topic.strip()


def get_words(text):
    """Return meaningful words from a topic."""

    words = re.findall(
        r"[a-zA-Z]{3,}",
        text.lower()
    )

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


# =========================================================
# SIBLING TOPIC DETECTION
# =========================================================

def is_sibling_topic(topic_a, topic_b):
    """
    Detect topics that are parallel concepts rather
    than prerequisite relationships.
    """

    a = topic_a.lower()
    b = topic_b.lower()

    sibling_pairs = [
        ("supervised", "unsupervised"),
        ("linear regression", "logistic regression"),
        ("binary tree", "binary search tree"),
    ]

    for first, second in sibling_pairs:

        if (
            first in a and second in b
        ) or (
            second in a and first in b
        ):
            return True

    return False


# =========================================================
# FOUNDATION / ADVANCED CUES
# =========================================================

FOUNDATION_WORDS = {
    "introduction",
    "intro",
    "basic",
    "basics",
    "fundamentals",
    "fundamental",
    "concepts",
    "terminology",
    "overview",
    "principles",
    "algorithm",
    "algorithms"
}


ADVANCED_WORDS = {
    "advanced",
    "applications",
    "application",
    "optimization",
    "implementation",
    "evaluation",
    "classification",
    "analysis",
    "multiple"
}


def foundation_score(topic):
    """
    Give a score to topics that appear foundational.
    """

    words = get_words(topic)

    return len(
        words.intersection(
            FOUNDATION_WORDS
        )
    )


def advanced_score(topic):
    """
    Give a score to topics that appear more advanced
    or application-oriented.
    """

    words = get_words(topic)

    return len(
        words.intersection(
            ADVANCED_WORDS
        )
    )


# =========================================================
# UNIT / SEMESTER CONVERSION
# =========================================================

def unit_number(value):

    if value is None:
        return None

    value = str(value).strip()

    roman = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8
    }

    if value.upper() in roman:
        return roman[value.upper()]

    try:
        return int(value)

    except (ValueError, TypeError):
        return None


# =========================================================
# DEPENDENCY INFERENCE
# =========================================================

def infer_dependencies(topics):

    """
    Infer likely prerequisite relationships.

    The system combines:

    1. AI semantic similarity
    2. Syllabus order
    3. Unit progression
    4. Topic-word relationships
    5. Foundation/advanced terminology
    6. Sibling-topic detection

    Semantic similarity alone is NOT treated as
    a prerequisite.
    """

    # -----------------------------------------------------
    # PREPARE TOPICS
    # -----------------------------------------------------

    cleaned_topics = []

    for item in topics:

        topic = clean_topic_name(
            item.get("topic", "")
        )

        if not topic:
            continue

        cleaned_topics.append({
            "topic": topic,
            "unit": unit_number(
                item.get("unit")
            ),
            "semester": unit_number(
                item.get("semester")
            )
        })


    # -----------------------------------------------------
    # NEED AT LEAST TWO TOPICS
    # -----------------------------------------------------

    if len(cleaned_topics) < 2:
        return []


    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    unique_topics = []

    seen_names = set()

    for item in cleaned_topics:

        name_key = item["topic"].lower()

        if name_key not in seen_names:

            unique_topics.append(item)

            seen_names.add(name_key)

    cleaned_topics = unique_topics


    # -----------------------------------------------------
    # CREATE AI EMBEDDINGS
    # -----------------------------------------------------

    topic_names = [
        item["topic"]
        for item in cleaned_topics
    ]

    embeddings = model.encode(
        topic_names,
        convert_to_numpy=True
    )

    similarity_matrix = cosine_similarity(
        embeddings
    )


    # =====================================================
    # FIND CANDIDATE RELATIONSHIPS
    # =====================================================

    candidates = []

    for current_index in range(
        len(cleaned_topics)
    ):

        current = cleaned_topics[
            current_index
        ]

        current_name = current["topic"]


        # -------------------------------------------------
        # ONLY EARLIER TOPICS CAN BE PREREQUISITES
        # -------------------------------------------------

        for previous_index in range(
            current_index
        ):

            previous = cleaned_topics[
                previous_index
            ]

            previous_name = previous["topic"]


            # -------------------------------------------------
            # IDENTICAL TOPICS
            # -------------------------------------------------

            if (
                previous_name.lower()
                == current_name.lower()
            ):
                continue


            # -------------------------------------------------
            # SIBLING TOPICS
            # -------------------------------------------------

            if is_sibling_topic(
                previous_name,
                current_name
            ):
                continue


            # -------------------------------------------------
            # SEMANTIC SIMILARITY
            # -------------------------------------------------

            semantic_similarity = float(
                similarity_matrix[
                    previous_index
                ][
                    current_index
                ]
            )


            # -------------------------------------------------
            # WORD RELATIONSHIP
            # -------------------------------------------------

            previous_words = get_words(
                previous_name
            )

            current_words = get_words(
                current_name
            )

            shared_words = (
                previous_words
                .intersection(
                    current_words
                )
            )


            # -------------------------------------------------
            # CONCEPT CONTAINMENT
            # -------------------------------------------------

            concept_containment = (
                len(previous_words) > 0
                and previous_words.issubset(
                    current_words
                )
            )


            # -------------------------------------------------
            # UNIT INFORMATION
            # -------------------------------------------------

            same_unit = (
                previous["unit"] is not None
                and current["unit"] is not None
                and previous["unit"]
                == current["unit"]
            )

            previous_unit = False

            if (
                previous["unit"] is not None
                and current["unit"] is not None
            ):

                previous_unit = (
                    previous["unit"]
                    < current["unit"]
                )


            # -------------------------------------------------
            # SEMESTER INFORMATION
            # -------------------------------------------------

            same_semester = (
                previous["semester"] is not None
                and current["semester"] is not None
                and previous["semester"]
                == current["semester"]
            )


            # -------------------------------------------------
            # TOPIC DISTANCE
            # -------------------------------------------------

            distance = (
                current_index
                - previous_index
            )

            if distance <= 1:

                position_score = 1.0

            elif distance <= 3:

                position_score = 0.75

            elif distance <= 6:

                position_score = 0.45

            else:

                position_score = 0.15


            # -------------------------------------------------
            # STRUCTURAL SCORE
            # -------------------------------------------------

            structural_score = 0.0

            if same_unit:
                structural_score += 0.35

            if previous_unit:
                structural_score += 0.25

            if same_semester:
                structural_score += 0.15

            if concept_containment:
                structural_score += 0.40

            if len(shared_words) > 0:
                structural_score += 0.10


            # -------------------------------------------------
            # FOUNDATION → ADVANCED PROGRESSION
            # -------------------------------------------------

            previous_foundation = (
                foundation_score(
                    previous_name
                )
            )

            current_advanced = (
                advanced_score(
                    current_name
                )
            )

            progression_bonus = 0.0

            if (
                previous_foundation > 0
                and current_advanced > 0
            ):
                progression_bonus = 0.15


            # -------------------------------------------------
            # COMBINED CONFIDENCE SCORE
            # -------------------------------------------------

            score = (
                semantic_similarity * 0.50
                + position_score * 0.15
                + structural_score * 0.25
                + progression_bonus * 0.10
            )


            # =================================================
            # STRONG RELATIONSHIP RULES
            # =================================================

            strong_relationship = False


            # -------------------------------------------------
            # RULE 1
            # Strong semantic + structural relationship
            # -------------------------------------------------

            if (
                semantic_similarity >= 0.68
                and structural_score >= 0.25
            ):

                strong_relationship = True


            # -------------------------------------------------
            # RULE 2
            # Direct concept expansion
            # -------------------------------------------------

            elif (
                concept_containment
                and semantic_similarity >= 0.55
            ):

                strong_relationship = True


            # -------------------------------------------------
            # RULE 3
            # Nearby topics in same unit
            # -------------------------------------------------

            elif (
                same_unit
                and distance <= 2
                and semantic_similarity >= 0.52
            ):

                strong_relationship = True


            # -------------------------------------------------
            # RULE 4
            # Earlier unit → later unit
            # -------------------------------------------------

            elif (
                previous_unit
                and semantic_similarity >= 0.62
            ):

                strong_relationship = True


            # -------------------------------------------------
            # RULE 5
            # FOUNDATIONAL TOPIC → LATER CONCEPT
            # -------------------------------------------------

            elif (
                previous_foundation > 0
                and distance <= 3
                and semantic_similarity >= 0.50
            ):

                strong_relationship = True


            # -------------------------------------------------
            # SAVE CANDIDATE
            # -------------------------------------------------

            if strong_relationship:

                candidates.append({

                    "prerequisite":
                        previous_name,

                    "topic":
                        current_name,

                    "score":
                        round(
                            score,
                            3
                        ),

                    "similarity":
                        round(
                            semantic_similarity,
                            3
                        ),

                    "distance":
                        distance
                })


    # =====================================================
    # GROUP RELATIONSHIPS BY DESTINATION TOPIC
    # =====================================================

    topic_candidates = {}

    for candidate in candidates:

        topic = candidate["topic"]

        if topic not in topic_candidates:

            topic_candidates[topic] = []

        topic_candidates[
            topic
        ].append(candidate)


    # =====================================================
    # SELECT BEST RELATIONSHIPS
    # =====================================================

    final_dependencies = []

    for topic, candidate_list in (
        topic_candidates.items()
    ):

        candidate_list.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # Keep at most 2 strong prerequisites
        # for each topic.
        selected = candidate_list[:2]

        for candidate in selected:

            final_dependencies.append({

                "prerequisite":
                    candidate["prerequisite"],

                "topic":
                    candidate["topic"],

                "score":
                    candidate["score"],

                "similarity":
                    candidate["similarity"],

                "reason":
                    (
                        "Detected using semantic "
                        "similarity, syllabus order, "
                        "and curriculum structure."
                    )
            })


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    unique_dependencies = []

    seen = set()

    for dependency in final_dependencies:

        pair = (
            dependency["prerequisite"],
            dependency["topic"]
        )

        if pair not in seen:

            unique_dependencies.append(
                dependency
            )

            seen.add(pair)


    return unique_dependencies


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def build_dependencies(topics):

    """
    Compatibility wrapper used by the Streamlit app.
    """

    return infer_dependencies(topics)


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    topics = parse_syllabus(
        "data/syllabus.txt"
    )

    dependencies = infer_dependencies(
        topics
    )

    print(
        "\nAI-Based Curriculum Dependency Analysis"
    )

    print(
        "========================================="
    )

    for dependency in dependencies:

        print(
            f"{dependency['prerequisite']} "
            f"--> "
            f"{dependency['topic']} "
            f"| Score: "
            f"{dependency['score']}"
        )

    print(
        f"\nTotal inferred dependencies: "
        f"{len(dependencies)}"
    )