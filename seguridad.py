"""seguridad.py — Control de acceso con contraseña y diseño estilizado."""

import streamlit as st

# Contraseña de acceso a la aplicación
PASSWORD_CORRECTA = "kiracamelo7"


def verificar_password():
  """Retorna True si el usuario ingresó la contraseña correcta."""
  if st.session_state.get("autenticado", False):
    return True

  # Contenedor centrado para la tarjeta de Login
  st.markdown("<br><br>", unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 2, 1])

  with col2:
    st.markdown(
        """
            <div style="
                background-color: #F0F2F6;
                padding: 24px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                border: 1px solid #E0E0E0;
                text-align: center;
                margin-bottom: 20px;
            ">
                <h2 style="color: #1E88E5; margin-bottom: 4px;">🚗 Control Financiero</h2>
                <p style="color: #555555; font-size: 14px; margin-top: 0;">Ingresa tu clave de acceso para continuar</p>
            </div>
            """,
        unsafe_allow_html=True,
    )

    with st.form("form_login"):
      clave = st.text_input(
          "🔒 Contraseña",
          type="password",
          placeholder="Escribe tu contraseña...",
          label_visibility="collapsed",
      )
      ingresar = st.form_submit_button(
          "🔑 INGRESAR AL SISTEMA", use_container_width=True, type="primary"
      )

    if ingresar:
      if clave == PASSWORD_CORRECTA:
        st.session_state["autenticado"] = True
        st.success("✅ Acceso concedido")
        st.rerun()
      else:
        st.error("❌ Contraseña incorrecta. Inténtalo de nuevo.")

  return False