"""paginas/registrar.py — Pantalla para consultar, registrar, editar y eliminar un día."""

import streamlit as st
import db
from utilidades import hoy, pesos

# Valores iniciales para días nuevos
VALORES_INICIALES_DIA_NUEVO = {"Gasolina": 60000}


def _campos(grupo, titulo, existentes, es_nuevo, fecha):
  """Dibuja campos numéricos para ingresar valores."""
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
          key=f"{grupo}_{nombre}_{fecha}",
      )
  return valores


def _mostrar_balance(fecha):
  """Muestra el resumen y cuadre de caja del día consultado/guardado."""
  df_res = db.resumen_dias(desde=fecha, hasta=fecha)
  if df_res.empty:
    st.warning("No hay registros detallados para este día.")
    return

  fila = df_res.iloc[0]

  st.markdown("---")
  st.markdown("### 💰 CUADRE DE CAJA Y DINERO DISPONIBLE")

  # 1. Énfasis principal en Total Disponible
  st.metric("💵 TOTAL DISPONIBLE EN CAJA", pesos(fila.get("Total Disp", 0)))

  # 2. Desglose detallado Efectivo vs Nequi
  dia = db.cargar_dia(fecha)
  movs = dia.get("movimientos", {}) if dia else {}
  val_efectivo = movs.get("Efectivo", 0) or 0
  val_nequi = (
      movs.get("Nequi", 0)
      or movs.get("Nequi / Bancos", 0)
      or movs.get("Bancos", 0)
      or 0
  )

  col_e, col_n = st.columns(2)
  col_e.metric("💵 Recibido Efectivo", pesos(val_efectivo))
  col_n.metric("📱 Recibido Nequi / Bancos", pesos(val_nequi))

  st.markdown("---")
  st.markdown("##### 📊 Resumen Financiero Adicional")

  # 3. Métricas secundarias
  c1, c2 = st.columns(2)
  c1.metric("📥 Total Ingresos", pesos(fila.get("Total Ingresos", 0)))
  c2.metric("📤 Total Gastos", pesos(fila.get("Total Gastos", 0)))

  c3, c4 = st.columns(2)
  c3.metric("📈 Ganancia Estimada", pesos(fila.get("Ganancia Est", 0)))
  c4.metric("⚖️ Diferencia de Caja", pesos(fila.get("Diferencia", 0)))

  obs = dia.get("observaciones", "") if dia else ""
  if obs:
    st.info(f"📝 **Observaciones:** {obs}")


def mostrar():
  st.subheader("📱 Gestión Diaria de Trabajo")
  fecha = st.date_input("Selecciona la Fecha", value=hoy(), format="DD/MM/YYYY")

  dia = db.cargar_dia(fecha)
  es_nuevo = dia is None
  existentes = dia or {
      "ingresos": {},
      "gastos": {},
      "movimientos": {},
      "observaciones": "",
  }

  if not es_nuevo:
    st.success(f"📅 Registros encontrados para el día **{fecha.strftime('%d/%m/%Y')}**")

    # Pestañas para elegir la acción deseada
    tab_ver, tab_editar, tab_eliminar = st.tabs(
        ["👁️ Visualizar", "✏️ Editar Día", "🗑️ Eliminar Día"]
    )

    with tab_ver:
      _mostrar_balance(fecha)

    with tab_editar:
      with st.form("form_editar_dia"):
        ingresos = _campos(
            "ingresos",
            "### 📥 Ingresos",
            existentes["ingresos"],
            False,
            fecha,
        )
        gastos = _campos(
            "gastos", "### 📤 Gastos", existentes["gastos"], False, fecha
        )
        movimientos = _campos(
            "movimientos",
            "### 💳 Dinero recibido",
            existentes["movimientos"],
            False,
            fecha,
        )
        observaciones = st.text_input(
            "Observaciones (opcional)",
            value=existentes["observaciones"],
            key=f"obs_edit_{fecha}",
        )

        guardar_edit = st.form_submit_button(
            "🔄 ACTUALIZAR DÍA", use_container_width=True, type="primary"
        )

      if guardar_edit:
        db.guardar_dia(fecha, ingresos, gastos, movimientos, observaciones)
        st.success(f"✅ ¡Día {fecha.strftime('%d/%m/%Y')} actualizado!")
        st.rerun()

    with tab_eliminar:
      st.error(
          "⚠️ **Atención:** Esta acción eliminará permanentemente todos los"
          " registros de este día."
      )
      confirmar_borrado = st.checkbox(
          "Confirmo que deseo borrar este día de la base de datos."
      )

      if st.button(
          "🗑️ ELIMINAR DÍA DEFINITIVAMENTE",
          type="primary",
          disabled=not confirmar_borrado,
          use_container_width=True,
      ):
        db.eliminar_dia(fecha)
        st.success(f"🗑️ Registro del {fecha.strftime('%d/%m/%Y')} eliminado.")
        st.rerun()

  else:
    st.info(f"📝 Registrando nuevo día de trabajo: **{fecha.strftime('%d/%m/%Y')}**")
    with st.form("form_nuevo_dia"):
      ingresos = _campos(
          "ingresos", "### 📥 Ingresos", existentes["ingresos"], True, fecha
      )
      gastos = _campos(
          "gastos", "### 📤 Gastos", existentes["gastos"], True, fecha
      )
      movimientos = _campos(
          "movimientos",
          "### 💳 Dinero recibido",
          existentes["movimientos"],
          True,
          fecha,
      )
      observaciones = st.text_input(
          "Observaciones (opcional)",
          value=existentes["observaciones"],
          key=f"obs_new_{fecha}",
      )

      guardar_nuevo = st.form_submit_button(
          "💾 GUARDAR DÍA", use_container_width=True, type="primary"
      )

    if guardar_nuevo:
      db.guardar_dia(fecha, ingresos, gastos, movimientos, observaciones)
      st.success(f"✅ ¡Día {fecha.strftime('%d/%m/%Y')} guardado exitosamente!")
      st.rerun()