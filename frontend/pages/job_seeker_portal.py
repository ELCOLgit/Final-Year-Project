import os
import re

import pandas as pd
import requests
import streamlit as st


# helper to highlight important keywords in text blocks

def highlight_keywords(text, keywords):
    if not text:
        return "No text available."

    escaped = [re.escape(k) for k in keywords]
    if not escaped:
        return text

    pattern = r"(?i)(" + "|".join(escaped) + ")"
    return re.sub(pattern, r"<mark style='background-color:#ffeb3b;'>\1</mark>", text)


# load shared css file
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# set page settings
st.set_page_config(page_title="Job Seeker Portal", page_icon="??", layout="wide")
backend_url = "http://127.0.0.1:8000"


# block page if user is not logged in
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first.")
    st.stop()

# block page if logged user is not a job seeker
if st.session_state.get("role") != "job_seeker":
    st.error("Access denied.")
    st.stop()


token = st.session_state["token"]
headers = {"Authorization": f"Bearer {token}"}


# page header
st.title("Job Seeker Dashboard")
st.markdown(
    "<h5 style='color:#001F3F;'>Upload your CV, view matches, and compare job descriptions.</h5>",
    unsafe_allow_html=True,
)
st.markdown("---")


# section 1: upload resume
st.subheader(" Upload Your CV")
uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"])

if uploaded_file:
    st.success(f"Selected: {uploaded_file.name}")

    if st.button("Upload CV to System", use_container_width=True):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        res = requests.post(f"{backend_url}/resumes/upload/", headers=headers, files=files)

        if res.status_code == 200:
            st.success("Uploaded successfully!")
            st.json(res.json())
        else:
            st.error(f"Upload failed: {res.text}")

st.markdown("---")


# section 2: load all matches
st.subheader(" Your Matches")

if st.button("Load All Matches", use_container_width=True):
    res = requests.get(f"{backend_url}/matches/", headers=headers)

    if res.status_code != 200:
        st.error(res.text)
    else:
        matches = res.json()
        if not matches:
            st.info("No matches yet. Make sure a recruiter has generated them.")
        else:
            st.success("Matches Loaded!")
            df = pd.DataFrame(matches)
            st.dataframe(df, use_container_width=True)

st.markdown("---")


# section 3: top matches + faiss search + compare
st.subheader(" Your Top Matches")

# toggle this section on when user clicks
if st.button("Show Top Matches", use_container_width=True):
    st.session_state["show_top_matches"] = True

if st.session_state.get("show_top_matches"):
    # load top matches and user resumes to map filename -> resume_id
    top_res = requests.get(f"{backend_url}/matches/top/", headers=headers)
    resumes_res = requests.get(f"{backend_url}/resumes/", headers=headers)

    if top_res.status_code != 200:
        st.error(top_res.text)
    elif resumes_res.status_code != 200:
        st.error(resumes_res.text)
    else:
        top_matches = top_res.json().get("top_matches", [])
        resumes = resumes_res.json()
        resume_id_by_filename = {r["filename"]: r["id"] for r in resumes}

        if not top_matches:
            st.info("No top matches yet.")
        else:
            st.success("Here are your strongest matches!")
            st.dataframe(pd.DataFrame(top_matches), use_container_width=True)

            # user picks a top match, then clicks button to call /matches/search/{resume_id}
            selected_top_match = st.selectbox(
                "click a top match to load search results",
                top_matches,
                format_func=lambda x: f"{x.get('job_title', 'job')} (score: {x.get('score', 0):.3f})",
            )

            selected_resume_name = selected_top_match.get("resume")
            selected_resume_id = resume_id_by_filename.get(selected_resume_name)

            if st.button("Load Search Results", use_container_width=True):
                if not selected_resume_id:
                    st.error("Could not find resume id for this match.")
                else:
                    search_res = requests.get(
                        f"{backend_url}/matches/search/{selected_resume_id}",
                        headers=headers,
                    )

                    if search_res.status_code != 200:
                        st.error(search_res.text)
                    else:
                        st.session_state["search_resume_id"] = selected_resume_id
                        st.session_state["search_matches"] = search_res.json()


# show faiss search results if they were loaded
search_matches = st.session_state.get("search_matches", [])
search_resume_id = st.session_state.get("search_resume_id")

if search_resume_id and search_matches is not None:
    st.markdown("### search results")

    if not search_matches:
        st.info("No search results to show.")
    else:
        for i, match in enumerate(search_matches):
            # show title + similarity score for each match
            title = match.get("title", "unknown")
            score = float(match.get("similarity_score", 0.0))
            job_id = match.get("job_id")

            st.markdown(f"**job title:** {title}")
            st.write(f"similarity score: {score:.3f}")

            # when user clicks this, we show cv text vs job description
            if st.button("compare cv text vs job description", key=f"compare_btn_{i}"):
                st.session_state["compare_job_id"] = job_id
                st.session_state["compare_job_title"] = title


# show compare panel when a compare button was clicked
compare_job_id = st.session_state.get("compare_job_id")
compare_job_title = st.session_state.get("compare_job_title", "selected job")

if compare_job_id and search_resume_id:
    resume_res = requests.get(f"{backend_url}/resumes/{search_resume_id}", headers=headers)
    job_res = requests.get(f"{backend_url}/jobs/{compare_job_id}")

    if resume_res.status_code == 200 and job_res.status_code == 200:
        resume_text = resume_res.json().get("text_content", "")
        job_text = job_res.json().get("description", "")

        # simple keyword list for highlighting overlap
        keywords = [
            "python", "sql", "analysis", "developer", "machine learning",
            "nlp", "cloud", "react", "backend", "frontend"
        ]

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### your cv text")
            # put resume text inside a scrollable box so long cvs stay readable
            st.markdown(
                (
                    "<div style='height:420px; overflow-y:auto; border:1px solid #d9d9d9; "
                    "border-radius:8px; padding:12px; background:#ffffff; white-space:pre-wrap;'>"
                    f"{highlight_keywords(resume_text, keywords)}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        with col_b:
            st.markdown(f"### job description: {compare_job_title}")
            # put job text inside a scrollable box and highlight keywords too
            st.markdown(
                (
                    "<div style='height:420px; overflow-y:auto; border:1px solid #d9d9d9; "
                    "border-radius:8px; padding:12px; background:#ffffff; white-space:pre-wrap;'>"
                    f"{highlight_keywords(job_text, keywords)}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
    else:
        st.error("Could not load resume/job text for comparison.")


st.markdown("---")


# logout button
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()
