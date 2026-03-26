from typing import List


# keep the list small and simple for basic matching
KNOWN_SKILLS = [
    "python",
    "sql",
    "fastapi",
    "excel",
    "cloud",
    "react",
    "machine learning",
]


def extract_skills_from_text(text: str) -> List[str]:
    # make the text lowercase so matching is easier
    lowered_text = text.lower()
    found_skills = []

    # check if each known skill is mentioned in the text
    for skill in KNOWN_SKILLS:
        if skill in lowered_text:
            found_skills.append(skill)

    return found_skills


def compare_skills(cv_skills: List[str], job_skills: List[str]) -> List[str]:
    # convert both lists to lowercase so the comparison is simple
    cv_skills_lower = [skill.lower() for skill in cv_skills]
    missing_skills = []

    # add skills that are in the job list but not in the cv list
    for skill in job_skills:
        lowered_skill = skill.lower()
        if lowered_skill not in cv_skills_lower and lowered_skill not in missing_skills:
            missing_skills.append(lowered_skill)

    return missing_skills
