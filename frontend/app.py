import streamlit as st
import requests
import os

def navigate_to(page_name: str):
    st.session_state["redirect_to"] = page_name
    st.rerun()


# === Load Styling ===
css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Page Setup ===
st.set_page_config(page_title="AI Career Advisor", page_icon="🧠", layout="wide")
backend_url = "http://127.0.0.1:8000"

# === Session State ===
if "token" not in st.session_state:
    st.session_state["token"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None
if "view" not in st.session_state:
    st.session_state["view"] = "login"

# === Center Layout ===
col1, mid, col2 = st.columns([1, 2, 1])
with mid:
    st.title("AI Career Advisor")
    st.markdown(
        "<h5 style='text-align:center; color:#001F3F;'>Empowering your career journey with intelligent matching.</h5>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # === Navigation Buttons ===
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Login"):
            st.session_state["view"] = "login"
    with btn_col2:
        if st.button("Register"):
            st.session_state["view"] = "register"

    st.markdown("---")

    # === LOGIN ===
    if st.session_state["view"] == "login":
        st.subheader("Login")

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="Enter your email", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            login_submit = st.form_submit_button("Login")

            if login_submit:
                if email and password:
                    res = requests.post(f"{backend_url}/auth/login/", params={"email": email, "password": password})
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["token"] = data["access_token"]
                        st.session_state["role"] = data["role"]

                        st.success(f"Welcome back, {data['role'].capitalize()}!")
                        if data["role"] == "job_seeker":
                            st.switch_page("pages/job_seeker_portal.py")
                        elif data["role"] == "recruiter":
                            st.switch_page("pages/recruiter_portal.py")
                    else:
                        st.error("Invalid email or password. Please try again.")
                else:
                    st.warning("Please fill in both fields.")

        st.markdown(
            "<p style='text-align:center;'><a href='#' style='color:#FFD700;'>Forgot your password?</a></p>",
            unsafe_allow_html=True,
        )

    # === REGISTER ===
    elif st.session_state["view"] == "register":
        st.subheader("Create an Account")

        with st.form("register_form", clear_on_submit=False):
            name = st.text_input("Full Name", placeholder="e.g., John Doe")
            email = st.text_input("Email Address", placeholder="e.g., johndoe@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter a secure password")
            role_display = st.selectbox("Role", ["Job Seeker", "Recruiter"], index=0)
            role = "job_seeker" if role_display == "Job Seeker" else "recruiter"
            register_submit = st.form_submit_button("Register")

            if register_submit:
                if name and email and password:
                    res = requests.post(
                        f"{backend_url}/auth/register/",
                        params={"name": name, "email": email, "password": password, "role": role},
                    )
                    if res.status_code == 200:
                        st.success("Account created successfully! You can now log in.")
                        st.session_state["view"] = "login"
                    elif res.status_code == 400:
                        st.warning("This email is already registered.")
                    else:
                        st.error("Registration failed. Please try again.")
                else:
                    st.warning("All fields are required.")

    # === Accessibility Footer ===
    st.markdown(
        """
        <div style='margin-top:2rem; text-align:center; font-size:0.9rem; color:#555;'>
        <strong>Accessibility:</strong> This form supports keyboard navigation and screen readers.
        Use <kbd>Tab</kbd> to move between fields and <kbd>Enter</kbd> to submit.
        </div>
        """,
        unsafe_allow_html=True,
    )
