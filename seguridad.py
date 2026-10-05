import streamlit as st


def verificar_password():
  # Intentar obtener la contraseña desde st.secrets de Streamlit Cloud
  try:
    password_correcta = st.secrets["passwords"]["admin_password"]
  except Exception:
    # Si no existe en secrets o en local, usa la clave por defecto
    password_correcta = "kiracamelo7"

  def password_entered():
    if st.session_state["password_input"] == password_correcta:
      st.session_state["password_correct"] = True
      del st.session_state["password_input"]
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.title("🔒 Control Financiero")
    st.markdown("##### Acceso Privado")
    st.text_input(
        "Ingresa la contraseña secreta",
        type="password",
        on_change=password_entered,
        key="password_input",
    )
    return False
  elif not st.session_state["password_correct"]:
    st.title("🔒 Control Financiero")
    st.markdown("##### Acceso Privado")
    st.text_input(
        "Ingresa la contraseña secreta",
        type="password",
        on_change=password_entered,
        key="password_input",
    )
    st.error("😕 Contraseña incorrecta")
    return False
  else:
    return True