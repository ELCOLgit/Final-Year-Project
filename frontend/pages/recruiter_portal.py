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

# === Auth Check ===
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first.")
    st.stop()

if st.session_state.get("role") != "recruiter":
    st.error("Access denied.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

# === HEADER ===
st.title("Recruiter Dashboard")
st.markdown("<h5 style='color:#001F3F;'>Manage job postings and analyze AI-generated candidate matches.</h5>", unsafe_allow_html=True)

st.markdown("---")

# ====================================================
#            JOB POSTING UPLOAD SECTION
# ====================================================
st.subheader("📄 Create a New Job Posting")

col1, col2 = st.columns([1.5, 2])

with col1:
    st.markdown("### Job Details")

    with st.form("job_form"):
        title = st.text_input("Job Title", placeholder="e.g., Junior Backend Developer")
        description = st.text_area("Job Description", height=180, placeholder="Describe the skills, responsibilities, and qualifications...")

        submit_job = st.form_submit_button("Upload Job Posting")

        if submit_job:
            if title and description:
                res = requests.post(
                    f"{backend_url}/jobs/upload/",
                    data={"title": title, "description": description},
                    headers=headers
                )
                if res.status_code == 200:
                    st.success("Job posted successfully!")
                else:
                    st.error(res.text)
            else:
                st.warning("Please fill in all fields.")

with col2:
    st.markdown("### Recently Added Jobs")

    try:
        job_res = requests.get(f"{backend_url}/jobs/")
        if job_res.status_code == 200:
            jobs = job_res.json()
            if jobs:
                df_jobs = pd.DataFrame(jobs)
                st.dataframe(df_jobs, height=260, use_container_width=True)
            else:
                st.info("No job postings available.")
        else:
            st.error(job_res.text)
    except:
        st.error("Backend unavailable.")

st.markdown("---")

# ====================================================
#            MATCH GENERATION SECTION
# ====================================================
st.subheader("🔍 AI Match Generation")

st.markdown("Click below to analyze all candidate resumes and generate matching scores.")

if st.button("Generate & View Matches", use_container_width=True):
    try:
        res = requests.post(f"{backend_url}/generate/matches/", headers=headers)
        if res.status_code == 200:
            result = res.json()

            st.success("Match generation completed!")

            # metrics summary
            st.markdown("### Match Generation Summary")

            summary = {
                "Processed Resumes": result.get("processed_resumes"),
                "Processed Jobs": result.get("processed_jobs"),
                "New Matches": result.get("new_matches"),
                "Updated Matches": result.get("updated_matches"),
                "Removed Low Matches": result.get("removed_low_matches"),
                "Threshold": result.get("threshold")
            }

            df_summary = pd.DataFrame(summary.items(), columns=["Metric", "Value"])
            st.table(df_summary)

            with st.expander("🔎 Raw Match Generation Output (Debug)"):
                st.json(result)

        else:
            st.error(f"Error generating matches: {res.text}")

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend.")

st.markdown("---")

# LOGOUT
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()

st.markdown("""
<div style='margin-top:2rem; text-align:center; font-size:0.9rem; color:#555;'>
<strong>Accessibility:</strong> Fully keyboard navigable. High-contrast mode supported.
</div>
""", unsafe_allow_html=True)
