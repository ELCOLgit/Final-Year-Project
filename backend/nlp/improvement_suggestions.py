from typing import List


def generate_suggestions(cv_text: str, job_text: str, missing_skills: List[str]) -> List[str]:
    # make both texts lowercase so matching is easier
    cv_text_lower = cv_text.lower()
    job_text_lower = job_text.lower()
    suggestions = []

    # suggest adding each missing skill to the skills section
    for skill in missing_skills:
        lowered_skill = skill.lower()
        suggestions.append(f"consider adding {lowered_skill} to your skills section")

        # add a second suggestion if the resume talks about experience but misses the skill
        if "experience" in cv_text_lower and lowered_skill in job_text_lower:
            suggestions.append(
                f"your resume mentions experience but does not include {lowered_skill}"
            )

    # add a simple fallback if nothing is missing
    if not suggestions:
        suggestions.append("your cv already matches the main skills in the job description")

    return suggestions
