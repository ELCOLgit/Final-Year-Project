import os
import re

import pandas as pd
import requests
import streamlit as st


def highlight_keywords(text, keywords):
    if not text:
        return "No text available."

    escaped = [re.escape(keyword) for keyword in keywords]
    if not escaped:
        return text

    pattern = r"(?i)(" + "|".join(escaped) + ")"
    return re.sub(pattern, r"<mark style='background-color:#fde68a;'>\1</mark>", text)


def fetch_json(url, headers=None, timeout=20):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json(), None
        return None, response.text
    except requests.RequestException:
        return None, "backend unavailable"


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
    score = float(candidate.get("score", 0.0))
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
                score {score:.3f}
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

# load page data
jobs, jobs_error = fetch_json(f"{backend_url}/jobs/")
resumes, resumes_error = fetch_json(f"{backend_url}/resumes/")

jobs = jobs or []
resumes = resumes or []

latest_job_title = jobs[0]["title"] if jobs else "none yet"
selected_resume_data = None
candidate_rankings = []
dashboard_rankings = []

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

dashboard_tab, ranking_tab, ai_tab = st.tabs(["Dashboard", "Ranking", "AI Assistant"])

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
        chart_left, chart_right = st.columns(2, gap="large")

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
                        "score": [item["score"] for item in dashboard_rankings[:5]],
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
                ranking_job_id = st.selectbox(
                    "Selected job",
                    [job["id"] for job in jobs],
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
            resume_ids = [resume["id"] for resume in resumes]
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
            selected_resume_id = st.selectbox(
                "Candidate context",
                [None] + [resume["id"] for resume in resumes],
                format_func=lambda value: "no candidate selected" if value is None else next(
                    resume["filename"] for resume in resumes if resume["id"] == value
                ),
                key="ai_resume_id",
            )

        st.markdown("<div class='field-gap'></div>", unsafe_allow_html=True)

        if jobs:
            selected_job_id = st.selectbox(
                "Job context",
                [None] + [job["id"] for job in jobs],
                format_func=lambda value: "no job selected" if value is None else next(
                    job["title"] for job in jobs if job["id"] == value
                ),
                key="ai_job_id",
            )

        st.markdown("<div class='field-gap'></div>", unsafe_allow_html=True)

        recruiter_question = st.text_input(
            "Ask a question",
            placeholder="what are the skills in this cv?",
            key="ai_question",
        )

        st.markdown("<div class='field-gap'></div>", unsafe_allow_html=True)

        if st.button("Ask recruiter AI", use_container_width=True):
            if not recruiter_question.strip():
                st.warning("please enter a question first")
            else:
                try:
                    response = requests.post(
                        f"{backend_url}/recruiter-ai/query/",
                        headers=headers,
                        json={
                            "question": recruiter_question,
                            "resume_id": selected_resume_id,
                            "job_id": selected_job_id,
                        },
                        timeout=30,
                    )
                    if response.status_code == 200:
                        st.session_state["recruiter_ai_answer"] = response.json().get("answer", "")
                    else:
                        st.error(response.text)
                except requests.RequestException:
                    st.error("backend unavailable")

        if st.session_state.get("recruiter_ai_answer"):
            st.markdown(
                (
                    "<div style='background:#ffffff; border-radius:10px; padding:1rem; "
                    "border:1px solid #e5e7eb; text-align:left;'>"
                    f"{st.session_state['recruiter_ai_answer']}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

st.markdown("---")

# logout button
if st.button("Logout"):
    # clear login data and send user back to the home page
    st.session_state.clear()
    st.switch_page("pages/home.py")
