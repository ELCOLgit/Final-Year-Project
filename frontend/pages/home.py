import streamlit as st
import os
import base64
from components.navbar import navbar


st.set_page_config(page_title="AI Career Advisor", page_icon="🧠", layout="wide")

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

navbar(show_auth_buttons=True)

# === Helper to Convert Image to Base64 ===
def get_base64(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode()

# === Image Paths ===
assets_path = os.path.join(os.path.dirname(__file__), "..", "assets")
bg_img_path = os.path.join(assets_path, "bg_home.png")
feature_ai = os.path.join(assets_path, "feature_ai.png")
feature_person = os.path.join(assets_path, "feature_person.png")
feature_trust = os.path.join(assets_path, "feature_trust.png")

# Convert BG image to base64 for CSS
bg_base64 = get_base64(bg_img_path)


# =========================================================
# HERO SECTION WITH BACKGROUND IMAGE (FULLY WORKING)
# =========================================================
st.markdown(
    f"""
    <div style="
        width: 100%;
        padding: 6rem 0;
        background-image: url('data:image/png;base64,{bg_base64}');
        background-size: cover;
        background-position: center;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 3rem;
    ">
        <div style="
            max-width: 700px;
            margin: auto;
            background: rgba(255,255,255,0.70);
            padding: 2.5rem;
            border-radius: 15px;
            backdrop-filter: blur(4px);
        ">
            <h1 style="color:#001F3F; font-size:2.5rem; font-weight:700;">
                Discover Smarter Career Opportunities
            </h1>
            <p style="color:#222; font-size:1.2rem;">
                Upload your CV to receive fair, AI-powered job matches and insights.
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# FEATURE SECTION 
# =========================================================
st.markdown(
    """
    <h2 style='text-align:center; margin-top:2rem;'>Explore the Platform</h2>
    """,
    unsafe_allow_html=True
)


import base64

def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def feature_card(image_path, title, text):
    img_b64 = img_to_base64(image_path)

    return f"""
    <div style="
        background:#f5f5f5;
        border-radius:15px;
        padding:25px;
        width:100%;
        text-align:center;
        box-shadow:0 2px 6px rgba(0,0,0,0.05);
    ">
        <img src="data:image/png;base64,{img_b64}" style="width:90px; margin-bottom:15px;">
        <h4 style="margin:0; color:#001F3F;">{title}</h4>
        <p style="margin-top:8px; color:#555; font-size:0.95rem;">
            {text}
        </p>
    </div>
    """


col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        feature_card(
            feature_ai,
            "AI-Powered Matching",
            "AI-powered matching system tailored to your career goals."
        ),
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        feature_card(
            feature_person,
            "Personalized Insights",
            "Personalized job recommendations based on your skills."
        ),
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        feature_card(
            feature_trust,
            "Fair & Transparent",
            "Transparent and bias-free evaluation across all resumes."
        ),
        unsafe_allow_html=True
    )


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    """
    <div style='text-align:center; margin-top:4rem; font-size:0.9rem; color:#666;'>
        © AI Career Advisor | Final Year Project
    </div>
    """,
    unsafe_allow_html=True,
)
