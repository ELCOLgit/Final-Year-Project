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


# =======================================================================
#  SECTION 1 — JOB POSTING UPLOAD
# =======================================================================
st.subheader("📄 Create a New Job Posting")

col1, col2 = st.columns([1.5, 2])

with col1:
    st.markdown("### Job Details")

    with st.form("job_form"):
        title = st.text_input("Job Title", placeholder="e.g., Junior Backend Developer")
        description = st.text_area("Job Description", height=180,
                                   placeholder="Describe the skills, responsibilities, and qualifications...")

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


# =======================================================================
#  SECTION 2 — CANDIDATE LIST VIEW + RESUME VIEWER
# =======================================================================
st.subheader("🧑‍💼 Candidate List")

colA, colB = st.columns([1.3, 1.7])

with colA:
    st.markdown("### All Uploaded Candidate Resumes")

    try:
        res = requests.get(f"{backend_url}/resumes/")
        if res.status_code == 200:
            resumes = res.json()

            if not resumes:
                st.info("No resumes uploaded yet.")
                selected_resume = None
            else:
                df_resumes = pd.DataFrame(resumes)
                df_resumes = df_resumes.rename(columns={
                    "id": "Resume ID",
                    "filename": "Filename",
                    "upload_date": "Uploaded",
                    "user_id": "User ID"
                })

                # Dropdown to select resume
                selected_resume = st.selectbox(
                    "Select a candidate",
                    df_resumes["Resume ID"],
                    format_func=lambda x: f"Resume {x} — {df_resumes.loc[df_resumes['Resume ID'] == x, 'Filename'].values[0]}"
                )

                st.dataframe(df_resumes, height=260, use_container_width=True)

        else:
            st.error("Error loading resumes.")

    except:
        st.error("Backend unavailable.")
        selected_resume = None


with colB:
    st.markdown("### Resume Viewer")

    if selected_resume:
        try:
            # Get resume full details
            res_text = requests.get(f"{backend_url}/resumes/{selected_resume}")
            if res_text.status_code == 200:
                resume_data = res_text.json()

                st.markdown(f"**📄 Filename:** {resume_data['filename']}")
                st.markdown(f"**👤 Uploaded By (User ID):** {resume_data['user_id']}")
                st.markdown("---")

                st.subheader("Extracted Resume Text")
                st.text_area("", resume_data["text_content"], height=420)

            else:
                st.error("Error loading resume content.")

        except:
            st.error("Backend unavailable.")

st.markdown("---")


# =======================================================================
#  SECTION 3 — MATCH GENERATION
# =======================================================================
st.subheader("🔍 AI Match Generation")

st.markdown("Click below to analyze all candidate resumes and generate matching scores.")

if st.button("Generate & View Matches", use_container_width=True):
    try:
        res = requests.post(f"{backend_url}/generate/matches/", headers=headers)
        if res.status_code == 200:
            result = res.json()

            st.success("Match generation completed!")

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


# =======================================================================
#  LOGOUT
# =======================================================================
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()


st.markdown("""
<div style='margin-top:2rem; text-align:center; font-size:0.9rem; color:#555;'>
<strong>Accessibility:</strong> Fully keyboard navigable. High-contrast mode supported.
</div>
""", unsafe_allow_html=True)
