
"""app.py — Punto de entrada del Control Financiero.

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
# ESTILOS GENERALES
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
        transition: background-color 0.2s ease;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #1565C0 !important;
        border: none !important;
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
       CAMPOS DE TEXTO GENERALES
    ========================================= */

    [data-testid="stTextInput"] input:not([type="password"]) {
        font-size: 24px !important;
        min-height: 65px !important;
    }

    /* =========================================
       LOGIN: ESPACIADO Y TARJETA
    ========================================= */

    .login-espacio-superior {
        height: clamp(45px, 13vh, 115px);
    }

    .login-header {
        background: linear-gradient(
            145deg,
            #F0F5FC 0%,
            #E7F0FC 100%
        );

        border: 1px solid #DCE6F2;
        border-radius: 20px;

        padding: 30px 24px 24px;

        text-align: center;

        box-shadow: 0 5px 18px rgba(15, 45, 80, 0.08);

        margin-bottom: 12px;
    }

    .login-icono {
        font-size: 42px;
        margin-bottom: 8px;
    }

    .login-header h1 {
        color: #176FC1;
        font-size: 30px;
        font-weight: 750;
        margin: 0 0 12px 0;
        line-height: 1.2;
    }

    .login-header p {
        color: #586779;
        font-size: 14px;
        line-height: 1.5;
        margin: 0;
    }

    .login-separador {
        height: 1px;
        background-color: #D5E0EC;
        margin: 20px auto 14px;
        max-width: 150px;
    }

    .login-seguridad {
        display: inline-block;
        color: #2876B9;
        background-color: #E0EDFA;
        border-radius: 20px;
        padding: 6px 12px;
        font-size: 10px;
        font-weight: 750;
        letter-spacing: 1px;
    }

    /* =========================================
       LOGIN: FORMULARIO
    ========================================= */

    [data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #DCE2E9 !important;
        border-radius: 16px !important;
        padding: 18px !important;
        margin-top: 0 !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
    }

    .login-label {
        color: #344256;
        font-size: 14px;
        font-weight: 650;
        margin-bottom: 7px;
    }

    [data-testid="stTextInput"]:has(input[type="password"]) {
        margin-bottom: 12px !important;
    }

    [data-testid="stTextInput"]:has(input[type="password"])
    [data-baseweb="input"] {
        height: 56px !important;
        min-height: 56px !important;
        background-color: #F5F7FA !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }

    [data-testid="stTextInput"] input[type="password"] {
        font-size: 20px !important;
        font-weight: 500 !important;
        min-height: 54px !important;
        height: 54px !important;
        color: #243447 !important;
        padding-left: 12px !important;
    }

    [data-testid="stTextInput"] input[type="password"]::placeholder {
        color: #8995A5 !important;
        font-size: 15px !important;
        font-weight: 400 !important;
    }

    /* Botón específico del formulario de acceso */

    [data-testid="stForm"] .stFormSubmitButton > button {
        min-height: 54px !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        border-radius: 10px !important;
        margin-top: 4px !important;
    }

    /* =========================================
       ADAPTACIÓN PARA CELULARES
    ========================================= */

    @media screen and (max-width: 768px) {

        .login-espacio-superior {
            height: 35px;
        }

        .login-header {
            padding: 24px 16px 20px;
            border-radius: 16px;
        }

        .login-icono {
            font-size: 36px;
        }

        .login-header h1 {
            font-size: 25px;
        }

        .login-header p {
            font-size: 13px;
        }

        [data-testid="stForm"] {
            padding: 15px !important;
        }

        [data-testid="stTextInput"]:has(input[type="password"])
        [data-baseweb="input"] {
            min-height: 54px !important;
            height: 54px !important;
        }

        [data-testid="stTextInput"] input[type="password"] {
            font-size: 18px !important;
            min-height: 52px !important;
            height: 52px !important;
        }

        [data-testid="stTextInput"] input[type="password"]::placeholder {
            font-size: 14px !important;
        }

        [data-testid="stForm"] .stFormSubmitButton > button {
            min-height: 58px !important;
            font-size: 15px !important;
        }

        /* Se conservan los campos numéricos */

        [data-testid="stNumberInput"] [data-baseweb="input"] {
            min-height: 110px !important;
            height: 110px !important;
        }

        [data-testid="stNumberInput"] input {
            font-size: 44px !important;
            font-weight: 800 !important;
        }

        [data-testid="stNumberInput"] button {
            min-width: 65px !important;
            min-height: 105px !important;
        }

        [data-testid="stNumberInput"] button svg {
            width: 32px !important;
            height: 32px !important;
        }

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
