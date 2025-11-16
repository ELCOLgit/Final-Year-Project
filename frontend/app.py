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
            response = requests.post(f"{backend_url}/upload-cv/", files=files)
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.error("Upload failed. Please try again.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend. Make sure FastAPI is running.")

# === Section 2: View Matches ===
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
