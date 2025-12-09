import streamlit as st
import requests
import os

st.set_page_config(page_title="Register - AI Career Advisor", page_icon="📝", layout="centered")
backend_url = "http://127.0.0.1:8000"

# Load CSS BEFORE navbar
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from components.navbar import navbar
navbar(show_auth_buttons=False)

st.markdown("<h2 style='text-align:center;'>SIGN UP</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Create your account to get started.</p>", unsafe_allow_html=True)

# -------------------------
# FORM (ONLY submit button allowed here)
# -------------------------
with st.form("register_form"):
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    role_display = st.selectbox("Role", ["Job Seeker", "Recruiter"])
    role = "job_seeker" if role_display == "Job Seeker" else "recruiter"

    submit = st.form_submit_button("SIGN UP")

    if submit:
        if name and email and password:
            res = requests.post(
                f"{backend_url}/auth/register/",
                params={"name": name, "email": email, "password": password, "role": role},
            )

            if res.status_code == 200:
                st.success("Successfully registered!")
            elif res.status_code == 400:
                st.warning("This email is already registered.")
            else:
                st.error("Registration failed. Try again.")
        else:
            st.warning("Please fill in all fields.")

# -------------------------
# BUTTON OUTSIDE THE FORM
# -------------------------
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Back to Login"):
    st.switch_page("pages/login.py")
