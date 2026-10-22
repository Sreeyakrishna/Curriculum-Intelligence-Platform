# =========================================================
# PERSONALIZED LEARNING PATH RECOMMENDER
# =========================================================

FOUNDATION_PHRASES = (
    "introduction",
    "introduction to",
    "basics of",
    "basic concepts",
    "fundamentals of",
    "fundamental concepts",
    "overview of",
    "preliminaries",
    "definition of",
    "algorithm analysis",
    "complexity analysis",
    "time complexity",
    "space complexity",
    "basic principles",
    "core concepts",
)

ADVANCED_PHRASES = (
    "advanced",
    "string matching",
    "convex hull",
    "network flow",
    "approximation algorithm",
    "randomized algorithm",
    "advanced optimization",
)

FOUNDATION_WORDS = {
    "introduction",
    "intro",
    "basic",
    "basics",
    "fundamental",
    "fundamentals",
    "overview",
    "terminology",
    "definition",
    "definitions",
    "preliminaries",
}


def is_foundation_topic(topic):
    """Return True when a topic appears introductory."""
    name = str(topic).strip().lower()

    if any(phrase in name for phrase in ADVANCED_PHRASES):
        return False

    if any(phrase in name for phrase in FOUNDATION_PHRASES):
        return True

    return any(
        word in name.split()
        for word in FOUNDATION_WORDS
    )


def is_advanced_topic(topic):
    """Identify topics that should generally come later."""
    name = str(topic).strip().lower()

    return any(
        phrase in name
        for phrase in ADVANCED_PHRASES
    )


def recommend_learning_path(
    topics,
    dependencies,
    completed_topics,
    selected_course=None,
):
    """
    Recommend a learning path for one course.

    Topics with no detected prerequisites are treated as possible
    starting points, not as proof that they are beginner topics.
    """

    # -----------------------------------------------------
    # 1. FILTER TOPICS
    # -----------------------------------------------------

    filtered_topics = []

    for item in topics:
        topic = str(item.get("topic", "")).strip()

        if not topic:
            continue

        subject = str(item.get("subject", "")).strip()

        if selected_course and subject != selected_course:
            continue

        filtered_topics.append(item)

    if not filtered_topics:
        return []

    topic_names = [
        str(item["topic"]).strip()
        for item in filtered_topics
    ]

    valid_names = set(topic_names)

    topic_order = {
        topic: index
        for index, topic in enumerate(topic_names)
    }

    completed_set = {
        str(topic).strip().casefold()
        for topic in (completed_topics or [])
    }

    completed_positions = [
        topic_order[topic]
        for topic in topic_names
        if topic.casefold() in completed_set
    ]

    # -----------------------------------------------------
    # 2. BUILD PREREQUISITE MAP
    # -----------------------------------------------------

    prerequisites = {
        topic: []
        for topic in valid_names
    }

    for dependency in dependencies or []:
        topic = str(dependency.get("topic", "")).strip()
        prerequisite = str(
            dependency.get("prerequisite", "")
        ).strip()

        if (
            topic in valid_names
            and prerequisite in valid_names
            and topic != prerequisite
        ):
            prerequisites[topic].append(prerequisite)

    for topic in prerequisites:
        prerequisites[topic] = list(
            dict.fromkeys(prerequisites[topic])
        )

    # -----------------------------------------------------
    # 3. NO COMPLETED TOPICS: RECOMMEND STARTING TOPICS
    # -----------------------------------------------------

    if not completed_set:
        candidates = []

        for topic in topic_names:
            required = prerequisites[topic]

            # A topic with detected prerequisites should not
            # normally be offered as a first choice.
            if required:
                continue

            position = topic_order[topic]
            score = 0

            # Prefer topics near the beginning of the course.
            score -= position * 2

            if is_foundation_topic(topic):
                score += 100

            if is_advanced_topic(topic):
                score -= 100

            candidates.append({
                "topic": topic,
                "score": score,
                "position": position,
                "reason": (
                    "This topic has no detected prerequisite "
                    "in the selected course and appears suitable "
                    "as a possible starting point. Confirm the "
                    "course syllabus for the intended order."
                ),
            })

        # If dependency inference leaves no starting nodes,
        # fall back to early course topics and flag the limitation.
        if not candidates:
            for topic in topic_names:
                position = topic_order[topic]
                score = -position * 2

                if is_foundation_topic(topic):
                    score += 100

                if is_advanced_topic(topic):
                    score -= 100

                candidates.append({
                    "topic": topic,
                    "score": score,
                    "position": position,
                    "reason": (
                        "Suggested from the early course topics "
                        "because the inferred dependency graph "
                        "did not identify a clear starting point. "
                        "Check the syllabus before studying."
                    ),
                })

        candidates.sort(
            key=lambda item: (
                -item["score"],
                item["position"],
            )
        )

        return [
            {
                "topic": item["topic"],
                "reason": item["reason"],
            }
            for item in candidates[:5]
        ]

    # -----------------------------------------------------
    # 4. SOME TOPICS COMPLETED: FIND NEXT TOPICS
    # -----------------------------------------------------

    recommendations = []

    latest_position = max(completed_positions, default=-1)

    for topic in topic_names:
        if topic.casefold() in completed_set:
            continue

        required = prerequisites[topic]

        incomplete = [
            prerequisite
            for prerequisite in required
            if prerequisite.casefold() not in completed_set
        ]

        if required and incomplete:
            continue

        position = topic_order[topic]
        score = 0

        if is_foundation_topic(topic):
            score += 10

        if is_advanced_topic(topic):
            score -= 10

        if position >= latest_position:
            score += 5

        if required:
            score += 10
            reason = (
                "All detected prerequisite topics have been "
                "marked completed, so this topic may be ready "
                "to study next."
            )
        else:
            # Only recommend independent topics near the
            # learner's current position.
            if position > latest_position + 3:
                continue

            reason = (
                "No prerequisite was detected for this topic, "
                "and it is near your current course position."
            )

        recommendations.append({
            "topic": topic,
            "score": score,
            "position": position,
            "reason": reason,
        })

    recommendations.sort(
        key=lambda item: (
            -item["score"],
            item["position"],
        )
    )

    return [
        {
            "topic": item["topic"],
            "reason": item["reason"],
        }
        for item in recommendations[:5]
    ]