import streamlit as st

# Disable sidebar / Streamlit default navigation
st.set_page_config(
    page_title="AI Career Advisor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.switch_page("pages/home.py")

