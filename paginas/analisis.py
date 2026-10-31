
"""analisis.py — Análisis financiero del Control Financiero."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import db
import estadisticas as est
from utilidades import pesos, hoy, nombre_mes


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def moneda(valor):
    """Convierte un valor numérico a formato de pesos."""
    try:
        return pesos(float(valor or 0))
    except (ValueError, TypeError):
        return pesos(0)


def obtener_columnas(df, grupo):
    """
    Obtiene las columnas de plataformas o categorías,
    incluyendo las personalizadas que existan en la BD.
    """
    nombres = db.nombres_disponibles(grupo)

    disponibles = [
        nombre for nombre in nombres
        if nombre in df.columns
    ]

    return disponibles


def calcular_resumen(df, plataformas, categorias):
    """Calcula los principales indicadores financieros."""

    if df.empty:
        return {}

    ingresos = float(df["Total Ingresos"].sum())
    gastos = float(df["Total Gastos"].sum())
    ganancia = ingresos - gastos

    dias_trabajados = df[df["Trabajado"]]

    cantidad_dias = len(dias_trabajados)

    porcentaje_gastos = (
        gastos / ingresos * 100
        if ingresos > 0 else 0
    )

    promedio_ingresos = (
        ingresos / cantidad_dias
        if cantidad_dias else 0
    )

    promedio_gastos = (
        gastos / cantidad_dias
        if cantidad_dias else 0
    )

    promedio_ganancia = (
        ganancia / cantidad_dias
        if cantidad_dias else 0
    )

    ingresos_plataformas = {
        nombre: float(df[nombre].sum())
        for nombre in plataformas
    }

    gastos_categorias = {
        nombre: float(df[nombre].sum())
        for nombre in categorias
    }

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ganancia": ganancia,
        "porcentaje_gastos": porcentaje_gastos,
        "dias_trabajados": cantidad_dias,
        "promedio_ingresos": promedio_ingresos,
        "promedio_gastos": promedio_gastos,
        "promedio_ganancia": promedio_ganancia,
        "plataformas": ingresos_plataformas,
        "categorias": gastos_categorias,
    }


def crear_grafico_barras(
    df,
    x,
    y,
    titulo,
    color=None,
):
    """Crea un gráfico de barras financiero."""

    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        title=titulo,
        text_auto=".2s",
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Valor en pesos",
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
    )

    fig.update_yaxes(
        tickprefix="$",
        separatethousands=True,
    )

    return fig


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def mostrar():

    st.title("📊 Análisis financiero")

    st.caption(
        "Analiza el comportamiento de los ingresos, "
        "gastos y ganancias de la actividad."
    )

    # -----------------------------------------------------
    # 1. CARGAR DATOS
    # -----------------------------------------------------

    try:
        df_original = db.resumen_dias()

    except Exception as e:
        st.error(
            f"No fue posible cargar los registros: {e}"
        )
        return

    if df_original is None or df_original.empty:
        st.info(
            "Todavía no existen registros para realizar "
            "un análisis financiero."
        )
        return

    df = est.preparar(df_original)

    if df.empty:
        st.warning(
            "No se encontraron registros válidos."
        )
        return

    # Obtener plataformas y categorías dinámicas.
    try:
        plataformas = obtener_columnas(
            df,
            "ingresos",
        )

        categorias = obtener_columnas(
            df,
            "gastos",
        )

    except Exception as e:
        st.error(
            f"No fue posible obtener las categorías: {e}"
        )
        return

    # Garantizar que existan las columnas.
    for columna in plataformas + categorias:
        if columna not in df.columns:
            df[columna] = 0

    # -----------------------------------------------------
    # 2. FILTROS
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🔎 Período de análisis")

    tipo_filtro = st.radio(
        "Selecciona el período:",
        [
            "Por Mes",
            "Rango Personalizado",
        ],
        horizontal=True,
        key="analisis_tipo_filtro",
    )

    fecha_minima = df["Fecha"].min().date()
    fecha_maxima = df["Fecha"].max().date()

    if tipo_filtro == "Por Mes":

        meses = sorted(
            df["AñoMes"].dropna().unique().tolist(),
            reverse=True,
        )

        mes_actual = hoy().strftime("%Y-%m")

        mes_predeterminado = (
            mes_actual
            if mes_actual in meses
            else meses[0]
        )

        mes = st.selectbox(
            "Mes:",
            options=meses,
            index=meses.index(mes_predeterminado),
            format_func=nombre_mes,
            key="analisis_mes",
        )

        df_periodo = df[
            df["AñoMes"] == mes
        ].copy()

        titulo_periodo = nombre_mes(mes)

    else:

        c1, c2 = st.columns(2)

        with c1:
            desde = st.date_input(
                "Desde:",
                value=fecha_minima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="analisis_desde",
            )

        with c2:
            hasta = st.date_input(
                "Hasta:",
                value=fecha_maxima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="analisis_hasta",
            )

        if desde > hasta:
            st.warning(
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            )
            return

        df_periodo = df[
            (df["Fecha"].dt.date >= desde)
            & (df["Fecha"].dt.date <= hasta)
        ].copy()

        titulo_periodo = (
            f"{desde.strftime('%d/%m/%Y')} "
            f"al {hasta.strftime('%d/%m/%Y')}"
        )

    if df_periodo.empty:
        st.info(
            "No existen registros para el período seleccionado."
        )
        return

    # -----------------------------------------------------
    # 3. RESUMEN FINANCIERO
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("💰 Resumen financiero")

    resumen = calcular_resumen(
        df_periodo,
        plataformas,
        categorias,
    )

    st.caption(
        f"Resultados correspondientes a {titulo_periodo}"
    )

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Total de ingresos",
            moneda(resumen["ingresos"]),
        )

    with c2:
        st.metric(
            "Total de gastos",
            moneda(resumen["gastos"]),
        )

    c3, c4 = st.columns(2)

    with c3:
        st.metric(
            "Ganancia estimada",
            moneda(resumen["ganancia"]),
        )

    with c4:
        st.metric(
            "Gastos sobre ingresos",
            f"{resumen['porcentaje_gastos']:.1f}%",
        )

    st.caption(
        "La ganancia estimada se calcula restando los gastos "
        "a los ingresos. El porcentaje indica qué parte "
        "de los ingresos representa el total de gastos."
    )

    # -----------------------------------------------------
    # 4. RENDIMIENTO POR PLATAFORMA
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🚗 Rendimiento por plataforma")

    datos_plataformas = resumen["plataformas"]

    df_plataformas = pd.DataFrame(
        [
            {
                "Plataforma": nombre,
                "Ingresos": valor,
                "Participación": (
                    valor / resumen["ingresos"] * 100
                    if resumen["ingresos"] > 0 else 0
                ),
            }
            for nombre, valor in datos_plataformas.items()
        ]
    )

    df_plataformas = df_plataformas.sort_values(
        "Ingresos",
        ascending=False,
    )

    df_plataformas_positivas = df_plataformas[
        df_plataformas["Ingresos"] > 0
    ]

    if not df_plataformas_positivas.empty:

        col1, col2 = st.columns(2)

        with col1:
            fig_plataformas = px.bar(
                df_plataformas_positivas,
                x="Plataforma",
                y="Ingresos",
                title="Ingresos por plataforma",
                text_auto=".2s",
            )

            fig_plataformas.update_layout(
                yaxis_title="Ingresos en pesos",
                xaxis_title=None,
                margin=dict(l=5, r=5, t=50, b=5),
            )

            fig_plataformas.update_yaxes(
                tickprefix="$",
                separatethousands=True,
            )

            st.plotly_chart(
                fig_plataformas,
                use_container_width=True,
            )

        with col2:
            fig_participacion = px.pie(
                df_plataformas_positivas,
                names="Plataforma",
                values="Ingresos",
                hole=0.55,
                title="Participación en los ingresos",
            )

            fig_participacion.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            fig_participacion.update_layout(
                margin=dict(l=5, r=5, t=50, b=5),
            )

            st.plotly_chart(
                fig_participacion,
                use_container_width=True,
            )

        st.markdown("**Detalle por plataforma**")

        tabla_plataformas = df_plataformas.copy()

        tabla_plataformas["Participación"] = (
            tabla_plataformas["Participación"].round(2)
        )

        st.dataframe(
            tabla_plataformas,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ingresos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Participación": st.column_config.NumberColumn(
                    format="%.2f%%",
                ),
            },
        )

    else:
        st.info(
            "No hay ingresos registrados por plataforma "
            "en este período."
        )

    # -----------------------------------------------------
    # 5. ANÁLISIS DE GASTOS
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🧾 Análisis de gastos")

    datos_categorias = resumen["categorias"]

    df_categorias = pd.DataFrame(
        [
            {
                "Categoría": nombre,
                "Gastos": valor,
                "Participación": (
                    valor / resumen["gastos"] * 100
                    if resumen["gastos"] > 0 else 0
                ),
            }
            for nombre, valor in datos_categorias.items()
        ]
    )

    df_categorias = df_categorias.sort_values(
        "Gastos",
        ascending=False,
    )

    df_categorias_positivas = df_categorias[
        df_categorias["Gastos"] > 0
    ]

    if not df_categorias_positivas.empty:

        col1, col2 = st.columns(2)

        with col1:

            fig_categorias = px.bar(
                df_categorias_positivas,
                x="Categoría",
                y="Gastos",
                title="Gastos por categoría",
                text_auto=".2s",
            )

            fig_categorias.update_layout(
                xaxis_title=None,
                yaxis_title="Gastos en pesos",
                margin=dict(l=5, r=5, t=50, b=5),
            )

            fig_categorias.update_yaxes(
                tickprefix="$",
                separatethousands=True,
            )

            st.plotly_chart(
                fig_categorias,
                use_container_width=True,
            )

        with col2:

            fig_distribucion = px.pie(
                df_categorias_positivas,
                names="Categoría",
                values="Gastos",
                hole=0.55,
                title="Distribución de los gastos",
            )

            fig_distribucion.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            fig_distribucion.update_layout(
                margin=dict(l=5, r=5, t=50, b=5),
            )

            st.plotly_chart(
                fig_distribucion,
                use_container_width=True,
            )

        st.markdown("**Detalle de gastos**")

        st.dataframe(
            df_categorias,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Gastos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Participación": st.column_config.NumberColumn(
                    format="%.2f%%",
                ),
            },
        )

    else:
        st.info(
            "No hay gastos registrados por categoría "
            "en este período."
        )

    # -----------------------------------------------------
    # 6. RENDIMIENTO POR JORNADA
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🗓️ Rendimiento por jornada")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Ingresos promedio",
            moneda(resumen["promedio_ingresos"]),
        )

    with c2:
        st.metric(
            "Gastos promedio",
            moneda(resumen["promedio_gastos"]),
        )

    with c3:
        st.metric(
            "Ganancia promedio",
            moneda(resumen["promedio_ganancia"]),
        )

    st.caption(
        "Los promedios se calculan dividiendo los valores "
        "acumulados entre los días trabajados."
    )

    df_trabajado = df_periodo[
        df_periodo["Trabajado"]
    ].copy()

    if not df_trabajado.empty:

        df_trabajado["Día"] = (
            df_trabajado["Fecha"].dt.strftime("%d/%m")
        )

        fig_jornadas = go.Figure()

        fig_jornadas.add_trace(
            go.Bar(
                x=df_trabajado["Día"],
                y=df_trabajado["Total Ingresos"],
                name="Ingresos",
            )
        )

        fig_jornadas.add_trace(
            go.Bar(
                x=df_trabajado["Día"],
                y=df_trabajado["Total Gastos"],
                name="Gastos",
            )
        )

        fig_jornadas.add_trace(
            go.Scatter(
                x=df_trabajado["Día"],
                y=df_trabajado["Ganancia Est"],
                name="Ganancia estimada",
                mode="lines+markers",
                yaxis="y2",
            )
        )

        fig_jornadas.update_layout(
            title="Comportamiento financiero por jornada",
            xaxis_title="Día trabajado",
            yaxis=dict(
                title="Ingresos y gastos",
                tickprefix="$",
            ),
            yaxis2=dict(
                title="Ganancia estimada",
                overlaying="y",
                side="right",
                tickprefix="$",
                showgrid=False,
            ),
            barmode="group",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=55, b=10),
        )

        st.plotly_chart(
            fig_jornadas,
            use_container_width=True,
        )

        mejor = df_trabajado.loc[
            df_trabajado["Ganancia Est"].idxmax()
        ]

        peor = df_trabajado.loc[
            df_trabajado["Ganancia Est"].idxmin()
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🏆 Jornada con mayor ganancia**")
            st.write(
                mejor["Fecha"].strftime("%d/%m/%Y")
            )
            st.write(
                moneda(mejor["Ganancia Est"])
            )

        with col2:
            st.markdown("**📉 Jornada con menor ganancia**")
            st.write(
                peor["Fecha"].strftime("%d/%m/%Y")
            )
            st.write(
                moneda(peor["Ganancia Est"])
            )

    else:
        st.info(
            "No hay jornadas con ingresos registrados "
            "en este período."
        )

    # -----------------------------------------------------
    # 7. EVOLUCIÓN MENSUAL
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📈 Evolución mensual")

    resumen_mensual = est.resumen_por_mes(df)

    if not resumen_mensual.empty:

        resumen_mensual = resumen_mensual.sort_values(
            "AñoMes"
        ).copy()

        resumen_mensual["Mes"] = (
            resumen_mensual["AñoMes"].apply(nombre_mes)
        )

        datos_mensuales = resumen_mensual.melt(
            id_vars=["Mes"],
            value_vars=[
                "Ingresos",
                "Gastos",
                "Ganancia",
            ],
            var_name="Concepto",
            value_name="Valor",
        )

        fig_mensual = px.bar(
            datos_mensuales,
            x="Mes",
            y="Valor",
            color="Concepto",
            barmode="group",
            title="Ingresos, gastos y ganancias por mes",
        )

        fig_mensual.update_layout(
            xaxis_title=None,
            yaxis_title="Valor en pesos",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=55, b=10),
        )

        fig_mensual.update_yaxes(
            tickprefix="$",
            separatethousands=True,
        )

        st.plotly_chart(
            fig_mensual,
            use_container_width=True,
        )

        st.markdown("**Historial mensual**")

        tabla_mensual = resumen_mensual[
            [
                "Mes",
                "Ingresos",
                "Gastos",
                "Ganancia",
                "Dias",
            ]
        ].rename(
            columns={
                "Dias": "Días trabajados",
            }
        )

        st.dataframe(
            tabla_mensual,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ingresos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Gastos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Ganancia": st.column_config.NumberColumn(
                    format="$%d",
                ),
            },
        )

    else:
        st.info(
            "No hay suficientes datos para mostrar "
            "la evolución mensual."
        )

    # -----------------------------------------------------
    # 8. EXPORTACIÓN DEL ANÁLISIS
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📥 Exportar análisis")

    reporte = df_periodo.copy()

    columnas_reporte = [
        "Fecha",
        *plataformas,
        "Total Ingresos",
        *categorias,
        "Total Gastos",
        "Ganancia Est",
    ]

    columnas_reporte = [
        columna for columna in columnas_reporte
        if columna in reporte.columns
    ]

    reporte = reporte[columnas_reporte].copy()

    reporte["Fecha"] = (
        reporte["Fecha"].dt.strftime("%d/%m/%Y")
    )

    archivo = reporte.to_csv(
        index=False,
        sep=";",
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    st.download_button(
        "📊 Descargar análisis en CSV",
        data=archivo,
        file_name="analisis_financiero.csv",
        mime="text/csv",
        use_container_width=True,
    )
