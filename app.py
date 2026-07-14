# app.py
import streamlit as st
from dotenv import load_dotenv

from chat_ui import show_login_box
from src.auth import authenticate_tenant
from src.handlers import show_main_ui
from src.utils import init_chat_history

load_dotenv()
st.set_page_config(page_title="SalesBot", layout="wide")

# Initialize state
init_chat_history()
st.session_state.setdefault("tenant_id", None)
st.session_state.setdefault("gname", None)
st.session_state.setdefault("current_menu", "login")
st.session_state.setdefault("is_creator", False)

if st.session_state.tenant_id is None:
    show_login_box()
    st.title("🔒 Tenant Login")
    tname = st.text_input("Enter your Tenant ID (tname):", key="tenant_id_input")
    if st.button("Login", disabled=(tname.strip() == ""), key="login_btn"):
        if authenticate_tenant(tname):
            st.session_state.tenant_id = tname
            st.session_state.current_menu = "main"
            st.session_state.selected_main_menu_option = "Ask a Question"
            st.rerun()
        else:
            st.error("Invalid Tenant ID")
else:
    show_main_ui()
