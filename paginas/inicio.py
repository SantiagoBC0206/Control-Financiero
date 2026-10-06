"""paginas/inicio.py — Dashboard principal con gráficos interactivos y exportación profesional a Excel."""

from datetime import datetime
import io
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import db
from utilidades import pesos


def convertir_df_a_excel(df):
  """Genera un archivo Excel profesional con colores, bordes, totales y formato moneda."""
  output = io.BytesIO()
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "Control Financiero"

  ws.views.sheetView[0].showGridLines = True

  df_export = df.drop(
      columns=["Fecha_dt", "Año_Mes", "Dia_Semana", "Dia_Semana_ES"],
      errors="ignore",
  ).copy()

  headers = list(df_export.columns)
  ws.append(headers)

  fill_header = PatternFill(
      start_color="1E88E5", end_color="1E88E5", fill_type="solid"
  )
  font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
  align_center = Alignment(horizontal="center", vertical="center")
  thin_border = Border(
      left=Side(style="thin", color="CCCCCC"),
      right=Side(style="thin", color="CCCCCC"),
      top=Side(style="thin", color="CCCCCC"),
      bottom=Side(style="thin", color="CCCCCC"),
  )

  for col_num, _ in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_num)
    cell.fill = fill_header
    cell.font = font_header
    cell.alignment = align_center
    cell.border = thin_border

  font_data = Font(name="Calibri", size=10)
  cols_moneda = [c for c in headers if c not in ["Fecha", "Observaciones"]]

  for _, row in df_export.iterrows():
    row_data = [row[col] for col in headers]
    ws.append(row_data)

    current_row = ws.max_row
    for col_idx, col_name in enumerate(headers, 1):
      cell = ws.cell(row=current_row, column=col_idx)
      cell.font = font_data
      cell.border = thin_border

      if col_name == "Fecha":
        cell.alignment = Alignment(horizontal="center")
      elif col_name in cols_moneda:
        cell.number_format = '"$"#,##0'
        cell.alignment = Alignment(horizontal="right")

  totales_row = ["TOTALES"]
  for col in headers[1:]:
    if col in cols_moneda:
      totales_row.append(df_export[col].sum())
    else:
      totales_row.append("")

  ws.append(totales_row)
  tot_row_idx = ws.max_row

  fill_total = PatternFill(
      start_color="E3F2FD", end_color="E3F2FD", fill_type="solid"
  )
  font_total = Font(name="Calibri", size=11, bold=True, color="0D47A1")

  for col_idx, col_name in enumerate(headers, 1):
    cell = ws.cell(row=tot_row_idx, column=col_idx)
    cell.fill = fill_total
    cell.font = font_total
    cell.border = Border(
        top=Side(style="medium", color="1E88E5"),
        bottom=Side(style="double", color="1E88E5"),
    )
    if col_name in cols_moneda:
      cell.number_format = '"$"#,##0'
      cell.alignment = Alignment(horizontal="right")

  for col in ws.columns:
    max_len = 0
    col_letter = get_column_letter(col[0].column)
    for cell in col:
      val_str = str(cell.value or "")
      if cell.number_format == '"$"#,##0' and isinstance(
          cell.value, (int, float)
      ):
        val_str = f"${cell.value:,.0f}"
      max_len = max(max_len, len(val_str))
    ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

  wb.save(output)
  return output.getvalue()


def mostrar():
  st.subheader("📊 Dashboard Financiero y Reportes")

  df = db.resumen_dias()

  if df.empty:
    st.info(
        "👋 ¡Bienvenido! Aún no hay registros en el sistema. Ve a la sección **➕"
        " Registrar día** para comenzar."
    )
    return

  df["Fecha_dt"] = pd.to_datetime(df["Fecha"])
  df["Año_Mes"] = df["Fecha_dt"].dt.strftime("%Y-%m")
  df["Dia_Semana"] = df["Fecha_dt"].dt.day_name()

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

  st.markdown("### 🔍 Filtro de Período")
  tipo_filtro = st.radio(
      "Tipo de Consulta",
      ["Por Mes", "Rango Personalizado"],
      horizontal=True,
      label_visibility="collapsed",
  )

  if tipo_filtro == "Por Mes":
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
    df_filtrado = df[df["Año_Mes"] == mes_sel].copy()
    titulo_periodo = f"Mes {mes_sel}"
  else:
    col_f1, col_f2 = st.columns(2)
    min_fecha = df["Fecha_dt"].min().date()
    max_fecha = df["Fecha_dt"].max().date()
    f_inicio = col_f1.date_input("Fecha Inicio", value=min_fecha)
    f_fin = col_f2.date_input("Fecha Fin", value=max_fecha)

    df_filtrado = df[
        (df["Fecha_dt"].dt.date >= f_inicio)
        & (df["Fecha_dt"].dt.date <= f_fin)
    ].copy()
    titulo_periodo = (
        f"Período {f_inicio.strftime('%d/%m/%Y')} a {f_fin.strftime('%d/%m/%Y')}"
    )

  if df_filtrado.empty:
    st.warning("No se encontraron registros para el período seleccionado.")
    return

  excel_data = convertir_df_a_excel(df_filtrado)
  st.download_button(
      label=f"📥 Descargar Reporte Excel ({titulo_periodo})",
      data=excel_data,
      file_name=f"Reporte_Control_Financiero_{titulo_periodo.replace(' ', '_')}.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      use_container_width=True,
  )

  tot_ingresos = df_filtrado["Total Ingresos"].sum()
  tot_gastos = df_filtrado["Total Gastos"].sum()
  tot_ganancia = df_filtrado["Ganancia Est"].sum()
  tot_disponible = df_filtrado["Total Disp"].sum()

  st.markdown("---")
  c1, c2 = st.columns(2)
  c1.metric("💵 Total Disponible en Caja", pesos(tot_disponible))
  c2.metric("📈 Ganancia Estimada", pesos(tot_ganancia))

  c3, c4 = st.columns(2)
  c3.metric("📥 Total Ingresos", pesos(tot_ingresos))
  c4.metric("📤 Total Gastos", pesos(tot_gastos))

  st.markdown("---")
  st.markdown(f"### 🏆 Análisis de Rentabilidad ({titulo_periodo})")

  df_dias_rentables = (
      df_filtrado.groupby("Dia_Semana_ES")["Total Disp"].mean().reset_index()
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

  if not df_dias_rentables.empty and df_dias_rentables["Total Disp"].max() > 0:
    dia_top = df_dias_rentables.loc[
        df_dias_rentables["Total Disp"].idxmax()
    ]
    st.success(
        f"⭐ **Día más rentable en disponibilidad de caja:**"
        f" **{dia_top['Dia_Semana_ES']}** con un promedio de"
        f" **{pesos(dia_top['Total Disp'])}** disponibles por día."
    )

  st.markdown("---")
  st.markdown(f"### 🍩 Distribución de Ingresos ({titulo_periodo})")

  col_plat = [
      c
      for c in ["Didi", "InDrive", "Uber", "Extras"]
      if c in df_filtrado.columns and df_filtrado[c].sum() > 0
  ]

  if col_plat:
    plat_totales = df_filtrado[col_plat].sum().reset_index()
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
    st.info("Sin datos de plataformas para graficar en este período.")

  st.markdown("---")
  st.markdown(f"### 📉 Ingresos vs Gastos por Día ({titulo_periodo})")

  fig_barras = go.Figure()
  fig_barras.add_trace(
      go.Bar(
          x=df_filtrado["Fecha"],
          y=df_filtrado["Total Ingresos"],
          name="Ingresos",
          marker_color="#1E88E5",
      )
  )
  fig_barras.add_trace(
      go.Bar(
          x=df_filtrado["Fecha"],
          y=df_filtrado["Total Gastos"],
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