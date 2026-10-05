"""
paginas/inicio.py — Pantalla de inicio: balance de hoy, del mes y del año.
"""

import altair as alt
import pandas as pd
import streamlit as st

import db
import estadisticas as est
from utilidades import MESES_CORTOS, hoy, nombre_mes, pesos


# ---------------------------------------------------------------------------
# Gráficas sencillas (Altair) que respetan el orden de los datos
# ---------------------------------------------------------------------------
def _barras(serie, ordenar=None):
    """Gráfica de barras de una Serie (índice = nombre, valor = pesos)."""
    datos = serie.reset_index()
    datos.columns = ["Nombre", "Valor"]
    grafica = (
        alt.Chart(datos, height=220)
        .mark_bar()
        .encode(
            x=alt.X("Nombre:N", sort=ordenar, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Valor:Q", title=None),
            tooltip=["Nombre", "Valor"],
        )
    )
    st.altair_chart(grafica)


def _linea(serie):
    """Gráfica de línea con puntos de una Serie (para acumulados)."""
    datos = serie.reset_index()
    datos.columns = ["Nombre", "Valor"]
    grafica = (
        alt.Chart(datos, height=220)
        .mark_line(point=True)
        .encode(
            x=alt.X("Nombre:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Valor:Q", title=None),
            tooltip=["Nombre", "Valor"],
        )
    )
    st.altair_chart(grafica)


def _delta(valor):
    """Texto de variación con signo: +$5.000 / -$5.000 (None si es 0)."""
    if valor == 0:
        return None
    return ("+" if valor > 0 else "") + pesos(valor)


# ---------------------------------------------------------------------------
# Pestaña HOY
# ---------------------------------------------------------------------------
def _tab_hoy(df):
    fecha = hoy()
    st.markdown(f"#### {fecha.strftime('%d/%m/%Y')}")

    fila_hoy = df[df["Fecha"] == pd.Timestamp(fecha)]
    anterior = est.dia_anterior_trabajado(df, fecha)

    if fila_hoy.empty:
        st.info("Hoy todavía no hay registro. Ve a ➕ Registrar día.")
        if anterior is not None:
            st.caption(
                f"Último día trabajado: {anterior['Fecha']:%d/%m/%Y} — "
                f"disponible {pesos(anterior['Total Disp'])}"
            )
        return

    f = fila_hoy.iloc[0]
    delta = None
    if anterior is not None:
        delta = _delta(int(f["Total Disp"] - anterior["Total Disp"]))
    # Cifra principal: el dinero disponible
    st.metric("💵 Disponible de hoy", pesos(f["Total Disp"]), delta=delta)
    if anterior is not None:
        st.caption(
            f"Comparado con el último día trabajado ({anterior['Fecha']:%d/%m/%Y}): "
            f"{pesos(anterior['Total Disp'])}"
        )

    c1, c2 = st.columns(2)
    c1.metric("📥 Ingresos", pesos(f["Total Ingresos"]))
    c2.metric("📤 Gastos", pesos(f["Total Gastos"]))
    c3, c4 = st.columns(2)
    c3.metric("📈 Ganancia estimada", pesos(f["Ganancia Est"]))
    c4.metric("⚖️ Diferencia", pesos(f["Diferencia"]))

    ing, _, _ = est.grupos_columnas(df)
    por_plataforma = f[ing].astype(int)
    if por_plataforma.sum() > 0:
        mejor = por_plataforma.idxmax()
        st.caption(f"Plataforma que más produjo hoy: **{mejor}** ({pesos(por_plataforma[mejor])})")
        _barras(por_plataforma)


# ---------------------------------------------------------------------------
# Pestaña MES
# ---------------------------------------------------------------------------
def _tab_mes(df):
    meses = sorted(df["AñoMes"].unique(), reverse=True)
    mes = st.selectbox("Mes", meses, format_func=nombre_mes)
    d = df[df["AñoMes"] == mes]
    r = est.resumen_periodo(d)

    # Cifra principal: el dinero disponible del mes
    st.metric("💵 Total disponible del mes", pesos(r["disponible"]))
    c3, c4 = st.columns(2)
    c3.metric("🚗 Días trabajados", r["dias_trabajados"])
    c4.metric("📊 Promedio disponible por día trabajado", pesos(r["promedio_dia"]))

    if r["mejor_dia"]:
        c5, c6 = st.columns(2)
        c5.metric(f"⭐ Mejor día ({r['mejor_dia'][0]:%d/%m})", pesos(r["mejor_dia"][1]))
        c6.metric(f"⚠️ Peor día ({r['peor_dia'][0]:%d/%m})", pesos(r["peor_dia"][1]))

    c1, c2 = st.columns(2)
    c1.metric("📥 Ingresos", pesos(r["ingresos"]))
    c2.metric("📤 Gastos", pesos(r["gastos"]))
    c7, c8 = st.columns(2)
    c7.metric("📈 Ganancia estimada", pesos(r["ganancia"]))
    c8.metric("⚖️ Diferencia", pesos(r["diferencia"]))

    st.markdown("##### Disponible por día")
    por_dia = d.set_index(d["Fecha"].dt.strftime("%d"))["Total Disp"]
    _barras(por_dia)

    st.markdown("##### Ingresos por plataforma")
    _barras(r["por_plataforma"], ordenar="-y")
    st.markdown("##### Gastos por categoría")
    _barras(r["por_categoria"], ordenar="-y")


# ---------------------------------------------------------------------------
# Pestaña AÑO
# ---------------------------------------------------------------------------
def _tab_anio(df):
    anios = sorted(df["Fecha"].dt.year.unique(), reverse=True)
    anio = st.selectbox("Año", [int(a) for a in anios])
    d = df[df["Fecha"].dt.year == anio]
    r = est.resumen_periodo(d)
    por_mes = est.resumen_por_mes(d)

    # Cifra principal: el dinero disponible del año
    st.metric("💵 Total disponible del año", pesos(r["disponible"]))
    c3, c4 = st.columns(2)
    c3.metric("🚗 Días trabajados", r["dias_trabajados"])
    c4.metric("📊 Promedio disponible por día trabajado", pesos(r["promedio_dia"]))

    con_dias = por_mes[por_mes["Dias"] > 0]
    if not con_dias.empty:
        mejor = con_dias["Disponible"].idxmax()
        peor = con_dias["Disponible"].idxmin()
        c5, c6 = st.columns(2)
        c5.metric(f"⭐ Mejor mes ({nombre_mes(mejor).split()[0]})", pesos(con_dias.loc[mejor, "Disponible"]))
        c6.metric(f"⚠️ Peor mes ({nombre_mes(peor).split()[0]})", pesos(con_dias.loc[peor, "Disponible"]))

    c1, c2 = st.columns(2)
    c1.metric("📥 Ingresos", pesos(r["ingresos"]))
    c2.metric("📤 Gastos", pesos(r["gastos"]))
    c7, c8 = st.columns(2)
    c7.metric("📈 Ganancia estimada", pesos(r["ganancia"]))
    c8.metric("⚖️ Diferencia", pesos(r["diferencia"]))

    etiquetas = [MESES_CORTOS[int(m.split("-")[1]) - 1] for m in por_mes.index]

    st.markdown("##### Disponible por mes")
    disponible_mes = por_mes["Disponible"].copy()
    disponible_mes.index = etiquetas
    _barras(disponible_mes)

    st.markdown("##### Disponible acumulado")
    _linea(disponible_mes.cumsum())

    st.markdown("##### Detalle por mes")
    tabla = por_mes[["Disponible", "Dias", "Promedio", "Ingresos", "Gastos", "Ganancia"]].copy()
    tabla.index = [nombre_mes(m).split()[0] for m in por_mes.index]
    for col in ["Disponible", "Promedio", "Ingresos", "Gastos", "Ganancia"]:
        tabla[col] = tabla[col].map(pesos)
    tabla = tabla.rename(columns={
        "Dias": "Días", "Promedio": "Promedio/día", "Ganancia": "Ganancia est.",
    })
    st.dataframe(tabla, width="stretch")

    st.markdown("##### Ingresos por plataforma")
    _barras(r["por_plataforma"], ordenar="-y")


# ---------------------------------------------------------------------------
def mostrar():
    st.subheader("🏠 Inicio")
    resumen = db.resumen_dias()
    if resumen.empty:
        st.info("Aún no hay días registrados. Ve a ➕ Registrar día para empezar.")
        return

    df = est.preparar(resumen)
    tab_hoy, tab_mes, tab_anio = st.tabs(["Hoy", "Mes", "Año"])
    with tab_hoy:
        _tab_hoy(df)
    with tab_mes:
        _tab_mes(df)
    with tab_anio:
        _tab_anio(df)
