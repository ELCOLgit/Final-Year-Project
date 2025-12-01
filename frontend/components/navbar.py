import streamlit as st

def navbar(show_auth_buttons=True):

    login_register_html = ""
    if show_auth_buttons:
        login_register_html = """
<a href="/login" target="_self" class="nav-btn">Login</a>
<a href="/register" target="_self" class="nav-btn">Register</a>
"""

    html = f"""<style>
code, pre {{ display: none !important; }}
</style>

<div class="navbar">
    <div class="navbar-title">AI Career Advisor</div>
    <div class="navbar-links">
        {login_register_html}
    </div>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)
