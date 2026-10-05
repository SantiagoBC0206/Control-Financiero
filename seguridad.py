"""
seguridad.py — Acceso con contraseña.

La contraseña NO está en el código. Se lee de los "secrets" de Streamlit:
  - En tu computador: archivo .streamlit/secrets.toml  (no se sube a GitHub)
  - En Streamlit Cloud: Settings -> Secrets
"""

import hmac

import streamlit as st


def _clave_correcta():
    """Lee la contraseña de los secrets. Devuelve None si no está configurada."""
    try:
        return st.secrets.get("password")
    except Exception:
        return None


def verificar_password():
    """Muestra la pantalla de acceso. Devuelve True solo si ya entró."""
    if st.session_state.get("autenticado"):
        return True

    st.title("🔒 Control Financiero")
    clave_correcta = _clave_correcta()

    if not clave_correcta:
        st.error(
            "No hay contraseña configurada. Crea el archivo "
            ".streamlit/secrets.toml con la línea: password = \"tu_clave\""
        )
        return False

    with st.form("form_login"):
        clave = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        # compare_digest evita que se pueda adivinar la clave por tiempos de respuesta
        if hmac.compare_digest(clave.encode(), str(clave_correcta).encode()):
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("😕 Contraseña incorrecta")
    return False
