import streamlit as st
import requests
import os
import pandas as pd

# === Styling ===
css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Page setup ===
st.set_page_config(page_title="AI Career Advisor", page_icon="🧠", layout="wide")
backend_url = "http://127.0.0.1:8000"

# === Header ===
st.title("AI Career Advisor")
st.write("Upload your CV to receive AI-driven feedback and career insights.")

# === Section 1: Upload CV ===
uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"])

if uploaded_file is not None:
    st.success(f"Uploaded: {uploaded_file.name}")

    if st.button("Send to Backend"):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        try:
            response = requests.post(f"{backend_url}/resumes/upload/", files=files)
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.error("Upload failed. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend. Make sure FastAPI is running.")
            
# === Section2: Job Posting Upload ===
st.markdown("---")
st.subheader("Upload a Job Posting")

with st.form("job_form"):
    job_title = st.text_input("Job Title", placeholder="e.g., Software Engineer Intern")
    job_description = st.text_area("Job Description", height=150, placeholder="Enter job description here...")
    submitted = st.form_submit_button("Send to Backend")

    if submitted:
        if job_title and job_description:
            data = {"title": job_title, "description": job_description}
            try:
                res = requests.post("http://127.0.0.1:8000/jobs/upload/", data=data)
                if res.status_code == 200:
                    st.success("Job posted successfully!")
                    st.json(res.json())
                else:
                    st.error(f"Upload failed: {res.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure FastAPI is running.")
        else:
            st.warning("Please fill in both title and description.")

# === Section 3: View Job Postings ===
st.markdown("---")
st.subheader("View All Job Postings")

if st.button("Load Job Postings"):
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
            st.error(f"Error fetching job postings: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
        
# === Section 4: Generate Matches ===
st.markdown("---")
st.subheader("Generate Matches Between Resumes and Jobs")

if st.button("Generate Matches"):
    try:
        res = requests.post(f"{backend_url}/generate/matches/")
        if res.status_code == 200:
            data = res.json()["generated_matches"]

            if not data:
                st.info("No matches were created or updated.")
            else:
                st.success("Matches generated successfully!")
                df_matches = pd.DataFrame(data)
                st.dataframe(df_matches, use_container_width=True)
        else:
            st.error(f"Error generating matches: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")


# === Section 5: View Matches ===
st.markdown("---")
st.subheader("View Existing Matches")

if st.button("Load Matches"):
    try:
        res = requests.get(f"{backend_url}/matches/")
        if res.status_code == 200:
            data = res.json()["matches"]

            if not data:
                st.info("No matches found yet.")
            else:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
        else:
            st.error("Error fetching matches. Please check the backend.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")

# === Section 6: View Top Matches per CV ===
st.markdown("---")
st.subheader("Top Matches per Resume")

if st.button("Load Top Matches"):
    try:
        res = requests.get(f"{backend_url}/matches/top/")
        if res.status_code == 200:
            data = res.json()["top_matches"]
            if not data:
                st.info("No matches found yet. Try generating matches first.")
            else:
                st.success("Showing best job match for each uploaded resume.")
                df_top = pd.DataFrame(data)
                st.dataframe(df_top, use_container_width=True)
        else:
            st.error(f"Error fetching top matches: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")

# === Section 7: Recruiter Filtered Search ===
st.markdown("---")
st.subheader("Recruiter Match Filter")

col1, col2 = st.columns(2)
with col1:
    job_filter = st.text_input("Search by Job Title", placeholder="e.g., Data Science")
with col2:
    score_filter = st.slider("Minimum Match Score", 0.0, 1.0, 0.3, 0.05)

if st.button("Apply Filters"):
    try:
        params = {"job_title": job_filter, "min_score": score_filter}
        res = requests.get(f"{backend_url}/matches/filter/", params=params)
        if res.status_code == 200:
            data = res.json()["filtered_matches"]
            if not data:
                st.info("No matches found for the selected filters.")
            else:
                st.success(f"Showing matches with score ≥ {score_filter}")
                df_filtered = pd.DataFrame(data)
                st.dataframe(df_filtered, use_container_width=True)
        else:
            st.error(f"Error fetching filtered matches: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
