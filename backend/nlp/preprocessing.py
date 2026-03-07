import re
from typing import List


def preprocess_text(text: str) -> str:
    # make the whole text lowercase first
    cleaned_text = text.lower()

    # remove weird chars but keep letters, numbers, spaces, and . , : / + -
    cleaned_text = re.sub(r"[^a-z0-9\s\.,:/+\-]", "", cleaned_text)

    # replace multiple spaces/newlines/tabs with one space
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text


def extract_skills(text: str) -> List[str]:
    # placeholder for skills extraction later
    return []


def extract_experience(text: str) -> List[str]:
    # placeholder for experience extraction later
    return []


def extract_education(text: str) -> List[str]:
    # placeholder for education extraction later
    return []


def extract_sections(text):
    # clean the text before splitting into sections
    cleaned_text = preprocess_text(text)

    # return all section results in one dictionary
    return {
        "skills": extract_skills(cleaned_text),
        "experience": extract_experience(cleaned_text),
        "education": extract_education(cleaned_text),
    }
