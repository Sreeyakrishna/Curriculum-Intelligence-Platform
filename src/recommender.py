# =========================================================
# PERSONALIZED LEARNING PATH RECOMMENDER
# =========================================================


# =========================================================
# FOUNDATION TOPIC DETECTION
# =========================================================

FOUNDATION_WORDS = {
    "introduction",
    "intro",
    "basic",
    "basics",
    "fundamental",
    "fundamentals",
    "concept",
    "concepts",
    "terminology",
    "overview",
    "algorithm",
    "algorithms"
}


def is_foundation_topic(topic):
    """
    Identify whether a topic appears to be foundational.
    """

    topic_lower = topic.lower()

    for word in FOUNDATION_WORDS:

        if word in topic_lower:
            return True

    return False


# =========================================================
# PERSONALIZED LEARNING PATH
# =========================================================

def recommend_learning_path(
    topics,
    dependencies,
    completed_topics
):
    """
    Generate a personalized learning path.

    The system considers:

    1. Completed topics
    2. Detected prerequisite relationships
    3. Syllabus order
    4. Foundational topics

    The system recommends only topics that are
    reasonably ready to be studied next.
    """

    # -----------------------------------------------------
    # NORMALIZE COMPLETED TOPICS
    # -----------------------------------------------------

    completed_set = {
        topic.strip().lower()
        for topic in completed_topics
    }


    # -----------------------------------------------------
    # CREATE PREREQUISITE MAP
    # -----------------------------------------------------

    prerequisites = {}

    for dependency in dependencies:

        topic = dependency["topic"]
        prerequisite = dependency["prerequisite"]

        if topic not in prerequisites:

            prerequisites[topic] = []

        prerequisites[topic].append(
            dependency
        )


    # -----------------------------------------------------
    # REMOVE DUPLICATE PREREQUISITES
    # -----------------------------------------------------

    for topic in prerequisites:

        unique = {}

        for dependency in prerequisites[topic]:

            prerequisite = dependency[
                "prerequisite"
            ]

            if prerequisite not in unique:

                unique[prerequisite] = dependency

        prerequisites[topic] = list(
            unique.values()
        )


    # -----------------------------------------------------
    # CREATE TOPIC ORDER
    # -----------------------------------------------------

    topic_order = {}

    for index, item in enumerate(topics):

        topic_order[
            item["topic"]
        ] = index


    # =====================================================
    # CASE 1 — NOTHING COMPLETED
    # =====================================================

    if not completed_set:

        starting_topics = []

        for item in topics:

            topic = item["topic"]

            required = prerequisites.get(
                topic,
                []
            )

            # ---------------------------------------------
            # Topic has no detected prerequisite
            # ---------------------------------------------

            if not required:

                score = 0

                # Earlier syllabus topics are preferred
                position = topic_order.get(
                    topic,
                    9999
                )

                if position <= 5:

                    score += 3

                elif position <= 10:

                    score += 2

                else:

                    score += 1


                # Foundation topics get extra priority
                if is_foundation_topic(topic):

                    score += 3


                starting_topics.append({

                    "topic": topic,

                    "score": score,

                    "reason":
                        "This topic has no detected "
                        "prerequisite and is suitable "
                        "as an initial learning topic."

                })


        # -------------------------------------------------
        # Sort starting topics
        # -------------------------------------------------

        starting_topics.sort(
            key=lambda x: (
                -x["score"],
                topic_order.get(
                    x["topic"],
                    9999
                )
            )
        )


        # -------------------------------------------------
        # Return only a small number of starting topics
        # -------------------------------------------------

        return [
            {
                "topic": item["topic"],
                "reason": item["reason"]
            }
            for item in starting_topics[:5]
        ]


    # =====================================================
    # CASE 2 — SOME TOPICS COMPLETED
    # =====================================================

    recommendations = []


    for item in topics:

        topic = item["topic"]

        topic_key = topic.strip().lower()


        # -------------------------------------------------
        # Skip completed topics
        # -------------------------------------------------

        if topic_key in completed_set:

            continue


        required = prerequisites.get(
            topic,
            []
        )


        # -------------------------------------------------
        # NO DETECTED PREREQUISITES
        # -------------------------------------------------

        if not required:

            # Find whether this topic is close to
            # the learner's current syllabus position.

            topic_position = topic_order.get(
                topic,
                9999
            )

            completed_positions = []

            for completed in topics:

                if (
                    completed["topic"]
                    .strip()
                    .lower()
                    in completed_set
                ):

                    completed_positions.append(
                        topic_order.get(
                            completed["topic"],
                            9999
                        )
                    )


            if completed_positions:

                latest_completed_position = max(
                    completed_positions
                )

                # Recommend independent topics that
                # occur shortly after completed topics.
                if (
                    topic_position
                    <= latest_completed_position + 5
                ):

                    recommendations.append({

                        "topic": topic,

                        "score": 2,

                        "reason":
                            "This topic has no detected "
                            "prerequisite and is close to "
                            "your current learning position."

                    })

            continue


        # -------------------------------------------------
        # CHECK PREREQUISITES
        # -------------------------------------------------

        completed_required = []
        incomplete_required = []


        for dependency in required:

            prerequisite = dependency[
                "prerequisite"
            ]

            prerequisite_key = (
                prerequisite.strip().lower()
            )


            if (
                prerequisite_key
                in completed_set
            ):

                completed_required.append(
                    dependency
                )

            else:

                incomplete_required.append(
                    dependency
                )


        # -------------------------------------------------
        # ALL PREREQUISITES COMPLETED
        # -------------------------------------------------

        if (
            len(incomplete_required) == 0
            and len(completed_required) > 0
        ):

            prerequisite_names = [

                dependency["prerequisite"]

                for dependency
                in completed_required

            ]


            # Calculate recommendation score

            score = 5

            if is_foundation_topic(topic):

                score += 1


            recommendations.append({

                "topic": topic,

                "score": score,

                "reason":
                    "You have completed all detected "
                    "prerequisites: "
                    + ", ".join(
                        prerequisite_names
                    )
                    + ". This topic is ready "
                    "to be studied next."

            })


    # =====================================================
    # SORT RECOMMENDATIONS
    # =====================================================

    recommendations.sort(
        key=lambda x: (
            -x["score"],
            topic_order.get(
                x["topic"],
                9999
            )
        )
    )


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    unique_recommendations = []

    seen = set()


    for recommendation in recommendations:

        topic = recommendation["topic"]

        if topic not in seen:

            unique_recommendations.append(
                {
                    "topic": topic,
                    "reason":
                        recommendation["reason"]
                }
            )

            seen.add(topic)


    # -----------------------------------------------------
    # Return top recommendations
    # -----------------------------------------------------

    return unique_recommendations[:5]