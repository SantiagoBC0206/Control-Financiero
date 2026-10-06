"""paginas/inicio.py — Dashboard principal con gráficos interactivos tipo Power BI."""

from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import db
from utilidades import pesos


def mostrar():
  st.subheader("📊 Dashboard Financiero")

  # Cargar datos del resumen
  df = db.resumen_dias()

  if df.empty:
    st.info(
        "👋 ¡Bienvenido! Aún no hay registros en el sistema. Ve a la sección **➕"
        " Registrar día** para comenzar."
    )
    return

  # Convertir la columna Fecha a datetime para agrupaciones
  df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
  df["Año_Mes"] = df["Fecha_dt"].dt.strftime("%Y-%m")
  df["Dia_Semana"] = df["Fecha_dt"].dt.day_name()

  # Mapeo de días al español
  dias_espanol = {
      "Monday": "Lunes",
      "Tuesday": "Martes",
      "Wednesday": "Miércoles",
      "Thursday": "Jueves",
      "Friday": "Viernes",
      "Saturday": "Sábado",
      "Sunday": "Domingo",
  }
  df["Dia_Semana_ES"] = df["Dia_Semana"].map(dias_espanol)

  # --- FILTRO POR MES ---
  meses_disponibles = sorted(df["Año_Mes"].unique(), reverse=True)
  mes_actual_str = datetime.now().strftime("%Y-%m")
  default_index = (
      meses_disponibles.index(mes_actual_str)
      if mes_actual_str in meses_disponibles
      else 0
  )

  mes_sel = st.selectbox(
      "📅 Selecciona el Mes a Analizar",
      meses_disponibles,
      index=default_index,
  )
  df_mes = df[df["Año_Mes"] == mes_sel].copy()

  if df_mes.empty:
    st.warning("No hay datos para el mes seleccionado.")
    return

  # --- MÉTRICAS CLAVE (KPIs) ---
  tot_ingresos = df_mes["Total Ingresos"].sum()
  tot_gastos = df_mes["Total Gastos"].sum()
  tot_ganancia = df_mes["Ganancia Est"].sum()
  tot_disponible = df_mes["Total Disp"].sum()

  st.markdown("---")
  c1, c2 = st.columns(2)
  c1.metric("💵 Total Disponible en Caja", pesos(tot_disponible))
  c2.metric("📈 Ganancia Estimada", pesos(tot_ganancia))

  c3, c4 = st.columns(2)
  c3.metric("📥 Total Ingresos", pesos(tot_ingresos))
  c4.metric("📤 Total Gastos", pesos(tot_gastos))

  # --- INDICADOR: DÍA MÁS RENTABLE DE LA SEMANA ---
  st.markdown("---")
  st.markdown("### 🏆 Análisis de Rentabilidad por Día")

  df_dias_rentables = (
      df.groupby("Dia_Semana_ES")["Ganancia Est"]
      .mean()
      .reset_index()
  )
  orden_dias = [
      "Lunes",
      "Martes",
      "Miércoles",
      "Jueves",
      "Viernes",
      "Sábado",
      "Domingo",
  ]
  df_dias_rentables["Dia_Semana_ES"] = pd.Categorical(
      df_dias_rentables["Dia_Semana_ES"], categories=orden_dias, ordered=True
  )
  df_dias_rentables = df_dias_rentables.sort_values("Dia_Semana_ES")

  if not df_dias_rentables.empty and df_dias_rentables["Ganancia Est"].max() > 0:
    dia_top = df_dias_rentables.loc[
        df_dias_rentables["Ganancia Est"].idxmax()
    ]
    st.success(
        f"⭐ **Día más rentable históricamente:** **{dia_top['Dia_Semana_ES']}**"
        f" con un promedio de **{pesos(dia_top['Ganancia Est'])}** por día."
    )

  # --- GRÁFICO 1: DONUT DE DISTRIBUCIÓN DE INGRESOS ---
  st.markdown("---")
  st.markdown(f"### 🍩 Distribución de Ingresos (`{mes_sel}`)")

  col_plat = [
      c
      for c in ["Didi", "InDrive", "Uber", "Extras"]
      if c in df_mes.columns and df_mes[c].sum() > 0
  ]

  if col_plat:
    plat_totales = (
        df_mes[col_plat].sum().reset_index()
    )
    plat_totales.columns = ["Plataforma", "Monto"]

    fig_donut = px.pie(
        plat_totales,
        values="Monto",
        names="Plataforma",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_donut.update_traces(textposition="inside", textinfo="percent+label")
    fig_donut.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
    )
    st.plotly_chart(fig_donut, use_container_width=True)
  else:
    st.info("Sin datos de plataformas para graficar en este mes.")

  # --- GRÁFICO 2: EVOLUCIÓN DIARIA INGRESOS VS GASTOS ---
  st.markdown("---")
  st.markdown(f"### 📉 Ingresos vs Gastos por Día (`{mes_sel}`)")

  fig_barras = go.Figure()
  fig_barras.add_trace(
      go.Bar(
          x=df_mes["Fecha"],
          y=df_mes["Total Ingresos"],
          name="Ingresos",
          marker_color="#1E88E5",
      )
  )
  fig_barras.add_trace(
      go.Bar(
          x=df_mes["Fecha"],
          y=df_mes["Total Gastos"],
          name="Gastos",
          marker_color="#E53935",
      )
  )

  fig_barras.update_layout(
      barmode="group",
      margin=dict(t=20, b=20, l=10, r=10),
      legend=dict(orientation="h", yanchor="bottom", y=1.02),
      xaxis_title="Día",
      yaxis_title="Pesos ($)",
  )
  st.plotly_chart(fig_barras, use_container_width=True)