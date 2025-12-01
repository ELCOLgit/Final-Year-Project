import streamlit as st
import os
from components.navbar import navbar

st.set_page_config(page_title="AI Career Advisor", page_icon="🧠", layout="wide")

# Load CSS
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

navbar(show_auth_buttons=True)

# === HERO SECTION ===
st.markdown("""
    <div style="width:100%; background-color:#e5e5e5; padding:5rem 0; text-align:center;">
        <div style="max-width:600px; margin:auto;">
            <img src="https://img.icons8.com/ios/200/000000/picture.png"
                 style="opacity:0.4;">
            <h2 style="color:#555; margin-top:2rem;">
                Discover Smarter Career Opportunities
            </h2>
            <p style="color:#666; font-size:1.1rem;">
                Upload your CV to receive fair, AI-powered job matches and insights.
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

# === FEATURES SECTION ===
col1, col2, col3 = st.columns(3)

with col1:
    st.image("https://img.icons8.com/ios-filled/100/CCCCCC/image.png")
    st.write("Lorem ipsum dolor sit amet et delectus accommodare his")

with col2:
    st.image("https://img.icons8.com/ios-filled/100/CCCCCC/image.png")
    st.write("Lorem ipsum dolor sit amet et delectus accommodare his consul")

with col3:
    st.image("https://img.icons8.com/ios-filled/100/CCCCCC/image.png")
    st.write("Lorem ipsum dolor sit amet et delectus")

# Footer
st.markdown("""
    <div style='text-align:center; margin-top:3rem; font-size:0.9rem; color:#666;'>
        © AI Career Advisor | Final Year Project
    </div>
""", unsafe_allow_html=True)
