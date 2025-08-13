
import streamlit as st
from modulos.gestion_trm import mostrar_interfaz_trm

st.set_page_config(page_title="Gestión TRM", page_icon="💱", layout="wide")

# Mostrar la interfaz de gestión de TRM
mostrar_interfaz_trm()
