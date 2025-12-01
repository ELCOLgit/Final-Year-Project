import streamlit as st
import requests
import os
from components.navbar import navbar
navbar(show_auth_buttons=False)

st.set_page_config(page_title="Login - AI Career Advisor", page_icon="🔑", layout="centered")
backend_url = "http://127.0.0.1:8000"

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>LOGIN</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Welcome back! Please enter your credentials.</p>", unsafe_allow_html=True)

with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    remember = st.checkbox("Remember me?")
    login_submit = st.form_submit_button("LOGIN")

    if login_submit:
        if email and password:
            res = requests.post(f"{backend_url}/auth/login/", params={"email": email, "password": password})
            if res.status_code == 200:
                data = res.json()
                st.session_state["token"] = data["access_token"]
                st.session_state["role"] = data["role"]
                st.success("Login successful!")
                if data["role"] == "job_seeker":
                    st.switch_page("pages/job_seeker_portal.py")
                else:
                    st.switch_page("pages/recruiter_portal.py")
            else:
                st.error("Invalid email or password.")
        else:
            st.warning("Please fill in all fields.")

st.markdown("<p style='text-align:center;'><a href='#' style='color:#FF4081;'>Forgot Password?</a></p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col2:
    st.markdown("<p style='text-align:center;'>OR</p>", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center;'>
    <img src='https://img.icons8.com/color/48/google-logo.png' width='35' style='margin:5px;'>
    <img src='https://img.icons8.com/color/48/facebook-new.png' width='35' style='margin:5px;'>
    <img src='https://img.icons8.com/color/48/linkedin.png' width='35' style='margin:5px;'>
</div>
""", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;'>Need an account? <a href='register' style='color:#FF4081;'>SIGN UP</a></p>", unsafe_allow_html=True)
