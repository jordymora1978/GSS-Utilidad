
import streamlit as st
from modulos.gestion_trm import mostrar_interfaz_trm

st.set_page_config(page_title="Gestión TRM", page_icon="💱", layout="wide")

# Verificar autenticación
try:
    from modulos.auth import is_logged_in, show_login_form
    if not is_logged_in():
        st.error("⛔ Debes iniciar sesión para acceder a esta página")
        show_login_form()
        st.stop()
except ImportError:
    st.warning("⚠️ Sistema de autenticación no disponible")

# Mostrar la interfaz de gestión de TRM
mostrar_interfaz_trm()
