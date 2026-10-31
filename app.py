
"""app.py — Punto de entrada del Control Financiero (Streamlit).

Ejecutar con: streamlit run app.py
"""

import streamlit as st

import db
from paginas import importar, inicio, registrar
from seguridad import verificar_password


# ==========================================================
# CONFIGURACIÓN GENERAL
# ==========================================================

st.set_page_config(
    page_title="Control Financiero",
    page_icon="🚗",
    layout="centered",
)


# ==========================================================
# ESTILOS GENERALES Y ADAPTACIÓN PARA CELULARES
# ==========================================================

st.markdown(
    """
    <style>

    /* =========================================
       DISEÑO GENERAL
    ========================================= */

    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* =========================================
       MÉTRICAS FINANCIERAS
    ========================================= */

    [data-testid="stMetric"] {
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

    /* =========================================
       BOTONES PRINCIPALES
    ========================================= */

    .stButton > button,
    .stFormSubmitButton > button {
        background-color: #1E88E5 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 16px 20px !important;
        min-height: 65px !important;
        width: 100% !important;
    }

    /* =========================================
       PESTAÑAS
    ========================================= */

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

    /* =========================================
       CAMPOS NUMÉRICOS
    ========================================= */

    [data-testid="stNumberInput"] {
        width: 100% !important;
        margin-bottom: 22px !important;
    }

    [data-testid="stNumberInput"] [data-baseweb="input"] {
        min-height: 105px !important;
        height: 105px !important;
        background-color: #F1F5F9 !important;
        border: 2px solid #CBD5E1 !important;
        border-radius: 14px !important;
    }

    [data-testid="stNumberInput"] input {
        font-size: 44px !important;
        font-weight: 800 !important;
        color: #000000 !important;
        height: 100% !important;
    }

    /* Botones de incremento y disminución */

    [data-testid="stNumberInput"] button {
        min-width: 60px !important;
        min-height: 100px !important;
    }

    [data-testid="stNumberInput"] button svg {
        width: 30px !important;
        height: 30px !important;
    }

    /* =========================================
       CAMPO DE CONTRASEÑA
    ========================================= */

    [data-testid="stTextInput"] input[type="password"] {
        font-size: 40px !important;
        font-weight: 800 !important;
        min-height: 85px !important;
    }

    [data-testid="stTextInput"]:has(input[type="password"])
    [data-baseweb="input"] {
        min-height: 90px !important;
        height: 90px !important;
        border-radius: 14px !important;
    }

    /* =========================================
       OTROS CAMPOS DE TEXTO
    ========================================= */

    [data-testid="stTextInput"] input:not([type="password"]) {
        font-size: 24px !important;
        min-height: 65px !important;
    }

    /* =========================================
       ADAPTACIÓN PARA CELULARES
    ========================================= */

    @media screen and (max-width: 768px) {

        /* Campos numéricos */

        [data-testid="stNumberInput"] [data-baseweb="input"] {
            min-height: 110px !important;
            height: 110px !important;
        }

        [data-testid="stNumberInput"] input {
            font-size: 44px !important;
            font-weight: 800 !important;
        }

        /* Botones + y - */

        [data-testid="stNumberInput"] button {
            min-width: 65px !important;
            min-height: 105px !important;
        }

        [data-testid="stNumberInput"] button svg {
            width: 32px !important;
            height: 32px !important;
        }

        /* Contraseña */

        [data-testid="stTextInput"] input[type="password"] {
            font-size: 40px !important;
        }

        [data-testid="stTextInput"]:has(input[type="password"])
        [data-baseweb="input"] {
            min-height: 95px !important;
            height: 95px !important;
        }

        /* Botones de guardar e ingresar */

        .stFormSubmitButton > button,
        .stButton > button {
            min-height: 75px !important;
            font-size: 22px !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================================
# ACCESO AL SISTEMA
# ==========================================================

if not verificar_password():
    st.stop()


# ==========================================================
# INICIALIZAR BASE DE DATOS
# ==========================================================

db.init_db()


# ==========================================================
# MENÚ PRINCIPAL
# ==========================================================

PAGINAS = {
    "🏠 Inicio": inicio.mostrar,
    "➕ Registrar día": registrar.mostrar,
    "📥 Importar Excel": importar.mostrar,
}


# ==========================================================
# MOSTRAR APLICACIÓN
# ==========================================================

st.title("🚗 Control Financiero")

opcion = st.radio(
    "Menú",
    list(PAGINAS),
    horizontal=True,
    label_visibility="collapsed",
)

PAGINAS[opcion]()
