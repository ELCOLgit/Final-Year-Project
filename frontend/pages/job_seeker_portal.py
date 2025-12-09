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
st.title("Job Seeker Portal")
st.markdown("<h5 style='color:#001F3F;'>Upload your CV and explore your job matches.</h5>", unsafe_allow_html=True)
st.markdown("---")

# ======================
#   UPLOAD RESUME
# ======================
st.subheader("Upload Your CV")
uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"])

if uploaded_file:
    st.success(f"Selected: {uploaded_file.name}")

    if st.button("Send to Backend"):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        res = requests.post(f"{backend_url}/resumes/upload/", headers=headers, files=files)

        if res.status_code == 200:
            st.success("Uploaded successfully!")
            st.json(res.json())
        else:
            st.error(f"Upload failed: {res.text}")

st.markdown("---")

# ======================
#   VIEW MATCHES
# ======================
st.subheader("View Matches")

if st.button("Load Matches"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    res = requests.get(f"{backend_url}/matches/", headers=headers)

    if res.status_code != 200:
        st.error(res.text)
    else:
        matches = res.json()
        if not matches:
            st.info("No matches yet.")
        else:
            st.dataframe(pd.DataFrame(matches), use_container_width=True)

st.markdown("---")

# ======================
#   VIEW TOP MATCHES
# ======================
st.subheader("Your Top Matches")

if st.button("Load Top Matches"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    res = requests.get(f"{backend_url}/matches/top/", headers=headers)

    if res.status_code != 200:
        st.error(res.text)
    else:
        data = res.json()
        top = data.get("top_matches", [])

        if not top:
            st.info("No top matches yet.")
        else:
            st.success("Here are your top matches!")
            st.dataframe(pd.DataFrame(top), use_container_width=True)

# Logout
if st.button("Logout"):
    st.session_state.clear()
    st.rerun()
