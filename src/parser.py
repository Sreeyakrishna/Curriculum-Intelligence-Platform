import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document


# ============================================================
# REGULAR EXPRESSIONS
# ============================================================

COURSE_CODE_RE = re.compile(
    r"\b(?:[A-Z]{2,6}\d{2}[A-Z]\d{2}|[A-Z]{2,6}\d{5})\b"
)

COURSE_HEADING_SAME_LINE = re.compile(
    r"^((?:[A-Z]{2,6}\d{2}[A-Z]\d{2}|[A-Z]{2,6}\d{5}))\s+(.+?)\s+L\s+T\s+P\s+C\s*$",
    re.IGNORECASE,
)

COURSE_CODE_ONLY = re.compile(
    r"^((?:[A-Z]{2,6}\d{2}[A-Z]\d{2}|[A-Z]{2,6}\d{5}))\s*$",
    re.IGNORECASE,
)

SEMESTER_RE = re.compile(
    r"\bSemester\s*[–-]?\s*([IVX]+|\d+)\b",
    re.IGNORECASE,
)

ROMAN_TO_INT = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
}


# ============================================================
# STOP SECTIONS
# ============================================================

STOP_PREFIXES = (
    "weightage",
    "assessment",
    "references",
    "e-resources",
    "description of co",
    "co description",
    "programme outcomes",
    "program outcomes",
    "programme specific outcomes",
    "program specific outcomes",
)


ACTIVITY_PREFIXES = (
    "activities:",
    "activity:",
    "suggested activities:",
    "practical:",
    "list of activities",
)


# ============================================================
# BASIC HELPERS
# ============================================================

def semester_number(value):

    if value.isdigit():
        return int(value)

    return ROMAN_TO_INT.get(value.upper())


def normalize_line(text):

    text = text.replace("\u00ad", "")
    text = text.replace("\ufeff", "")

    return re.sub(
        r"\s+",
        " ",
        text.strip(),
    )


# ============================================================
# FILE EXTRACTION
# ============================================================

def extract_text_from_file(file_path):

    path = Path(file_path)

    extension = path.suffix.lower()

    # --------------------------------------------------------
    # TXT
    # --------------------------------------------------------

    if extension == ".txt":

        try:
            return path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            return path.read_text(
                encoding="cp1252"
            )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if extension == ".pdf":

        reader = PdfReader(file_path)

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n".join(pages)

    # --------------------------------------------------------
    # DOCX
    # --------------------------------------------------------

    if extension == ".docx":

        document = Document(file_path)

        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    raise ValueError(
        "Unsupported file format. "
        "Please upload TXT, PDF, or DOCX."
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # Repair words broken by PDF line endings.
    text = re.sub(
        r"-\n(?=[a-z])",
        "",
        text,
    )

    # Normalize spaces.
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{2,}",
        "\n",
        text,
    )

    return text.strip()


# ============================================================
# BUILD COURSE → SEMESTER MAP
# ============================================================

def build_course_semester_map(pages):

    course_semesters = {}

    current_semester = None

    # The Anna University curriculum tables are
    # located in the first few pages.
    for _, page_text in pages[:6]:

        for raw_line in page_text.splitlines():

            line = normalize_line(
                raw_line
            )

            semester_match = SEMESTER_RE.search(
                line
            )

            if semester_match:

                current_semester = semester_number(
                    semester_match.group(1)
                )

            if current_semester is None:
                continue

            codes = COURSE_CODE_RE.findall(
                line
            )

            for code in codes:

                course_semesters[
                    code.upper()
                ] = current_semester

    return course_semesters


# ============================================================
# COURSE HEADING DETECTION
# ============================================================

def detect_course_heading(lines, index):

    line = normalize_line(
        lines[index]
    )

    # --------------------------------------------------------
    # Example:
    #
    # CS25C07 Object Oriented Programming L T P C
    # --------------------------------------------------------

    same_line = COURSE_HEADING_SAME_LINE.match(
        line
    )

    if same_line:

        return (
            same_line.group(1).upper(),
            same_line.group(2).strip(),
            1,
        )

    # --------------------------------------------------------
    # Example:
    #
    # CS25C03
    # Essentials of Computing
    # L T P C
    # --------------------------------------------------------

    code_only = COURSE_CODE_ONLY.match(
        line
    )

    if code_only:

        code = code_only.group(1).upper()

        following = []

        for position in range(
            index + 1,
            min(index + 5, len(lines)),
        ):

            following.append(
                normalize_line(
                    lines[position]
                )
            )

        if (
            len(following) >= 2
            and following[-1].upper() == "L T P C"
        ):

            title_parts = [
                item
                for item in following[:-1]
                if item
            ]

            if title_parts:

                return (
                    code,
                    " ".join(title_parts),
                    1 + len(following),
                )

        return None

    # --------------------------------------------------------
    # Wrapped heading:
    #
    # CS25C13 Database Management
    # Systems
    # L T P C
    # --------------------------------------------------------

    partial = re.match(
        r"^((?:[A-Z]{2,6}\d{2}[A-Z]\d{2}|[A-Z]{2,6}\d{5}))\s+(.+)$",
        line,
        re.IGNORECASE,
    )

    if partial:

        code = partial.group(1).upper()

        title_parts = [
            partial.group(2).strip()
        ]

        for position in range(
            index + 1,
            min(index + 5, len(lines)),
        ):

            next_line = normalize_line(
                lines[position]
            )

            if next_line.upper() == "L T P C":

                return (
                    code,
                    " ".join(title_parts),
                    position - index + 1,
                )

            if next_line:

                title_parts.append(
                    next_line
                )

    return None


# ============================================================
# CONTENT SECTION DETECTION
# ============================================================

def is_content_section(line):

    if ":" not in line:
        return False

    heading, content = line.split(
        ":",
        1
    )

    heading = heading.strip()

    content = content.strip()

    if not content:
        return False

    if len(heading) < 3:
        return False

    if len(heading) > 90:
        return False

    if len(heading.split()) > 10:
        return False

    blocked = {
        "course objectives",
        "course objective",
        "weightage",
        "assessment methodology",
        "references",
        "e-resources",
        "activities",
        "activity",
        "practical",
    }

    if heading.lower() in blocked:
        return False

    return bool(
        re.match(
            r"^[A-Za-z][A-Za-z0-9 &/()\-’'–]+$",
            heading,
        )
    )


# ============================================================
# CHECK IF A LINE IS ADMINISTRATIVE
# ============================================================

def is_administrative_line(line):

    lower = line.lower().strip()

    blocked = (

        "course objectives",
        "course objective",

        "to provide",
        "to apply",
        "to understand",
        "to develop",
        "to analyze",
        "to analyse",
        "to demonstrate",
        "to identify",
        "to design",
        "to evaluate",

        "students will",
        "students should",

        "activities:",
        "activity:",
        "suggested activities:",

        "weightage:",
        "assessment methodology:",
        "references:",
        "e-resources:",

    )

    return lower.startswith(blocked)


# ============================================================
# EXTRACT MAJOR TOPICS FROM COURSE CONTENT
# ============================================================

def extract_course_topics(lines):

    logical_lines = []

    # --------------------------------------------------------
    # First create cleaner logical lines.
    # --------------------------------------------------------

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        line = line.replace(
            "\u00ad",
            ""
        )

        # Repair hyphenated PDF words.
        if (
            logical_lines
            and logical_lines[-1].endswith("-")
            and re.match(
                r"^[a-z]",
                line
            )
        ):

            logical_lines[-1] = (
                logical_lines[-1][:-1]
                + line
            )

        else:

            logical_lines.append(
                line
            )

    topics = []

    in_objectives = False
    skipping_activity = False
    found_first_section = False

    for raw_line in logical_lines:

        line = normalize_line(
            raw_line
        )

        lower = line.lower()

        if not line:
            continue

        # ----------------------------------------------------
        # Ignore L T P C numbers.
        # ----------------------------------------------------

        if re.fullmatch(
            r"\d+\s+\d+\s+\d+\s+\d+",
            line,
        ):

            continue

        # ----------------------------------------------------
        # Stop at administrative sections.
        # ----------------------------------------------------

        if any(
            lower.startswith(prefix)
            for prefix in STOP_PREFIXES
        ):

            break

        # ----------------------------------------------------
        # Course objectives.
        # ----------------------------------------------------

        if lower.startswith(
            "course objective"
        ):

            in_objectives = True

            continue

        if in_objectives:

            if is_content_section(
                line
            ):

                in_objectives = False

            else:

                continue

        # ----------------------------------------------------
        # Activities.
        # ----------------------------------------------------

        if any(
            lower.startswith(prefix)
            for prefix in ACTIVITY_PREFIXES
        ):

            skipping_activity = True

            continue

        if skipping_activity:

            if is_content_section(
                line
            ):

                skipping_activity = False

            else:

                continue

        # ----------------------------------------------------
        # Major section headings.
        #
        # Example:
        #
        # Differential Calculus:
        # Functions, graph of functions...
        # ----------------------------------------------------

        if is_content_section(
            line
        ):

            heading = line.split(
                ":",
                1
            )[0].strip()

            if len(heading) >= 3:

                topics.append(
                    heading
                )

                found_first_section = True

            continue

        # ----------------------------------------------------
        # Ignore obvious administrative lines.
        # ----------------------------------------------------

        if is_administrative_line(
            line
        ):

            continue

        # ----------------------------------------------------
        # Ignore page/table noise.
        # ----------------------------------------------------

        if re.fullmatch(
            r"\d+(\.\d+)?",
            line
        ):

            continue

        if re.fullmatch(
            r"\d+\s*[-–]\s*\d+\s*[-–]\s*\d+",
            line
        ):

            continue

        if line.upper() == "L T P C":

            continue

        # ----------------------------------------------------
        # Ignore URLs.
        # ----------------------------------------------------

        if (
            line.startswith("http://")
            or line.startswith("https://")
        ):

            continue

        # ----------------------------------------------------
        # Ignore reference-book entries.
        # ----------------------------------------------------

        if re.match(
            r"^\d+\.\s+",
            line
        ):

            continue

        # ----------------------------------------------------
        # Only use additional standalone lines if we have
        # not found a major section yet.
        # ----------------------------------------------------

        if not found_first_section:

            if line.startswith(
                (
                    "•",
                    "●",
                    "○",
                    "-",
                    "*",
                )
            ):

                continue

            if len(line) > 90:

                continue

            if len(line.split()) > 12:

                continue

            topics.append(
                line.strip(" .:-")
            )

    return topics


# ============================================================
# PDF PARSER
# ============================================================

def parse_pdf(file_path):

    reader = PdfReader(
        file_path
    )

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        text = page.extract_text() or ""

        pages.append(
            (
                page_number,
                text
            )
        )

    # --------------------------------------------------------
    # Build course → semester mapping.
    # --------------------------------------------------------

    course_semesters = (
        build_course_semester_map(
            pages
        )
    )

    records = []

    current_course = None
    current_block = []

    seen_codes = set()

    # --------------------------------------------------------
    # Helper to finish one course.
    # --------------------------------------------------------

    def flush_course():

        nonlocal current_block

        if current_course is None:

            current_block = []

            return

        code, title = current_course

        topics = extract_course_topics(
            current_block
        )

        for topic in topics:

            if not topic:
                continue

            records.append(
                {
                    "semester":
                        course_semesters.get(
                            code
                        ),

                    "unit":
                        None,

                    "subject":
                        title,

                    "topic":
                        topic,

                    "course_code":
                        code,
                }
            )

        current_block = []

    # --------------------------------------------------------
    # Read every page.
    # --------------------------------------------------------

    for _, page_text in pages:

        lines = page_text.splitlines()

        index = 0

        while index < len(lines):

            heading = detect_course_heading(
                lines,
                index
            )

            if heading:

                code, title, consumed = heading

                # Finish previous course.
                if current_course is not None:

                    flush_course()

                # Keep one version of a course.
                if code in seen_codes:

                    index += consumed

                    continue

                seen_codes.add(
                    code
                )

                current_course = (
                    code,
                    title
                )

                current_block = []

                index += consumed

                continue

            # Add content to current course.
            if current_course is not None:

                current_block.append(
                    lines[index]
                )

            index += 1

    # Flush final course.
    flush_course()

    # --------------------------------------------------------
    # Remove duplicates.
    # --------------------------------------------------------

    unique_records = []

    seen = set()

    for item in records:

        key = (
            item.get(
                "course_code",
                ""
            ),
            item.get(
                "topic",
                ""
            ).casefold(),
        )

        if key not in seen:

            seen.add(
                key
            )

            unique_records.append(
                item
            )

    return unique_records


# ============================================================
# TXT / DOCX PARSER
# ============================================================

def parse_simple_text(file_path):

    text = extract_text_from_file(
        file_path
    )

    records = []

    current_semester = None
    current_unit = None
    current_subject = None

    for raw_line in text.splitlines():

        line = normalize_line(
            raw_line
        )

        if not line:
            continue

        # ----------------------------------------------------
        # Semester.
        # ----------------------------------------------------

        semester_match = SEMESTER_RE.search(
            line
        )

        if semester_match:

            current_semester = semester_number(
                semester_match.group(1)
            )

            current_unit = None

            continue

        # ----------------------------------------------------
        # Unit.
        # ----------------------------------------------------

        unit_match = re.match(
            r"^Unit\s*[-:]?\s*(\d+|[IVX]+)\b",
            line,
            re.IGNORECASE,
        )

        if unit_match:

            value = unit_match.group(1)

            if value.isdigit():

                current_unit = int(
                    value
                )

            else:

                current_unit = (
                    ROMAN_TO_INT.get(
                        value.upper()
                    )
                )

            continue

        # ----------------------------------------------------
        # Subject.
        # ----------------------------------------------------

        if line.lower().startswith(
            "subject:"
        ):

            current_subject = line.split(
                ":",
                1
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Bullet topic.
        # ----------------------------------------------------

        if line.startswith(
            (
                "-",
                "•",
                "●",
                "*",
            )
        ):

            topic = re.sub(
                r"^[\-•●*]+\s*",
                "",
                line
            ).strip()

            if len(topic) >= 3:

                records.append(
                    {
                        "semester":
                            current_semester,

                        "unit":
                            current_unit,

                        "subject":
                            current_subject,

                        "topic":
                            topic,
                    }
                )

    return records


# ============================================================
# MAIN FUNCTION
# ============================================================

def parse_syllabus(file_path):

    extension = Path(
        file_path
    ).suffix.lower()

    if extension == ".pdf":

        return parse_pdf(
            file_path
        )

    if extension in (
        ".txt",
        ".docx",
    ):

        return parse_simple_text(
            file_path
        )

    raise ValueError(
        "Unsupported file format. "
        "Please upload TXT, PDF, or DOCX."
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    file_path = "data/syllabus.txt"

    topics = parse_syllabus(
        file_path
    )

    print()

    print(
        "Extracted Syllabus Topics"
    )

    print(
        "========================="
    )

    for item in topics:

        print(
            f"Subject: {item.get('subject')} | "
            f"Semester: {item.get('semester')} | "
            f"Unit: {item.get('unit')} | "
            f"Topic: {item.get('topic')}"
        )

    print()

    print(
        f"Total extracted items: {len(topics)}"
    )