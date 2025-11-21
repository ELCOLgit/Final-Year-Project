import streamlit as st
import requests
import os
import pandas as pd

# === Styling ===
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Page Setup ===
st.set_page_config(page_title="Job Seeker Portal", page_icon="🎓", layout="wide")
backend_url = "http://127.0.0.1:8000"

# === Auth and Role Check ===
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first to access your portal.")

    if st.button("Back to Login"):
        st.rerun()

    st.markdown(
        "<meta http-equiv='refresh' content='1; url=/'>",
        unsafe_allow_html=True,
    )
    st.stop()

if st.session_state.get("role") != "job_seeker":
    st.error("Access denied. Only job seekers can access this page.")
    if st.button("Return to your portal"):
        if st.session_state.get("role") == "recruiter":
            st.switch_page("pages/recruiter_portal")
        else:
            st.rerun()
    st.stop()

# === Header ===
st.title("Job Seeker Portal")
st.markdown("<h5 style='color:#001F3F;'>Welcome! Upload your CV and explore your top job matches.</h5>", unsafe_allow_html=True)


st.markdown("---")

# === Section 1: Upload Resume ===
st.subheader("Upload Your CV")
uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"])

if uploaded_file is not None:
    st.success(f"Uploaded: {uploaded_file.name}")
    if st.button("Send to Backend"):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        try:
            response = requests.post(f"{backend_url}/resumes/upload/", files=files)
            if response.status_code == 200:
                st.success("CV uploaded and processed successfully!")
                st.json(response.json())
            else:
                st.error("Upload failed. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend. Make sure FastAPI is running.")

st.markdown("---")

# === Section 2: View Matches ===
st.subheader("View Matches")

if st.button("Load Matches"):
    try:
        res = requests.get(f"{backend_url}/matches/")
        if res.status_code == 200:
            data = res.json()["matches"]
            if not data:
                st.info("No matches found yet. Try uploading your CV and generating matches.")
            else:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
        else:
            st.error("Error fetching matches. Please check the backend.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")

st.markdown("---")

# === Section 3: Top Matches per Resume ===
st.subheader("Your Top Matches")

if st.button("Load Top Matches"):
    try:
        res = requests.get(f"{backend_url}/matches/top/")
        if res.status_code == 200:
            data = res.json()["top_matches"]
            if not data:
                st.info("No matches found yet. Try generating matches first.")
            else:
                st.success("Here are your best job matches!")
                df_top = pd.DataFrame(data)
                st.dataframe(df_top, use_container_width=True)
        else:
            st.error(f"Error fetching top matches: {res.text}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Make sure FastAPI is running.")
        
st.markdown("---")

# === Logout ===
if st.button("Logout"):
    st.session_state.clear()
    st.success("You have been logged out.")
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
