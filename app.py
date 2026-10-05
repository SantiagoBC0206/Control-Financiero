"""app.py — Punto de entrada del Control Financiero (Streamlit).

Ejecutar con:  streamlit run app.py
"""

import streamlit as st

import db
from paginas import importar, inicio, registrar
from seguridad import verificar_password

st.set_page_config(
    page_title="Control Financiero", page_icon="🚗", layout="centered"
)

# --- ESTILOS CSS CLEAN LIGHT ---
st.markdown(
    """
    <style>
    /* Fondo limpio de la app */
    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Tarjetas redondeadas para métricas y contenedores */
    [data-testid="stMetric"], .stMetric {
        background-color: #F0F2F6 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* Estilo del valor numérico principal en las métricas */
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #1E88E5 !important;
    }
    
    /* Botones principales estilo App Móvil */
    .stButton > button {
        background-color: #1E88E5 !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
        box-shadow: 0 3px 8px rgba(30, 136, 229, 0.25) !important;
        width: 100%;
    }
    
    /* Pestañas (Tabs) estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F0F2F6;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E88E5 !important;
        color: #FFFFFF !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 1) Acceso con contraseña (si no entra, aquí se detiene todo)
if not verificar_password():
  st.stop()

# 2) Asegurar que las tablas existan
db.init_db()

# 3) Menú. Las pantallas nuevas (Reportes) se agregan aquí.
PAGINAS = {
    "🏠 Inicio": inicio.mostrar,
    "➕ Registrar día": registrar.mostrar,
    "📥 Importar Excel": importar.mostrar,
}

st.title("🚗 Control Financiero")
opcion = st.radio(
    "Menú", list(PAGINAS), horizontal=True, label_visibility="collapsed"
)
PAGINAS[opcion]()