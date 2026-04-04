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
    percentage_score = context_data.get("percentage_score")
    rating_score = context_data.get("rating_score")
    match_label = context_data.get("match_label")
    best_candidate_name = context_data.get("best_candidate_name")
    best_candidate_score = context_data.get("best_candidate_score")
    best_candidate_percentage_score = context_data.get("best_candidate_percentage_score")
    best_candidate_rating_score = context_data.get("best_candidate_rating_score")
    best_candidate_match_label = context_data.get("best_candidate_match_label")

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
        if best_candidate_name and job_title and best_candidate_percentage_score is not None:
            responses = [
                f"Based on the stored match results, {best_candidate_name} is currently the top candidate for {job_title} with a {best_candidate_match_label} of {best_candidate_percentage_score} percent.",
                f"Looking at the saved rankings, {best_candidate_name} stands out for {job_title} with a rating of {best_candidate_rating_score} out of 10.",
                f"Right now, {best_candidate_name} appears to be the best fit for {job_title} with a score of {best_candidate_percentage_score} percent.",
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
        if percentage_score is not None and cv_skills and job_skills:
            shared_skills = [skill for skill in cv_skills if skill in job_skills]
            shared_text = _format_list(shared_skills[:3]) if shared_skills else "no direct skill overlap"
            responses = [
                f"{candidate_name} is a {match_label} for {job_title} with a score of {percentage_score} percent, based on overlap in skills such as {shared_text}.",
                f"The score for {candidate_name} is {rating_score} out of 10 for {job_title}, with shared skills including {shared_text}.",
                f"{candidate_name} has a {match_label} for {job_title} because the CV aligns with the role in areas like {shared_text}.",
            ]
            return random.choice(responses)
        if percentage_score is not None:
            responses = [
                f"{candidate_name} currently has a {match_label} for {job_title} with a score of {percentage_score} percent.",
                f"The saved score for {candidate_name} against {job_title} is {rating_score} out of 10.",
                f"Right now, {candidate_name} has a match score of {percentage_score} percent for {job_title}.",
            ]
            return random.choice(responses)
        return f"I could not find a saved match score for {candidate_name} and {job_title}."

    if percentage_score is not None and job_title != "this role":
        responses = [
            f"{candidate_name} currently has a {match_label} for {job_title} with a score of {percentage_score} percent.",
            f"The current rating for {candidate_name} and {job_title} is {rating_score} out of 10.",
            f"For {job_title}, {candidate_name} has a saved score of {percentage_score} percent.",
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

    # step 5: count the main values used in scoring
    match_count = len(matching_skills)
    missing_count = len(missing_skills)
    total_job_skills = len(job_skills)

    print("match count:", match_count)
    print("missing count:", missing_count)
    print("total job skills:", total_job_skills)

    # step 6: create the base score from job skill coverage
    if total_job_skills > 0:
        base_score = match_count / total_job_skills
    else:
        base_score = 0.0

    # step 7: add a small bonus for stronger overlap
    bonus = 0.0
    if match_count >= 5:
        bonus = 0.15
    elif match_count >= 3:
        bonus = 0.10
    elif match_count >= 1:
        bonus = 0.05

    # step 8: add a small penalty for too many missing skills
    penalty = 0.0
    if missing_count >= 6:
        penalty = 0.10
    elif missing_count >= 4:
        penalty = 0.05

    # step 9: combine everything into the final score
    score = base_score + bonus - penalty

    # keep the score between 0 and 1
    if score > 1:
        score = 1.0
    if score < 0:
        score = 0.0

    # create simpler score formats for the ui
    percentage_score = round(score * 100)
    rating_score = round(score * 10)

    # add a simple label for the match strength
    if score >= 0.75:
        match_label = "strong match"
    elif score >= 0.45:
        match_label = "moderate match"
    else:
        match_label = "weak match"

    print("base score:", float(base_score))
    print("bonus:", float(bonus))
    print("penalty:", float(penalty))
    print("score:", float(score))
    print("percentage score:", percentage_score)
    print("rating score:", rating_score)
    print("match label:", match_label)

    # step 10: return all results in one dictionary
    return {
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "score": float(score),
        "percentage_score": percentage_score,
        "rating_score": rating_score,
        "match_label": match_label,
    }


def explain_score(matching_skills, missing_skills, score, percentage_score, rating_score, match_label):
    # count the number of matching and missing skills
    matching_count = len(matching_skills or [])
    missing_count = len(missing_skills or [])

    # build a more natural explanation using the new score fields
    if match_label == "strong match":
        if missing_count == 0:
            return (
                f"this candidate is a strong match with a score of {percentage_score} percent "
                f"and a rating of {rating_score} out of 10. they match {matching_count} important "
                f"skills and meet most of the main job requirements."
            )
        return (
            f"this candidate is a strong match with a score of {percentage_score} percent "
            f"and a rating of {rating_score} out of 10. they match {matching_count} important "
            f"skills and are only missing {missing_count} skills from the job."
        )

    if match_label == "moderate match":
        return (
            f"this candidate is a moderate match with a score of {percentage_score} percent "
            f"and a rating of {rating_score} out of 10. they match {matching_count} important "
            f"skills but are missing {missing_count} skills from the job."
        )

    return (
        f"this candidate is a weak match with a score of {percentage_score} percent "
        f"and a rating of {rating_score} out of 10. they match {matching_count} important "
        f"skills and are missing {missing_count} skills from the job."
    )


def generate_match_explanation(cv_text, job_text):
    # run the multi-step analysis first
    analysis = multi_step_match_analysis(cv_text, job_text)

    # get the main values from the analysis
    matching_skills = analysis.get("matching_skills", [])
    missing_skills = analysis.get("missing_skills", [])
    score = analysis.get("score", 0.0)
    percentage_score = analysis.get("percentage_score", 0)
    rating_score = analysis.get("rating_score", 0)
    match_label = analysis.get("match_label", "weak match")

    # build readable skill text
    matching_text = _format_list(matching_skills[:3])
    missing_text = _format_list(missing_skills[:3])

    # use the simpler score explanation if we have no skill text
    if not matching_skills and not missing_skills:
        return explain_score(
            matching_skills,
            missing_skills,
            score,
            percentage_score,
            rating_score,
            match_label,
        )

    if matching_text and missing_text:
        return (
            f"this candidate is a {match_label} with a score of {rating_score} out of 10, "
            f"or {percentage_score} percent. they match {matching_text}, but are missing "
            f"{missing_text}."
        )

    if matching_text:
        return (
            f"this candidate is a {match_label} with a score of {rating_score} out of 10, "
            f"or {percentage_score} percent. they match {matching_text} and cover most of the "
            f"main job requirements."
        )

    return (
        f"this candidate is a {match_label} with a score of {rating_score} out of 10, "
        f"or {percentage_score} percent. they are missing {missing_text}, which lowers the match."
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
