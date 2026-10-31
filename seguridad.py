
"""seguridad.py — Control de acceso con contraseña."""

import streamlit as st


# Conserva aquí la contraseña real que utiliza tu aplicación.
PASSWORD_CORRECTA = "kiracamelo7"


def verificar_password():
    """Retorna True si el usuario ingresó la contraseña correcta."""

    if st.session_state.get("autenticado", False):
        return True

    # Espaciado superior.
    st.markdown(
        '<div class="login-espacio-superior"></div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.7, 1])

    with col2:

        # Tarjeta de presentación: renderizado HTML directo.
        st.html("""
            <div class="login-header">
                <div class="login-icono">🚗</div>

                <h1>Control Financiero</h1>

                <p>
                    Gestiona tus registros y consulta
                    tu información financiera.
                </p>

                <div class="login-separador"></div>

                <span class="login-seguridad">
                    🔒 ACCESO PRIVADO
                </span>
            </div>
        """)

        # Formulario de acceso.
        with st.form("form_login"):

            st.html("""
                <div class="login-label">
                    Ingresa tu contraseña aquí
                </div>
            """)

            clave = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Escribe tu contraseña...",
                label_visibility="collapsed",
                key="login_password",
            )

            ingresar = st.form_submit_button(
                "🔑 INGRESAR AL SISTEMA",
                use_container_width=True,
                type="primary",
            )

        # Validación.
        if ingresar:

            if clave == PASSWORD_CORRECTA:

                st.session_state["autenticado"] = True
                st.rerun()

            else:

                st.error(
                    "Contraseña incorrecta. "
                    "Verifica e inténtalo nuevamente."
                )

    return False
