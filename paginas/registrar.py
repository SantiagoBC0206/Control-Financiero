"""
paginas/registrar.py — Pantalla para registrar o editar un día (pensada para celular).
"""

import streamlit as st

import db
from utilidades import hoy, pesos

# Valores que aparecen ya escritos cuando el día es NUEVO (puedes cambiarlos).
VALORES_INICIALES_DIA_NUEVO = {"Gasolina": 60000}


def _campos(grupo, titulo, existentes, es_nuevo, fecha):
    """Dibuja un campo numérico por cada nombre del grupo y devuelve los valores."""
    st.markdown(titulo)
    valores = {}
    columnas = st.columns(2)
    for i, nombre in enumerate(db.nombres_disponibles(grupo)):
        inicial = existentes.get(nombre)
        if inicial is None and es_nuevo:
            inicial = VALORES_INICIALES_DIA_NUEVO.get(nombre)
        with columnas[i % 2]:
            valores[nombre] = st.number_input(
                nombre,
                min_value=0,
                step=1000,
                value=inicial,
                placeholder="0",
                format="%d",
                # la fecha en la clave hace que los campos se recarguen al cambiar de día
                key=f"{grupo}_{nombre}_{fecha}",
            )
    return valores


def _mostrar_balance(fecha):
    """Muestra el balance del día recién guardado."""
    fila = db.resumen_dias(desde=fecha, hasta=fecha).iloc[0]
    st.success(f"✅ Día {fecha.strftime('%d/%m/%Y')} guardado")
    st.metric("💰 Ganancia del día", pesos(fila["Ganancia Est"]))
    c1, c2 = st.columns(2)
    c1.metric("📥 Ingresos", pesos(fila["Total Ingresos"]))
    c2.metric("📤 Gastos", pesos(fila["Total Gastos"]))
    c3, c4 = st.columns(2)
    c3.metric("💵 Disponible", pesos(fila["Total Disp"]))
    c4.metric("⚖️ Diferencia", pesos(fila["Diferencia"]))


def mostrar():
    st.subheader("➕ Registrar día")
    fecha = st.date_input("Fecha", value=hoy(), format="DD/MM/YYYY")

    dia = db.cargar_dia(fecha)
    es_nuevo = dia is None
    existentes = dia or {"ingresos": {}, "gastos": {}, "movimientos": {}, "observaciones": ""}
    if not es_nuevo:
        st.info("Este día ya tiene datos. Si guardas, se reemplazan por los nuevos.")

    with st.form("form_dia"):
        ingresos = _campos("ingresos", "### 📥 Ingresos", existentes["ingresos"], es_nuevo, fecha)
        gastos = _campos("gastos", "### 📤 Gastos", existentes["gastos"], es_nuevo, fecha)
        movimientos = _campos("movimientos", "### 💳 Dinero recibido", existentes["movimientos"], es_nuevo, fecha)
        observaciones = st.text_input(
            "Observaciones (opcional)",
            value=existentes["observaciones"],
            key=f"obs_{fecha}",
        )
        guardar = st.form_submit_button("💾 GUARDAR DÍA", use_container_width=True, type="primary")

    if guardar:
        db.guardar_dia(fecha, ingresos, gastos, movimientos, observaciones)
        _mostrar_balance(fecha)
