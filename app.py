import streamlit as st
from auth.auth_utils import init_session
from db.mongo_client import ensure_indexes

#  PAGE CONFIG  

st.set_page_config(
    page_title="Venuebase — RFP Responder",
    layout="wide",
    initial_sidebar_state="collapsed",
)


init_session()
ensure_indexes()

#  PAGE IMPORTS 


def load_login_page():
    from pages.login_page import render
    render()

def load_signup_page():
    from pages.signup_page import render
    render()

def load_dashboard_page():
    from pages.dashboard_page import render
    render()

def load_project_page():
    from pages.project_page import render
    render()

#  ROUTER

page = st.session_state.get("current_page", "login")

if page == "login":
    load_login_page()
elif page == "signup":
    load_signup_page()
elif page == "dashboard":
    if not st.session_state.get("logged_in"):
        st.session_state["current_page"] = "login"
        st.rerun()
    else:
        load_dashboard_page()
elif page == "project":
    if not st.session_state.get("logged_in"):
        st.session_state["current_page"] = "login"
        st.rerun()
    else:
        load_project_page()
else:
    st.session_state["current_page"] = "login"
    st.rerun()