import random

from backend.nlp.skills_extractor import compare_skills, extract_skills_from_text
from backend.nlp.improvement_suggestions import generate_suggestions


def detect_intent(question: str) -> str:
    # normalize the question for simple keyword matching
    normalized_question = question.lower()

    if "skills" in normalized_question:
        return "skills_in_cv"

    if "missing" in normalized_question or "lack" in normalized_question:
        return "missing_skills"

    if "best" in normalized_question or "top" in normalized_question:
        return "best_candidate"

    if "why" in normalized_question or "score" in normalized_question:
        return "explain_match"

    return "general"


def generate_response(intent, context_data):
    # read context values from the provided data
    if not isinstance(context_data, dict):
        return "I could not find enough candidate or job data to answer that question."

    candidate_name = context_data.get("candidate_name", "this candidate")
    job_title = context_data.get("job_title", "this role")
    cv_skills = context_data.get("cv_skills", [])
    job_skills = context_data.get("job_skills", [])
    missing_skills = context_data.get("missing_skills", [])
    suggestions = context_data.get("suggestions", [])
    match_score = context_data.get("match_score")
    best_candidate_name = context_data.get("best_candidate_name")
    best_candidate_score = context_data.get("best_candidate_score")

    if intent == "skills_in_cv":
        if cv_skills:
            skill_text = _format_list(cv_skills[:3])
            responses = [
                f"{candidate_name} shows strong skills in {skill_text}.",
                f"Key strengths for {candidate_name} include {skill_text}.",
                f"The CV for {candidate_name} highlights experience in {skill_text}.",
            ]
            return random.choice(responses)
        return f"I could not identify any known skills in the CV for {candidate_name}."

    if intent == "missing_skills":
        if missing_skills:
            missing_text = _format_list(missing_skills[:3])
            responses = [
                f"For {job_title}, {candidate_name} is currently missing key skills such as {missing_text}.",
                f"{candidate_name} does not yet show some important requirements for {job_title}, including {missing_text}.",
                f"There are a few gaps for {candidate_name} in relation to {job_title}, especially {missing_text}.",
            ]
            response = random.choice(responses)
            if suggestions:
                response += f" {_format_suggestion_text(suggestions[0])}"
            return response
        if job_skills and cv_skills:
            responses = [
                f"{candidate_name} appears to cover the main extracted skills for {job_title}.",
                f"The CV already matches the main skills identified for {job_title}.",
                f"{candidate_name} seems to meet the key extracted skill requirements for {job_title}.",
            ]
            return random.choice(responses)
        return f"I could not compare the CV against the job requirements for {job_title}."

    if intent == "best_candidate":
        if best_candidate_name and job_title and best_candidate_score is not None:
            responses = [
                f"Based on the stored similarity scores, {best_candidate_name} is currently the strongest match for {job_title} with a score of {best_candidate_score:.3f}.",
                f"Looking at the saved match results, {best_candidate_name} stands out as the top candidate for {job_title} with a score of {best_candidate_score:.3f}.",
                f"Right now, {best_candidate_name} appears to be the best fit for {job_title}, with a similarity score of {best_candidate_score:.3f}.",
            ]
            return random.choice(responses)
        if best_candidate_name and job_title:
            responses = [
                f"Based on the stored similarity results, {best_candidate_name} is the top match for {job_title}.",
                f"{best_candidate_name} currently looks like the strongest candidate for {job_title}.",
                f"The saved ranking shows {best_candidate_name} as the best match for {job_title}.",
            ]
            return random.choice(responses)
        return "I could not find a ranked candidate for the selected job."

    if intent == "explain_match":
        if match_score is not None and cv_skills and job_skills:
            shared_skills = [skill for skill in cv_skills if skill in job_skills]
            shared_text = _format_list(shared_skills[:3]) if shared_skills else "no direct skill overlap"
            responses = [
                f"{candidate_name} has a match score of {match_score:.3f} for {job_title}, based on overlap in skills such as {shared_text}.",
                f"The score of {match_score:.3f} for {candidate_name} comes from shared skills with {job_title}, including {shared_text}.",
                f"{candidate_name} scored {match_score:.3f} for {job_title} because the CV aligns with the role in areas like {shared_text}.",
            ]
            return random.choice(responses)
        if match_score is not None:
            responses = [
                f"{candidate_name} currently has a match score of {match_score:.3f} for {job_title}.",
                f"The saved score for {candidate_name} against {job_title} is {match_score:.3f}.",
                f"Right now, {candidate_name} has a similarity score of {match_score:.3f} for {job_title}.",
            ]
            return random.choice(responses)
        return f"I could not find a saved match score for {candidate_name} and {job_title}."

    if match_score is not None and job_title != "this role":
        responses = [
            f"{candidate_name} currently has a match score of {match_score:.3f} for {job_title}.",
            f"The current similarity score for {candidate_name} and {job_title} is {match_score:.3f}.",
            f"For {job_title}, {candidate_name} has a saved match score of {match_score:.3f}.",
        ]
        return random.choice(responses)

    if cv_skills:
        skill_text = _format_list(cv_skills[:3])
        responses = [
            f"{candidate_name} has extracted CV skills including {skill_text}.",
            f"From the CV, the main identified skills are {skill_text}.",
            f"The profile shows experience in areas such as {skill_text}.",
        ]
        return random.choice(responses)

    return "I could not find enough candidate or job data to answer that question."


def explain_match(cv_text, job_text, score):
    # extract simple skill lists from the cv and job text
    cv_skills = extract_skills_from_text(cv_text or "")
    job_skills = extract_skills_from_text(job_text or "")
    shared_skills = [skill for skill in cv_skills if skill in job_skills]
    missing_skills = compare_skills(cv_skills, job_skills)
    suggestions = generate_suggestions(cv_text or "", job_text or "", missing_skills)

    # describe the strength of the score in simple language
    if score >= 0.75:
        score_text = "a strong match"
    elif score >= 0.45:
        score_text = "a moderate match"
    else:
        score_text = "a weaker match"

    if shared_skills:
        shared_text = _format_list(shared_skills[:3])
        explanation = (
            f"This candidate is {score_text} because they have {shared_text} "
            f"which align with the job requirements."
        )
    else:
        explanation = (
            f"This candidate is {score_text} because there is limited overlap "
            f"between the extracted CV skills and the job requirements."
        )

    if missing_skills:
        missing_text = _format_list(missing_skills[:3])
        explanation += (
            f" However, they are missing {missing_text}, which slightly lowers the score."
        )
        if suggestions:
            explanation += f" {_format_suggestion_text(suggestions[0])}"
    elif job_skills:
        explanation += " They cover the main extracted skills in the job description."

    return explanation


def multi_step_match_analysis(cv_text, job_text):
    # step 1: extract skills from the cv
    cv_skills = extract_skills_from_text(cv_text or "")
    print("extracted cv skills:", cv_skills)

    # step 2: extract skills from the job
    job_skills = extract_skills_from_text(job_text or "")
    print("extracted job skills:", job_skills)

    # step 3: find matching skills
    matching_skills = [skill for skill in cv_skills if skill in job_skills]
    print("matching skills:", matching_skills)

    # step 4: find missing skills
    missing_skills = compare_skills(cv_skills, job_skills)
    print("missing skills:", missing_skills)

    # step 5: calculate a simple match score
    if job_skills:
        score = len(matching_skills) / len(job_skills)
    else:
        score = 0.0
    print("score:", float(score))

    # step 6: return all results in one dictionary
    return {
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "score": float(score),
    }


def explain_score(matching_skills, missing_skills, score):
    # count the number of matching and missing skills
    matching_count = len(matching_skills or [])
    missing_count = len(missing_skills or [])

    # build readable skill text for the explanation
    matching_text = _format_list((matching_skills or [])[:3])
    missing_text = _format_list((missing_skills or [])[:3])

    # explain the score using simple score bands
    if score > 0.7:
        if matching_text:
            return (
                f"This candidate is a strong match because they meet most of the required skills, "
                f"including {matching_text}. They have {matching_count} matching skills and "
                f"{missing_count} missing skills."
            )
        return (
            f"This candidate is a strong match because they meet most of the required skills. "
            f"They have {matching_count} matching skills and {missing_count} missing skills."
        )

    if 0.4 <= score <= 0.7:
        if missing_text:
            return (
                f"This candidate is a moderate match. They meet some requirements but are missing "
                f"skills like {missing_text}. They have {matching_count} matching skills and "
                f"{missing_count} missing skills."
            )
        return (
            f"This candidate is a moderate match. They meet some of the role requirements. "
            f"They have {matching_count} matching skills and {missing_count} missing skills."
        )

    return (
        f"This candidate is a weak match because they are missing several key skills required for "
        f"this role. They have {matching_count} matching skills and {missing_count} missing skills."
    )


def generate_match_explanation(cv_text, job_text):
    # run the multi-step analysis first
    analysis = multi_step_match_analysis(cv_text, job_text)

    # get the main values from the analysis
    matching_skills = analysis.get("matching_skills", [])
    missing_skills = analysis.get("missing_skills", [])
    score = analysis.get("score", 0.0)

    # count total required skills from the analysis results
    matching_count = len(matching_skills)
    missing_count = len(missing_skills)
    total_job_skills = matching_count + missing_count

    # choose a simple overall label for the score
    if score > 0.7:
        overall_text = "a strong match"
    elif score >= 0.4:
        overall_text = "a moderate match"
    else:
        overall_text = "a weak match"

    # build readable skill text
    matching_text = _format_list(matching_skills[:3])
    missing_text = _format_list(missing_skills[:3])

    if total_job_skills == 0:
        return "I could not identify any required job skills, so a clear match explanation is not available."

    if matching_text and missing_text:
        return (
            f"This candidate matches {matching_count} out of {total_job_skills} required skills, "
            f"including {matching_text}. However, they are missing {missing_text}, which lowers "
            f"the score. Overall, this is {overall_text}."
        )

    if matching_text:
        return (
            f"This candidate matches {matching_count} out of {total_job_skills} required skills, "
            f"including {matching_text}. They cover most of the identified requirements. Overall, "
            f"this is {overall_text}."
        )

    return (
        f"This candidate matches {matching_count} out of {total_job_skills} required skills. They "
        f"are missing {missing_count} identified job skills, which lowers the score. Overall, this "
        f"is {overall_text}."
    )


def _format_list(values):
    # format short lists into a natural sentence fragment
    if not values:
        return ""

    if len(values) == 1:
        return values[0]

    if len(values) == 2:
        return f"{values[0]} and {values[1]}"

    return f"{', '.join(values[:-1])} and {values[-1]}"


def _format_suggestion_text(suggestion):
    # turn raw suggestions into a natural follow-up sentence
    cleaned_suggestion = (suggestion or "").strip().rstrip(".")
    if not cleaned_suggestion:
        return ""

    if cleaned_suggestion.startswith("consider adding "):
        skill_name = cleaned_suggestion.replace("consider adding ", "", 1)
        skill_name = skill_name.replace(" to your skills section", "")
        return f"Adding {skill_name} would improve this resume."

    return f"{cleaned_suggestion[:1].upper()}{cleaned_suggestion[1:]}."
