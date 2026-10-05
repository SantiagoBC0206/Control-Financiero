"""
app.py — Punto de entrada del Control Financiero (Streamlit).

Ejecutar con:  streamlit run app.py
"""

import streamlit as st

import db
from paginas import registrar
from seguridad import verificar_password

st.set_page_config(page_title="Control Financiero", page_icon="🚗", layout="centered")

# 1) Acceso con contraseña (si no entra, aquí se detiene todo)
if not verificar_password():
    st.stop()

# 2) Asegurar que las tablas existan
db.init_db()

# 3) Menú. Las pantallas nuevas (Inicio, Reportes, Importar) se agregan aquí.
PAGINAS = {
    "➕ Registrar día": registrar.mostrar,
}

st.title("🚗 Control Financiero")
opcion = st.radio("Menú", list(PAGINAS), horizontal=True, label_visibility="collapsed")
PAGINAS[opcion]()
