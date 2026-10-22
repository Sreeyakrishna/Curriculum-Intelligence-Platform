
import os
import tempfile

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from pypdf import PdfReader

from src.parser import parse_syllabus
from src.dependency import build_dependencies
from src.recommender import recommend_learning_path


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Curriculum Intelligence Platform",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_page_count(file_path):
    """Return the number of pages in a PDF, or 1 for other files."""
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        try:
            reader = PdfReader(file_path)
            return len(reader.pages)
        except Exception:
            return 0

    return 1


def display_recommendations(recommendations):
    """Display recommended topics and their explanations."""
    if recommendations:
        for index, recommendation in enumerate(
            recommendations, start=1
        ):
            if isinstance(recommendation, dict):
                topic_name = recommendation.get(
                    "topic", "Unknown topic"
                )
                reason = recommendation.get("reason", "")
            else:
                topic_name = str(recommendation)
                reason = ""

            st.markdown(f"### {index}. {topic_name}")

            if reason:
                st.write(f"💡 {reason}")
    else:
        st.info(
            "No recommendations were generated. Try selecting "
            "different completed topics or reviewing the inferred "
            "prerequisite relationships."
        )


def display_dependency_graph(topics, dependencies):
    """Visualize inferred prerequisite relationships."""
    graph = nx.DiGraph()

    for item in topics:
        topic_name = item.get("topic")
        if topic_name:
            graph.add_node(str(topic_name))

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue

        prerequisite = (
            dependency.get("prerequisite")
            or dependency.get("prerequisite_topic")
            or dependency.get("source")
            or dependency.get("from")
        )

        dependent = (
            dependency.get("topic")
            or dependency.get("dependent")
            or dependency.get("dependent_topic")
            or dependency.get("target")
            or dependency.get("to")
        )

        if (
            prerequisite
            and dependent
            and str(prerequisite) in graph
            and str(dependent) in graph
        ):
            graph.add_edge(
                str(prerequisite),
                str(dependent),
            )

    if graph.number_of_edges() == 0:
        st.info(
            "The graph could not identify compatible prerequisite "
            "and dependent topic fields in the inferred relationships."
        )
        return

    figure_width = min(
        20, max(10, graph.number_of_nodes() * 0.45)
    )

    figure, axis = plt.subplots(
        figsize=(figure_width, 8)
    )

    try:
        positions = nx.kamada_kawai_layout(graph)
    except Exception:
        positions = nx.spring_layout(
            graph, seed=42, k=1.2
        )

    nx.draw_networkx(
        graph,
        pos=positions,
        ax=axis,
        with_labels=True,
        node_size=1600,
        font_size=7,
        arrows=True,
        arrowsize=15,
    )

    axis.set_title("Curriculum Dependency Graph")
    axis.axis("off")
    figure.tight_layout()

    st.pyplot(figure)
    plt.close(figure)


# ============================================================
# HEADER
# ============================================================

st.title("📚 AI-Powered Curriculum Intelligence Platform")

st.write(
    "An AI-assisted system for analysing syllabus structure, "
    "identifying likely prerequisite relationships, and generating "
    "personalized learning paths."
)

st.divider()


# ============================================================
# UPLOAD SYLLABUS
# ============================================================

st.header("📂 Upload Syllabus")

uploaded_file = st.file_uploader(
    "Upload your syllabus",
    type=["pdf", "txt", "docx"],
)

use_sample = st.checkbox(
    "Use sample syllabus for testing"
)


# ============================================================
# SELECT INPUT SOURCE
# ============================================================

temp_path = None
source_path = None
source_name = None
pages = 1

if uploaded_file is not None:
    suffix = os.path.splitext(uploaded_file.name)[1].lower()

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_path = temp_file.name

        source_path = temp_path
        source_name = uploaded_file.name
        pages = get_page_count(source_path)

    except Exception as error:
        st.error(f"Could not read the uploaded file: {error}")

elif use_sample:
    source_path = os.path.join("data", "syllabus.txt")
    source_name = "Sample syllabus"

    if not os.path.exists(source_path):
        st.error(
            "Sample syllabus file was not found. "
            "Check that data/syllabus.txt exists in your project."
        )
        source_path = None


# ============================================================
# PROCESS SYLLABUS
# ============================================================

if source_path is not None:
    try:
        with st.spinner("Processing syllabus..."):
            topics = parse_syllabus(source_path)

        st.success(
            f"Syllabus loaded successfully: {source_name}"
        )

        if not topics:
            st.error(
                "No syllabus topics were detected. "
                "Please check the uploaded document."
            )
            st.stop()

        # ----------------------------------------------------
        # DOCUMENT ANALYSIS
        # ----------------------------------------------------

        st.header("📄 Document Analysis")

        subjects = sorted({
            str(item.get("subject")).strip()
            for item in topics
            if item.get("subject")
            and str(item.get("subject")).strip()
        })

        col1, col2, col3 = st.columns(3)

        col1.metric("Pages Processed", pages)
        col2.metric("Courses Detected", len(subjects))
        col3.metric("Topics Detected", len(topics))

        st.divider()

        # ----------------------------------------------------
        # EXTRACTED TOPICS
        # ----------------------------------------------------

        st.header("📚 Extracted Syllabus Topics")

        st.write(
            f"**{len(topics)} syllabus concepts detected.**"
        )

        dataframe = pd.DataFrame(topics)

        available_columns = [
            column
            for column in [
                "semester",
                "subject",
                "unit",
                "topic",
            ]
            if column in dataframe.columns
        ]

        dataframe = dataframe[available_columns]

        rename_map = {
            "semester": "Semester",
            "subject": "Course",
            "unit": "Unit",
            "topic": "Topic",
        }

        dataframe = dataframe.rename(columns=rename_map)

        st.dataframe(
            dataframe,
            use_container_width=True,
            height=400,
        )

        # ----------------------------------------------------
        # COURSE SUMMARY
        # ----------------------------------------------------

        if "Course" in dataframe.columns:
            st.header("📘 Course Summary")

            course_counts = (
                dataframe[dataframe["Course"].notna()]
                .groupby("Course")
                .size()
                .reset_index(name="Topics")
                .sort_values("Topics", ascending=False)
            )

            st.dataframe(
                course_counts,
                use_container_width=True,
            )

        # ----------------------------------------------------
        # DEPENDENCY ANALYSIS
        # ----------------------------------------------------

        st.header("🔗 AI-Inferred Prerequisite Relationships")

        st.info(
            "These are AI-inferred likely prerequisite relationships "
            "based on semantic similarity and syllabus structure. "
            "They are not official university prerequisites."
        )

        with st.spinner(
            "Analysing relationships between syllabus topics..."
        ):
            try:
                dependencies = build_dependencies(topics)
            except Exception as error:
                st.warning(
                    f"Dependency analysis could not be completed: {error}"
                )
                dependencies = []

        if dependencies:
            dependency_df = pd.DataFrame(dependencies)

            st.dataframe(
                dependency_df,
                use_container_width=True,
            )

            st.success(
                f"{len(dependencies)} likely prerequisite "
                "relationships inferred."
            )
        else:
            st.warning(
                "No prerequisite relationships were inferred."
            )

        # ----------------------------------------------------
        # PERSONALIZED LEARNING PATH
        # ----------------------------------------------------

        st.header("🎯 Personalized Learning Path")

        # Identify available courses.
        available_courses = sorted({
            str(item.get("subject")).strip()
            for item in topics
            if item.get("subject")
            and str(item.get("subject")).strip()
        })

        if available_courses:
            selected_course = st.selectbox(
                "Choose the course you want to study:",
                options=available_courses,
                key="learning_path_course",
                help=(
                    "Recommendations will be limited to "
                    "the selected course."
                ),
            )

            # Keep only topics from the selected course.
            course_topics = [
                item
                for item in topics
                if str(item.get("subject", "")).strip()
                == selected_course
                and item.get("topic")
            ]

            course_topic_names = list(dict.fromkeys(
                str(item["topic"]).strip()
                for item in course_topics
                if str(item.get("topic", "")).strip()
            ))

            st.write(
                f"**Selected course:** {selected_course}"
            )

            st.write(
                f"**Topics in this course:** "
                f"{len(course_topic_names)}"
            )

            completed_topics = st.multiselect(
                "Select the topics you have already completed:",
                options=course_topic_names,
                key="completed_course_topics",
                help=(
                    "Leave this empty to see recommended starting "
                    "topics for the selected course."
                ),
            )

            # CASE 1: No topics completed.
            # Automatically show recommended starting topics.
            if not completed_topics:
                st.info(
                    "You haven't selected any completed topics yet. "
                    "Here are some suggested starting topics for "
                    "your chosen course."
                )

                try:
                    with st.spinner(
                        "Finding suitable starting topics..."
                    ):
                        recommendations = recommend_learning_path(
                            topics,
                            dependencies,
                            [],
                            selected_course=selected_course,
                        )

                    st.subheader("🌱 Recommended Starting Topics")
                    display_recommendations(recommendations)

                except Exception as error:
                    st.error(
                        "Starting-topic recommendation failed: "
                        f"{error}"
                    )

            # CASE 2: Topics completed.
            # Generate next recommendations when the button is clicked.
            else:
                st.write(
                    f"You selected **{len(completed_topics)}** "
                    "completed topic(s). Click below to generate "
                    "your personalized next topics."
                )

                if st.button(
                    "Generate Personalized Learning Path",
                    type="primary",
                    key="generate_learning_path",
                ):
                    try:
                        with st.spinner(
                            "Generating your personalized learning path..."
                        ):
                            recommendations = recommend_learning_path(
                                topics,
                                dependencies,
                                completed_topics,
                                selected_course=selected_course,
                            )

                        st.subheader("🚀 Recommended Next Topics")
                        display_recommendations(recommendations)

                    except Exception as error:
                        st.error(
                            "Learning path generation failed: "
                            f"{error}"
                        )

        else:
            st.warning(
                "No course names were detected in this syllabus. "
                "Please check the extracted syllabus topics."
            )

        # ----------------------------------------------------
        # CURRICULUM DEPENDENCY GRAPH
        # ----------------------------------------------------

        st.header("🕸️ Curriculum Dependency Graph")

        display_dependency_graph(topics, dependencies)

        # ----------------------------------------------------
        # SYSTEM WORKFLOW
        # ----------------------------------------------------

        st.header("⚙️ System Workflow")

        st.markdown(
            """
**1. Syllabus Upload**

PDF, DOCX or TXT syllabus is provided by the learner.

↓

**2. Document Processing**

The system extracts readable syllabus content.

↓

**3. Syllabus Structure Analysis**

Courses, semesters, units and meaningful concepts are identified.

↓

**4. Semantic Analysis**

Sentence-transformer embeddings are used to compare syllabus concepts.

↓

**5. Dependency Inference**

The system identifies likely prerequisite relationships.

↓

**6. Personalized Learning Path**

Learner progress is considered to recommend suitable next topics.
"""
        )

        # ----------------------------------------------------
        # DISCLAIMER
        # ----------------------------------------------------

        st.divider()

        st.caption(
            "Note: This platform provides AI-assisted analysis. "
            "Inferred prerequisite relationships and learning "
            "recommendations should be reviewed by instructors "
            "or learners before being treated as authoritative."
        )

    except Exception as error:
        st.error(
            f"Error while processing the syllabus: {error}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

# ============================================================
# INITIAL MESSAGE
# ============================================================

else:
    st.info(
        "Upload a PDF, DOCX, or TXT syllabus, "
        "or select 'Use sample syllabus for testing' to begin."
    )
