import os
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# add the project root so backend imports work when streamlit runs this page
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.services.cvService import (
    compare_matching_methods,
    generate_match_explanation,
    multi_step_match_analysis,
)


def highlight_keywords(text, keywords):
    if not text:
        return "No text available."

    escaped = [re.escape(keyword) for keyword in keywords]
    if not escaped:
        return text

    pattern = r"(?i)(" + "|".join(escaped) + ")"
    return re.sub(pattern, r"<mark style='background-color:#fde68a;'>\1</mark>", text)


def format_skills(skills):
    # show skill lists in a simple readable way
    if not skills:
        return "none"
    return ", ".join(skills)


def get_match_label(score):
    # use the final score to pick a simple label
    if score >= 0.75:
        return "strong match"
    if score >= 0.5:
        return "moderate match"
    return "weak match"


def fetch_json(url, headers=None, timeout=20):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json(), None
        return None, response.text
    except requests.RequestException:
        return None, "backend unavailable"


def extract_skills_from_text(text):
    # use the same small skill list as the backend logic
    known_skills = [
        "python",
        "sql",
        "fastapi",
        "excel",
        "cloud",
        "react",
        "machine learning",
    ]

    lowered_text = (text or "").lower()
    found_skills = []

    for skill in known_skills:
        if skill in lowered_text:
            found_skills.append(skill)

    return found_skills


def get_top_resume_skills(resume_list, headers):
    # load each resume text and count how often each known skill appears
    skill_counter = Counter()

    for resume in resume_list:
        resume_id = resume.get("id")
        if resume_id is None:
            continue

        resume_data, resume_error = fetch_json(f"{backend_url}/resumes/{resume_id}", headers=headers)
        if resume_error or not resume_data:
            continue

        for skill in extract_skills_from_text(resume_data.get("text_content", "")):
            skill_counter[skill] += 1

    return skill_counter.most_common(10)


def summary_card(title, value, text):
    return f"""
    <div style="
        background:#f7f7f7;
        border:1px solid #eee;
        border-radius:12px;
        padding:1.5rem;
        min-height:150px;
        display:flex;
        flex-direction:column;
        justify-content:center;
        text-align:left;
    ">
        <div style="
            font-size:0.78rem;
            text-transform:uppercase;
            letter-spacing:0.08em;
            color:#6b7280;
            margin-bottom:0.6rem;
        ">{title}</div>
        <div style="
            font-size:2rem;
            font-weight:700;
            color:#111827;
            margin-bottom:0.5rem;
            line-height:1.1;
        ">{value}</div>
        <div style="
            font-size:0.9rem;
            color:#6b7280;
            line-height:1.4;
        ">{text}</div>
    </div>
    """


def ranking_card(candidate, rank_number):
    percentage_score = candidate.get("percentage_score", 0)
    rating_score = candidate.get("rating_score", 0)
    match_label = candidate.get("match_label", "no label")
    skill_text = ", ".join(candidate.get("skills", [])) or "no skills found"
    return f"""
    <div style="
        background:#ffffff;
        border-radius:10px;
        padding:1rem;
        margin-bottom:1rem;
        border:1px solid #e5e7eb;
        text-align:left;
    ">
        <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start;">
            <div style="text-align:left;">
                <div style="
                    font-size:0.8rem;
                    color:#6b7280;
                    margin-bottom:0.4rem;
                    text-transform:uppercase;
                    letter-spacing:0.06em;
                ">rank {rank_number}</div>
                <div style="font-size:1rem; font-weight:700; color:#111827; margin-bottom:0.4rem;">
                    {candidate["filename"]}
                </div>
                <div style="font-size:0.9rem; color:#6b7280;">
                    {skill_text}
                </div>
            </div>
            <div style="
                background:#dbeafe;
                color:#1d4ed8;
                border-radius:999px;
                padding:0.35rem 0.7rem;
                font-size:0.8rem;
                white-space:nowrap;
            ">
                {percentage_score}% | {rating_score}/10 | {match_label}
            </div>
        </div>
    </div>
    """


def get_unique_rankings(candidates):
    # keep the first result for each resume so duplicates do not show twice
    unique_candidates = []
    seen_resume_ids = set()

    for candidate in candidates:
        resume_id = candidate.get("resume_id")
        if resume_id in seen_resume_ids:
            continue

        seen_resume_ids.add(resume_id)
        unique_candidates.append(candidate)

    return unique_candidates


def unique_by_id(items, id_key):
    # keep only one item for each id in frontend lists
    unique_items = []
    seen_ids = set()

    for item in items:
        item_id = item.get(id_key)
        if item_id in seen_ids:
            continue

        seen_ids.add(item_id)
        unique_items.append(item)

    return unique_items


def load_comparison_results(job_id, candidates, headers):
    # load the selected job once and compare it with each candidate cv
    comparison_results = []
    job_data, job_error = fetch_json(f"{backend_url}/jobs/{job_id}")
    if job_error or not job_data:
        return [], job_error or "could not load job"

    job_text = job_data.get("description", "")

    for candidate in candidates:
        resume_id = candidate.get("resume_id")
        if resume_id is None:
            continue

        resume_data, resume_error = fetch_json(f"{backend_url}/resumes/{resume_id}", headers=headers)
        if resume_error or not resume_data:
            continue

        cv_text = resume_data.get("text_content", "")
        method_scores = compare_matching_methods(cv_text, job_text)
        analysis = multi_step_match_analysis(cv_text, job_text)
        embedding_score = method_scores.get("embedding_score", 0.0)

        # support both the old and new explanation function signatures
        try:
            explanation = generate_match_explanation(cv_text, job_text, embedding_score)
        except TypeError:
            explanation = generate_match_explanation(cv_text, job_text)

        comparison_results.append({
            "filename": candidate.get("filename", "unknown cv"),
            "resume_id": resume_id,
            "ats_score": method_scores.get("ats_score", 0.0),
            "tfidf_score": method_scores.get("tfidf_score", 0.0),
            "embedding_score": embedding_score,
            "match_label": get_match_label(embedding_score),
            "matching_skills": analysis.get("matching_skills", []),
            "missing_skills": analysis.get("missing_skills", []),
            "explanation": explanation,
        })

    return unique_by_id(comparison_results, "resume_id"), None


st.set_page_config(page_title="Recruiter Portal", page_icon="briefcase", layout="wide")

# load shared css file
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .section-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #111827;
        text-align: left;
        margin-bottom: 0.4rem;
    }
    .section-subtitle {
        font-size: 0.95rem;
        color: #6b7280;
        text-align: left;
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    .field-gap {
        height: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

backend_url = "http://127.0.0.1:8000"

# block page if user is not logged in
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first.")
    st.stop()

# block page if logged user is not a recruiter
if st.session_state.get("role") != "recruiter":
    st.error("Access denied.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

if "viewer_resume_id" not in st.session_state:
    st.session_state["viewer_resume_id"] = None

if "recruiter_ai_chat_history" not in st.session_state:
    st.session_state["recruiter_ai_chat_history"] = []

# load page data
jobs, jobs_error = fetch_json(f"{backend_url}/jobs/", headers=headers)
resumes, resumes_error = fetch_json(f"{backend_url}/resumes/")

jobs = unique_by_id(jobs or [], "id")
resumes = unique_by_id(resumes or [], "id")

# sort the main dropdown lists alphabetically before showing them
jobs = sorted(jobs, key=lambda item: item.get("title", "").lower())
resumes = sorted(resumes, key=lambda item: item.get("filename", "").lower())

latest_job_title = jobs[0]["title"] if jobs else "none yet"
selected_resume_data = None
candidate_rankings = []
dashboard_rankings = []
top_resume_skills = get_top_resume_skills(resumes, headers)

if jobs:
    dashboard_rankings_data, _ = fetch_json(
        f"{backend_url}/matches/by-job/{jobs[0]['id']}",
        headers=headers,
    )
    dashboard_rankings = get_unique_rankings(dashboard_rankings_data or [])

header_left, header_right = st.columns([12, 1])
with header_left:
    st.title("Recruiter Dashboard")
with header_right:
    # keep the same plain button style as the job seeker page
    if st.button("refresh", help="refresh data"):
        st.rerun()

dashboard_tab, ranking_tab, comparison_tab, ai_tab = st.tabs(["Dashboard", "Ranking", "Comparison", "AI Assistant"])

with dashboard_tab:
    with st.container():
        # show the main dashboard summary cards
        summary_col_1, summary_col_2, summary_col_3 = st.columns(3)

        with summary_col_1:
            st.markdown(
                summary_card("job postings", len(jobs), "roles currently available for ranking"),
                unsafe_allow_html=True,
            )

        with summary_col_2:
            st.markdown(
                summary_card("candidate cvs", len(resumes), "uploaded resumes in the system"),
                unsafe_allow_html=True,
            )

        with summary_col_3:
            st.markdown(
                summary_card("latest role", latest_job_title, "most recent job posting"),
                unsafe_allow_html=True,
            )

    st.markdown("---")

    with st.container():
        # add simple charts for the dashboard tab
        chart_left, chart_middle, chart_right = st.columns(3, gap="large")

        with chart_left:
            st.markdown("<div class='section-title'>System Overview</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-subtitle'>A quick count of roles and resumes in the platform.</div>",
                unsafe_allow_html=True,
            )

            overview_df = pd.DataFrame(
                {
                    "category": ["job postings", "candidate cvs"],
                    "count": [len(jobs), len(resumes)],
                }
            ).set_index("category")
            st.bar_chart(overview_df)

        with chart_middle:
            st.markdown("<div class='section-title'>Most Common Skills</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-subtitle'>Top 10 skills found across uploaded resumes.</div>",
                unsafe_allow_html=True,
            )

            if top_resume_skills:
                skills_df = pd.DataFrame(
                    {
                        "skill": [item[0] for item in top_resume_skills],
                        "count": [item[1] for item in top_resume_skills],
                    }
                ).set_index("skill")
                st.bar_chart(skills_df)
            else:
                st.info("no skills found yet")

        with chart_right:
            st.markdown("<div class='section-title'>Top Match Scores</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-subtitle'>Top ranked candidate scores for the latest job.</div>",
                unsafe_allow_html=True,
            )

            if dashboard_rankings:
                score_df = pd.DataFrame(
                    {
                        "candidate": [item["filename"] for item in dashboard_rankings[:5]],
                        "percentage score": [item.get("percentage_score", 0) for item in dashboard_rankings[:5]],
                    }
                ).set_index("candidate")
                st.bar_chart(score_df)
            else:
                st.info("no ranking data available yet")

with ranking_tab:
    with st.container():
        # keep the job posting and ranking tools in one tab
        workspace_left, workspace_right = st.columns(2, gap="large")

        with workspace_left:
            st.markdown("<div class='section-title'>Job Posting</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-subtitle'>Add a new role and reload the dashboard when you are ready.</div>",
                unsafe_allow_html=True,
            )

            with st.form("job_posting_form"):
                title = st.text_input("Job title", placeholder="e.g. junior backend developer")
                description = st.text_area(
                    "Job description",
                    height=220,
                    placeholder="add the responsibilities, skills, and requirements",
                )
                submit_job = st.form_submit_button("Upload job posting")

                if submit_job:
                    if not title or not description:
                        st.warning("please fill in the job title and description")
                    else:
                        try:
                            response = requests.post(
                                f"{backend_url}/jobs/upload/",
                                headers=headers,
                                data={"title": title, "description": description},
                                timeout=30,
                            )
                            if response.status_code == 200:
                                st.success("job posting uploaded successfully")
                                st.rerun()
                            else:
                                st.error(response.text)
                        except requests.RequestException:
                            st.error("backend unavailable")

        with workspace_right:
            st.markdown("<div class='section-title'>Candidate Ranking</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-subtitle'>Choose a job and review the top ranked candidates.</div>",
                unsafe_allow_html=True,
            )

            if jobs_error:
                st.error(jobs_error)
            elif not jobs:
                st.info("upload a job posting first to see candidate rankings")
            else:
                # sort job options alphabetically for the ranking dropdown
                ranking_job_ids = sorted(
                    [job["id"] for job in jobs],
                    key=lambda value: next(job["title"] for job in jobs if job["id"] == value).lower(),
                )
                ranking_job_id = st.selectbox(
                    "Selected job",
                    ranking_job_ids,
                    format_func=lambda value: next(job["title"] for job in jobs if job["id"] == value),
                    key="ranking_job_id",
                )

                ranking_data, ranking_error = fetch_json(
                    f"{backend_url}/matches/by-job/{ranking_job_id}",
                    headers=headers,
                )
                candidate_rankings = get_unique_rankings(ranking_data or [])

                if ranking_error:
                    st.error(ranking_error)
                elif not candidate_rankings:
                    st.info("no ranked candidates yet.")
                else:
                    ranking_resume_ids = [candidate["resume_id"] for candidate in candidate_rankings]
                    if st.session_state["viewer_resume_id"] not in ranking_resume_ids:
                        st.session_state["viewer_resume_id"] = ranking_resume_ids[0]

                    for rank_number, candidate in enumerate(candidate_rankings[:5], start=1):
                        st.markdown(ranking_card(candidate, rank_number), unsafe_allow_html=True)

    st.markdown("---")

    with st.container():
        # keep the cv viewer below the ranking tools
        st.markdown("<div class='section-title'>CV Viewer</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-subtitle'>Review the selected candidate cv with highlighted keywords.</div>",
            unsafe_allow_html=True,
        )

        if resumes_error:
            st.error(resumes_error)
        elif not resumes:
            st.info("no resumes uploaded yet")
        else:
            # sort candidate options alphabetically for the cv viewer
            resume_ids = sorted(
                [resume["id"] for resume in resumes],
                key=lambda value: next(resume["filename"] for resume in resumes if resume["id"] == value).lower(),
            )
            if st.session_state["viewer_resume_id"] not in resume_ids:
                st.session_state["viewer_resume_id"] = resume_ids[0]

            viewer_resume_id = st.selectbox(
                "Selected candidate",
                resume_ids,
                format_func=lambda value: next(resume["filename"] for resume in resumes if resume["id"] == value),
                key="viewer_resume_id",
            )

            selected_resume_data, resume_error = fetch_json(f"{backend_url}/resumes/{viewer_resume_id}")

            if resume_error:
                st.error(resume_error)
            elif selected_resume_data:
                keywords = [
                    "python",
                    "sql",
                    "fastapi",
                    "excel",
                    "cloud",
                    "react",
                    "machine learning",
                    "analysis",
                    "developer",
                    "backend",
                ]

                st.markdown(
                    (
                        "<div style='background:#ffffff; border-radius:10px; padding:1rem; "
                        "border:1px solid #e5e7eb; text-align:left; margin-bottom:1rem;'>"
                        f"<strong>filename:</strong> {selected_resume_data['filename']}<br>"
                        f"<strong>user id:</strong> {selected_resume_data['user_id']}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                highlighted_resume = highlight_keywords(selected_resume_data.get("text_content", ""), keywords)
                st.markdown(
                    (
                        "<div style='max-height:400px; overflow-y:auto; background:#ffffff; border-radius:10px; "
                        "padding:1rem; border:1px solid #e5e7eb; white-space:pre-wrap; text-align:left;'>"
                        f"{highlighted_resume}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

with comparison_tab:
    with st.container():
        # keep the comparison tools in their own tab
        st.markdown("<div class='section-title'>Candidate Comparison</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-subtitle'>Compare ats, tf-idf, embedding, and final match details for each candidate.</div>",
            unsafe_allow_html=True,
        )

        if jobs_error:
            st.error(jobs_error)
        elif not jobs:
            st.info("upload or import a job first to compare candidates")
        else:
            # sort job options alphabetically for the comparison dropdown
            comparison_job_ids = sorted(
                [job["id"] for job in jobs],
                key=lambda value: next(job["title"] for job in jobs if job["id"] == value).lower(),
            )
            comparison_job_id = st.selectbox(
                "Selected comparison job",
                comparison_job_ids,
                format_func=lambda value: next(job["title"] for job in jobs if job["id"] == value),
                key="comparison_job_id",
            )

            comparison_data, comparison_error = fetch_json(
                f"{backend_url}/matches/by-job/{comparison_job_id}",
                headers=headers,
            )
            comparison_candidates = get_unique_rankings(comparison_data or [])

            if comparison_error:
                st.error(comparison_error)
            elif not comparison_candidates:
                st.info("no candidate matches available for this job yet")
            else:
                comparison_results, load_error = load_comparison_results(
                    comparison_job_id,
                    comparison_candidates,
                    headers,
                )

                if load_error:
                    st.error(load_error)
                elif not comparison_results:
                    st.info("no comparison results available yet")
                else:
                    for result in comparison_results:
                        with st.container(border=True):
                            st.subheader(result["filename"])

                            # keep the summary compact so it is easy to scan
                            final_left, final_right = st.columns([2, 1], gap="medium")

                            with final_left:
                                st.markdown("**Final AI Match**")
                                st.metric(
                                    "Embedding Score",
                                    f"{round(result['embedding_score'] * 100)}%",
                                )

                            with final_right:
                                st.markdown("**Match Label**")
                                st.metric("Final Label", result["match_label"])

                            st.markdown("**Score Summary**")
                            score_col_1, score_col_2, score_col_3 = st.columns(3, gap="medium")
                            score_col_1.metric("ATS Score", f"{round(result['ats_score'] * 100)}%")
                            score_col_2.metric("TF-IDF Score", f"{round(result['tfidf_score'] * 100)}%")
                            score_col_3.metric("Embedding Score", f"{round(result['embedding_score'] * 100)}%")

                            # keep the detailed reasoning inside an expander
                            with st.expander("view details"):
                                st.markdown("**Matching Skills**")
                                st.write(format_skills(result["matching_skills"]))

                                st.markdown("**Missing Skills**")
                                st.write(format_skills(result["missing_skills"]))

                                st.markdown("**Explanation**")
                                st.write(result["explanation"])

with ai_tab:
    with st.container():
        # keep the ai tools inside their own tab
        st.markdown("<div class='section-title'>Recruiter AI</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-subtitle'>Ask simple questions about a selected cv or job.</div>",
            unsafe_allow_html=True,
        )

        selected_resume_id = None
        selected_job_id = None

        if resumes:
            # sort candidate options alphabetically for ai context
            ai_resume_ids = sorted(
                [resume["id"] for resume in resumes],
                key=lambda value: next(resume["filename"] for resume in resumes if resume["id"] == value).lower(),
            )
            selected_resume_id = st.selectbox(
                "Candidate context",
                [None] + ai_resume_ids,
                format_func=lambda value: "no candidate selected" if value is None else next(
                    resume["filename"] for resume in resumes if resume["id"] == value
                ),
                key="ai_resume_id",
            )

        st.markdown("<div class='field-gap'></div>", unsafe_allow_html=True)

        if jobs:
            # sort job options alphabetically for ai context
            ai_job_ids = sorted(
                [job["id"] for job in jobs],
                key=lambda value: next(job["title"] for job in jobs if job["id"] == value).lower(),
            )
            selected_job_id = st.selectbox(
                "Job context",
                [None] + ai_job_ids,
                format_func=lambda value: "no job selected" if value is None else next(
                    job["title"] for job in jobs if job["id"] == value
                ),
                key="ai_job_id",
            )

        st.markdown("<div class='field-gap'></div>", unsafe_allow_html=True)

        chat_container = st.container()

        with chat_container:
            for message in st.session_state["recruiter_ai_chat_history"]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        recruiter_question = st.chat_input("ask a question about the selected cv or job")

        if recruiter_question:
            cleaned_question = recruiter_question.strip()

            if not cleaned_question:
                st.warning("please enter a question first")
            else:
                st.session_state["recruiter_ai_chat_history"].append(
                    {"role": "user", "content": cleaned_question}
                )

                try:
                    response = requests.post(
                        f"{backend_url}/recruiter-ai/query/",
                        headers=headers,
                        json={
                            "question": cleaned_question,
                            "resume_id": selected_resume_id,
                            "job_id": selected_job_id,
                        },
                        timeout=30,
                    )
                    if response.status_code == 200:
                        assistant_answer = response.json().get("answer", "")
                        st.session_state["recruiter_ai_chat_history"].append(
                            {"role": "assistant", "content": assistant_answer}
                        )
                        st.rerun()
                    else:
                        st.error(response.text)
                except requests.RequestException:
                    st.error("backend unavailable")

st.markdown("---")

# logout button
if st.button("Logout"):
    # clear login data and send user back to the home page
    st.session_state.clear()
    st.switch_page("pages/home.py")
