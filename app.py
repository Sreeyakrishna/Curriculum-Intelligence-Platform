import os
import tempfile

import streamlit as st
import pandas as pd

from pypdf import PdfReader

from src.parser import parse_syllabus
from src.dependency import build_dependencies
from src.recommender import recommend_learning_path


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Curriculum Intelligence Platform",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# HELPER FUNCTION
# ============================================================

def get_page_count(file_path):

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":

        try:
            reader = PdfReader(file_path)
            return len(reader.pages)

        except Exception:
            return 0

    # TXT and DOCX are treated as one uploaded document
    return 1


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
    type=["pdf", "txt", "docx"]
)


# ============================================================
# SAMPLE OPTION
# ============================================================

use_sample = st.checkbox(
    "Use sample syllabus for testing"
)


# ============================================================
# MAIN PROCESSING
# ============================================================

if uploaded_file is not None:

    # --------------------------------------------------------
    # Save uploaded file temporarily
    # --------------------------------------------------------

    suffix = os.path.splitext(
        uploaded_file.name
    )[1]

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            temp_file.write(
                uploaded_file.getbuffer()
            )

            temp_path = temp_file.name


        # ----------------------------------------------------
        # DOCUMENT INFORMATION
        # ----------------------------------------------------

        pages = get_page_count(
            temp_path
        )


        # ----------------------------------------------------
        # PARSE SYLLABUS
        # ----------------------------------------------------

        topics = parse_syllabus(
            temp_path
        )


        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        st.success(
            f"Syllabus uploaded successfully: "
            f"{uploaded_file.name}"
        )


        # ----------------------------------------------------
        # DOCUMENT ANALYSIS
        # ----------------------------------------------------

        st.header("📄 Document Analysis")

        col1, col2, col3 = st.columns(3)


        # Pages
        with col1:

            st.metric(
                "Pages Processed",
                pages
            )


        # Courses
        with col2:

            subjects = sorted(
                set(
                    item.get("subject")
                    for item in topics
                    if item.get("subject")
                )
            )

            st.metric(
                "Courses Detected",
                len(subjects)
            )


        # Topics
        with col3:

            st.metric(
                "Topics Detected",
                len(topics)
            )


        st.divider()


        # ----------------------------------------------------
        # EXTRACTED TOPICS
        # ----------------------------------------------------

        st.header(
            "📚 Extracted Syllabus Topics"
        )


        if not topics:

            st.error(
                "No syllabus topics were detected. "
                "Please check the uploaded document."
            )

            st.stop()


        st.write(
            f"**{len(topics)} meaningful syllabus concepts detected.**"
        )


        dataframe = pd.DataFrame(
            topics
        )


        # ----------------------------------------------------
        # DISPLAY COLUMNS
        # ----------------------------------------------------

        available_columns = [
            column
            for column in [
                "semester",
                "subject",
                "unit",
                "topic"
            ]
            if column in dataframe.columns
        ]


        dataframe = dataframe[
            available_columns
        ]


        rename_map = {

            "semester": "Semester",

            "subject": "Course",

            "unit": "Unit",

            "topic": "Topic"

        }


        dataframe = dataframe.rename(
            columns=rename_map
        )


        st.dataframe(
            dataframe,
            use_container_width=True,
            height=450
        )


        # ----------------------------------------------------
        # COURSE SUMMARY
        # ----------------------------------------------------

        if "Course" in dataframe.columns:

            st.header(
                "📘 Course Summary"
            )


            course_counts = (
                dataframe[
                    dataframe["Course"].notna()
                ]
                .groupby("Course")
                .size()
                .reset_index(
                    name="Topics"
                )
                .sort_values(
                    "Topics",
                    ascending=False
                )
            )


            st.dataframe(
                course_counts,
                use_container_width=True
            )


        # ----------------------------------------------------
        # DEPENDENCY ANALYSIS
        # ----------------------------------------------------

        st.header(
            "🔗 AI-Inferred Prerequisite Relationships"
        )


        st.info(
            "The prerequisite relationships below are "
            "AI-inferred likely relationships based on "
            "semantic similarity and syllabus structure. "
            "They are not official university prerequisites."
        )


        with st.spinner(
            "Analysing semantic relationships..."
        ):

            try:

                dependencies = build_dependencies(
                    topics
                )

            except Exception as error:

                st.warning(
                    f"Dependency analysis could not be completed: "
                    f"{error}"
                )

                dependencies = []


        if dependencies:

            dependency_df = pd.DataFrame(
                dependencies
            )


            st.dataframe(
                dependency_df,
                use_container_width=True
            )


            st.success(
                f"{len(dependencies)} likely prerequisite "
                f"relationships inferred."
            )

        else:

            st.warning(
                "No prerequisite relationships were inferred."
            )


        # ----------------------------------------------------
        # PERSONALIZED LEARNING PATH
        # ----------------------------------------------------

        st.header(
            "🎯 Personalized Learning Path"
        )


        all_topics = [
            item["topic"]
            for item in topics
            if item.get("topic")
        ]


        completed_topics = st.multiselect(
            "Select the topics you have already completed:",
            options=all_topics
        )


        if st.button(
            "Generate Learning Path"
        ):

            try:

                recommendations = recommend_learning_path(
                    topics,
                    dependencies,
                    completed_topics
                )


                if recommendations:

                    st.subheader(
                        "Recommended Next Topics"
                    )


                    for index, recommendation in enumerate(
                        recommendations,
                        start=1
                    ):

                        if isinstance(
                            recommendation,
                            dict
                        ):

                            topic_name = recommendation.get(
                                "topic",
                                "Unknown topic"
                            )


                            reason = recommendation.get(
                                "reason",
                                ""
                            )


                            st.markdown(
                                f"### {index}. {topic_name}"
                            )


                            if reason:

                                st.write(
                                    f"💡 {reason}"
                                )

                        else:

                            st.markdown(
                                f"### {index}. {recommendation}"
                            )

                else:

                    st.info(
                        "No recommendations were generated."
                    )


            except Exception as error:

                st.error(
                    f"Learning path generation failed: "
                    f"{error}"
                )


        # ----------------------------------------------------
        # SYSTEM WORKFLOW
        # ----------------------------------------------------

        st.header(
            "⚙️ System Workflow"
        )


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
            "Note: The platform provides AI-assisted analysis. "
            "Inferred prerequisite relationships should be "
            "reviewed by instructors or learners before being "
            "treated as authoritative."
        )


    except Exception as error:

        st.error(
            f"Error while processing the syllabus: {error}"
        )


    finally:

        # ----------------------------------------------------
        # DELETE TEMPORARY FILE
        # ----------------------------------------------------

        if temp_path and os.path.exists(temp_path):

            try:

                os.remove(temp_path)

            except Exception:

                pass


# ============================================================
# SAMPLE SYLLABUS
# ============================================================

elif use_sample:

    sample_path = "data/syllabus.txt"


    if os.path.exists(sample_path):

        topics = parse_syllabus(
            sample_path
        )


        st.success(
            "Sample syllabus loaded successfully."
        )


        st.header(
            "📚 Extracted Syllabus Topics"
        )


        st.metric(
            "Topics Detected",
            len(topics)
        )


        dataframe = pd.DataFrame(
            topics
        )


        st.dataframe(
            dataframe,
            use_container_width=True
        )


    else:

        st.warning(
            "Sample syllabus file was not found."
        )


# ============================================================
# INITIAL MESSAGE
# ============================================================

else:

    st.info(
        "Upload a PDF, DOCX, or TXT syllabus to begin."
    )