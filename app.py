
"""app.py — Punto de entrada del Control Financiero (Streamlit).

Ejecutar con: streamlit run app.py
"""

import streamlit as st

import db
from paginas import importar, inicio, registrar
from seguridad import verificar_password

st.set_page_config(
    page_title="Control Financiero",
    page_icon="🚗",
    layout="centered",
)

# ==========================================================
# ESTILOS GENERALES Y CAMPOS DE ENTRADA
# ==========================================================

st.markdown(
    """
    <style>

    /* --------------------------------------------------
       DISEÑO GENERAL
    -------------------------------------------------- */

    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Tarjetas de métricas */
    [data-testid="stMetric"], .stMetric {
        background-color: #F0F2F6 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
        border: 1px solid #E0E0E0 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #1E88E5 !important;
    }

    /* Botones principales */
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

    /* Pestañas */
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

    /* --------------------------------------------------
       CAMPOS NUMÉRICOS: INGRESOS, GASTOS Y DINERO
    -------------------------------------------------- */

    /* Aumentar altura de las casillas */
    div[data-testid="stNumberInput"] div[data-baseweb="input"] {
        height: 110px !important;
        min-height: 110px !important;
        border-radius: 14px !important;
    }

    /* Aumentar números escritos */
    div[data-testid="stNumberInput"] input {
        font-size: 44px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        color: #000000 !important;
        height: 100% !important;
    }

    /* Botones de sumar y restar */
    div[data-testid="stNumberInput"] button {
        min-width: 60px !important;
        min-height: 100px !important;
    }

    div[data-testid="stNumberInput"] button svg {
        width: 30px !important;
        height: 30px !important;
    }

    /* --------------------------------------------------
       CONTRASEÑA DEL LOGIN
       Aplicar solamente al campo password
    -------------------------------------------------- */

    div[data-testid="stTextInput"]:has(input[type="password"])
    div[data-baseweb="input"] {
        height: 90px !important;
        min-height: 90px !important;
        border-radius: 12px !important;
    }

    div[data-testid="stTextInput"]:has(input[type="password"]) input {
        font-size: 40px !important;
        font-weight: 700 !important;
        color: #000000 !important;
        height: 100% !important;
    }

    /* --------------------------------------------------
       AJUSTES PARA CELULARES
    -------------------------------------------------- */

    @media screen and (max-width: 768px) {

        div[data-testid="stNumberInput"] div[data-baseweb="input"] {
            height: 110px !important;
            min-height: 110px !important;
        }

        div[data-testid="stNumberInput"] input {
            font-size: 44px !important;
        }

        div[data-testid="stNumberInput"] button {
            min-width: 60px !important;
            min-height: 100px !important;
        }

        div[data-testid="stTextInput"]:has(input[type="password"])
        div[data-baseweb="input"] {
            height: 90px !important;
            min-height: 90px !important;
        }

        div[data-testid="stTextInput"]:has(input[type="password"]) input {
            font-size: 40px !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# 1. ACCESO CON CONTRASEÑA
# ==========================================================

if not verificar_password():
    st.stop()


# ==========================================================
# 2. ASEGURAR QUE LAS TABLAS EXISTAN
# ==========================================================

db.init_db()


# ==========================================================
# 3. MENÚ PRINCIPAL
# ==========================================================

PAGINAS = {
    "🏠 Inicio": inicio.mostrar,
    "➕ Registrar día": registrar.mostrar,
    "📥 Importar Excel": importar.mostrar,
}

st.title("🚗 Control Financiero")

opcion = st.radio(
    "Menú",
    list(PAGINAS),
    horizontal=True,
    label_visibility="collapsed",
)

PAGINAS[opcion]()
