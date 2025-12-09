import streamlit as st
import os
import requests
import pandas as pd

# === Load Styling ===
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Page Config ===
st.set_page_config(page_title="Recruiter Portal", page_icon="💼", layout="wide")
backend_url = "http://127.0.0.1:8000"

# === Auth and Role Check ===
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first to access your portal.")
    if st.button("Back to Login"):
        st.rerun()
    st.markdown("<meta http-equiv='refresh' content='1; url=/'>", unsafe_allow_html=True)
    st.stop()

if st.session_state.get("role") != "recruiter":
    st.error("Access denied. Only recruiters can access this page.")
    if st.button("Return to your portal"):
        if st.session_state.get("role") == "job_seeker":
            st.switch_page("pages/job_seeker_portal.py")
        else:
            st.rerun()
    st.stop()

# === Header ===
st.title("Recruiter Dashboard")
st.markdown(
    "<h5 style='color:#001F3F;'>Manage job postings and view matches for applicants.</h5>",
    unsafe_allow_html=True
)


# === Upload Job Posting ===
st.markdown("---")
st.subheader("Upload a New Job Posting")

with st.form("job_form"):
    title = st.text_input("Job Title", placeholder="e.g., Software Engineer Intern")
    description = st.text_area("Job Description", height=150, placeholder="Enter job description here...")
    submit_job = st.form_submit_button("Upload Job Posting")

    if submit_job:
        if title and description:
            data = {"title": title, "description": description}
            headers = {
            "Authorization": f"Bearer {st.session_state['token']}"
            }   
            try:
                res = requests.post(
                    f"{backend_url}/jobs/upload/",
                    data=data,
                    headers=headers
                    )
                if res.status_code == 200:
                    st.success("Job posted successfully!")
                    st.json(res.json())
                else:
                    st.error(f"Upload failed: {res.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure FastAPI is running.")
        else:
            st.warning("Please fill in both title and description fields.")

# === View All Jobs ===
st.markdown("---")
st.subheader("View All Job Postings")

if st.button("Load All Jobs"):
    try:
        res = requests.get(f"{backend_url}/jobs/")
        if res.status_code == 200:
            jobs = res.json()
            if not jobs:
                st.info("No job postings found yet.")
            else:
                df_jobs = pd.DataFrame(jobs)
                st.dataframe(df_jobs, use_container_width=True)
        else:
            st.error(f"Error fetching jobs: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")

# === View Matches ===
st.markdown("---")
st.subheader("View Candidate Matches")

if st.button("Generate & View Matches"):
    try:
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        res = requests.post(f"{backend_url}/generate/matches/", headers=headers)
        if res.status_code == 200:
            result = res.json()
            st.success("Match generation complete!")
            st.json(result)
        else:
            st.error(f"Error generating matches: {res.text}")

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
# === Logout ===
st.markdown("---")
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()
# === Accessibility Footer ===
st.markdown(
    """
    <div style='margin-top:2rem; text-align:center; font-size:0.9rem; color:#555;'>
    <strong>Accessibility:</strong> Use <kbd>Tab</kbd> to move through upload and buttons.
    High contrast colors are enabled for better readability.
    </div>
    """,
    unsafe_allow_html=True,
)
