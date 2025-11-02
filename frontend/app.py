import streamlit as st
import requests

st.set_page_config(page_title="AI Career Advisor", page_icon="🧠", layout="wide")

st.title("AI Career Advisor")
st.write("Upload your CV to receive AI-driven feedback and career insights.")

uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"])

if uploaded_file is not None:
    st.success(f"Uploaded: {uploaded_file.name}")

    if st.button("Send to Backend"):
        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        response = requests.post("http://127.0.0.1:8000/upload-cv/", files=files)

        if response.status_code == 200:
            st.json(response.json())
        else:
            st.error("Upload failed. Please try again.")
