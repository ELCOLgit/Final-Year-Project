import streamlit as st
import requests
import os
import pandas as pd
import re

# === Helper: Keyword Highlighting ===
def highlight_keywords(text, keywords):
    if not text:
        return "No text available."
    escaped = [re.escape(k) for k in keywords]
    if not escaped:
        return text
    pattern = r"(?i)(" + "|".join(escaped) + ")"
    return re.sub(pattern, r"<mark style='background-color:#ffeb3b;'>\1</mark>", text)

# === Styling ===
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Page Setup ===
st.set_page_config(page_title="Job Seeker Portal", page_icon="🎓", layout="wide")
backend_url = "http://127.0.0.1:8000"

# === Auth Check ===
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first.")
    st.stop()

if st.session_state.get("role") != "job_seeker":
    st.error("Access denied.")
    st.stop()

token = st.session_state["token"]
headers = {"Authorization": f"Bearer {token}"}

# === Header ===
st.title("Job Seeker Dashboard")
st.markdown("<h5 style='color:#001F3F;'>Upload your CV, view matches, and compare job descriptions.</h5>", unsafe_allow_html=True)
st.markdown("---")


# ===================================================================
#   SECTION 1 — UPLOAD RESUME
# ===================================================================
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


# ===================================================================
#   SECTION 2 — VIEW MATCHES
# ===================================================================
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


# ===================================================================
#   SECTION 3 — TOP MATCHES + COMPARISON VIEWER
# ===================================================================
st.subheader(" Your Top Matches")

# Button that toggles panel open
if st.button("Show Top Matches", use_container_width=True):
    st.session_state["show_top_matches"] = True

# Only render this section when toggled on
if st.session_state.get("show_top_matches"):

    # Load top matches
    res = requests.get(f"{backend_url}/matches/top/", headers=headers)

    if res.status_code != 200:
        st.error(res.text)
    else:
        data = res.json()
        top_matches = data.get("top_matches", [])

        if not top_matches:
            st.info("No top matches yet.")
        else:
            st.success("Here are your strongest matches!")
            df_top = pd.DataFrame(top_matches)
            st.dataframe(df_top, use_container_width=True)

            # Load all matches so we can map resume->id
            all_match_res = requests.get(f"{backend_url}/matches/", headers=headers)
            all_matches = all_match_res.json() if all_match_res.status_code == 200 else []

            # Let the user select a match
            selected = st.selectbox(
                "Select a Match to Compare:",
                top_matches,
                format_func=lambda x: f"{x['job_title']} (Score: {x['score']:.3f})"
            )

            # Find resume row
            resume_row = next((m for m in all_matches if m["resume"] == selected["resume"]), None)
            resume_id = resume_row["id"] if resume_row else None

            if not resume_id:
                st.error("Could not locate resume ID.")
            else:
                # Load resume text
                resume_details = requests.get(
                    f"{backend_url}/resumes/{resume_id}", headers=headers
                ).json()
                resume_text = resume_details.get("text_content", "")

                # Load job description
                job_info = requests.get(
                    f"{backend_url}/jobs/get-by-title/{selected['job_title']}"
                ).json()

                job_text = job_info.get("description") if job_info else ""

                # Highlight keywords
                keywords = [
                    "python", "sql", "analysis", "developer", "machine learning",
                    "nlp", "cloud", "react", "backend", "frontend"
                ]

                colA, colB = st.columns(2)

                with colA:
                    st.markdown("### Your Resume (Highlighted)")
                    st.markdown(
                        f"<div style='white-space:pre-wrap;'>{highlight_keywords(resume_text, keywords)}</div>",
                        unsafe_allow_html=True
                    )

                with colB:
                    st.markdown(f"### Job Description: {selected['job_title']}")
                    st.markdown(
                        f"<div style='white-space:pre-wrap;'>{highlight_keywords(job_text, keywords)}</div>",
                        unsafe_allow_html=True
                    )


st.markdown("---")


# ===================================================================
#   LOGOUT
# ===================================================================
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()
