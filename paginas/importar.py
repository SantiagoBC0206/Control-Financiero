"""
paginas/importar.py — Importar los Excel (o CSV) de cada mes.
"""

import pandas as pd
import streamlit as st

import importador as imp
from utilidades import MESES, hoy, nombre_mes, pesos

ETIQUETA_ESTADO = {
    "nuevo": "🆕 Nuevo",
    "igual": "✅ Ya existe igual",
    "distinto": "⚠️ Ya existe, es diferente",
}


def _mostrar_analisis(analisis):
    """Muestra el resultado de leer una hoja: tabla, comprobación de totales y avisos."""
    dias = analisis["dias"]
    if dias:
        filas = []
        for d in dias:
            t = imp.totales_dia(d)
            filas.append({
                "Fecha": d["fecha"].strftime("%d/%m/%Y"),
                "Estado": ETIQUETA_ESTADO[d["estado"]],
                "Ingresos": pesos(t["Total Ingresos"]),
                "Gastos": pesos(t["Total Gastos"]),
                "Ganancia est.": pesos(t["Ganancia Est"]),
                "Disponible": pesos(t["Total Disp"]),
            })
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
    else:
        st.info("No encontré días con movimiento en esta hoja.")

    if analisis["sin_movimiento"]:
        st.caption(f"{analisis['sin_movimiento']} días sin movimiento (descanso) no se importan.")

    if analisis["comparacion"]:
        st.markdown("**Comprobación contra la fila de totales del Excel**")
        for etiqueta, calculado, en_excel in analisis["comparacion"]:
            if calculado == en_excel:
                st.markdown(f"✅ {etiqueta}: {pesos(calculado)}")
            else:
                st.markdown(
                    f"⚠️ {etiqueta}: el sistema suma {pesos(calculado)} y el Excel dice {pesos(en_excel)}"
                )

    for fila, motivo in analisis["descartadas"]:
        st.warning(f"Fila {fila} omitida: {motivo}")
    for aviso in analisis["avisos"]:
        st.caption(f"ℹ️ {aviso}")


def mostrar():
    st.subheader("📥 Importar Excel")
    st.caption(
        "Sube el Excel de uno o varios meses (.xlsx o .csv). Antes de guardar nada "
        "verás una vista previa y la comprobación de los totales. Subir dos veces el "
        "mismo mes no duplica información."
    )

    archivos = st.file_uploader(
        "Archivos", type=["xlsx", "csv"], accept_multiple_files=True
    )
    if not archivos:
        return

    conflicto = st.radio(
        "Si un día ya existe en el sistema y es diferente al del archivo:",
        ["Conservar el que ya está", "Reemplazar con el del archivo"],
        index=0,
    )

    todos = []
    for archivo in archivos:
        try:
            hojas = imp.leer_archivo(archivo.name, archivo.getvalue())
        except Exception as error:
            st.error(f"No pude leer {archivo.name}: {error}")
            continue

        for nombre_hoja, crudo in hojas:
            titulo = archivo.name if len(hojas) == 1 else f"{archivo.name} — hoja «{nombre_hoja}»"
            base = imp.analizar_hoja(crudo)
            if base is None:
                st.warning(f"{titulo}: no encontré las columnas esperadas (Fecha, Didi, ...). Se omite.")
                continue

            # ¿El nombre dice un mes y las fechas de adentro dicen otro?
            detectado = imp.detectar_mes(nombre_hoja, archivo.name)
            en_fechas = base["meses_en_fechas"]
            desajuste = bool(detectado) and en_fechas != {detectado}
            clave = f"{archivo.name}|{nombre_hoja}"

            with st.expander(titulo, expanded=True):
                if en_fechas:
                    st.caption(
                        "Fechas escritas en el Excel: "
                        + ", ".join(nombre_mes(f"{a}-{m:02d}") for a, m in sorted(en_fechas))
                    )
                if desajuste:
                    st.warning(
                        f"Por el nombre parece ser **{nombre_mes('%d-%02d' % detectado)}**, pero las "
                        "fechas de adentro son de otro mes. Revisa la opción de abajo antes de importar."
                    )
                usar_mes = st.checkbox(
                    "Las fechas del Excel no son las del mes real: usar el mes que elijo aquí "
                    "(solo se toma el número de día de cada fila)",
                    value=desajuste,
                    key=f"usar|{clave}",
                )
                analisis = base
                if usar_mes:
                    por_defecto = detectado or (min(en_fechas) if en_fechas else (hoy().year, hoy().month))
                    c1, c2 = st.columns(2)
                    mes_sel = c1.selectbox(
                        "Mes real", list(range(1, 13)), index=por_defecto[1] - 1,
                        format_func=lambda m: MESES[m - 1], key=f"mes|{clave}",
                    )
                    anio_sel = c2.number_input(
                        "Año real", min_value=2000, max_value=2100, value=por_defecto[0],
                        step=1, key=f"anio|{clave}",
                    )
                    analisis = imp.analizar_hoja(crudo, mes_forzado=(int(anio_sel), int(mes_sel)))

                imp.clasificar(analisis["dias"])
                _mostrar_analisis(analisis)
            todos.extend(analisis["dias"])

    if not todos:
        return

    fechas = [d["fecha"] for d in todos]
    if len(fechas) != len(set(fechas)):
        st.warning("Hay fechas repetidas entre los archivos; si las importas, la última subida es la que queda.")

    reemplazar = conflicto.startswith("Reemplazar")
    nuevos = sum(d["estado"] == "nuevo" for d in todos)
    iguales = sum(d["estado"] == "igual" for d in todos)
    distintos = sum(d["estado"] == "distinto" for d in todos)
    a_guardar = nuevos + (distintos if reemplazar else 0)

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("🆕 Nuevos", nuevos)
    c2.metric("✅ Ya existen", iguales)
    c3.metric("⚠️ Diferentes", distintos)

    if st.button(f"🚀 Importar {a_guardar} días", type="primary", disabled=(a_guardar == 0), width="stretch"):
        n, r, o = imp.importar(todos, reemplazar_distintos=reemplazar)
        st.success(f"Listo: {n} días nuevos, {r} reemplazados y {o} omitidos.")
        st.caption("Ve a 🏠 Inicio para ver los resultados.")
