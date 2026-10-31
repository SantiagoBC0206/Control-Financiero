
import pandas as pd


def preparar(df):
    """
    Prepara los datos diarios para los análisis del dashboard.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    df = df.copy()

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df = df.sort_values("Fecha").reset_index(drop=True)

    columnas_numericas = [
        "Total Ingresos",
        "Total Gastos",
        "Ganancia Est",
        "Total Disp",
        "Diferencia",
        "Efectivo",
        "Nequi",
    ]

    for columna in columnas_numericas:
        if columna in df.columns:
            df[columna] = pd.to_numeric(
                df[columna], errors="coerce"
            ).fillna(0)

    if "Total Ingresos" in df.columns:
        df["Trabajado"] = df["Total Ingresos"] > 0
    else:
        df["Trabajado"] = False

    df["AñoMes"] = df["Fecha"].dt.strftime("%Y-%m")

    return df


def grupos_columnas(df):
    """
    Separa las columnas correspondientes a ingresos,
    gastos y movimientos de dinero.
    """
    columnas_ingresos = [
        "Didi",
        "InDrive",
        "Uber",
        "Extras",
    ]

    columnas_gastos = [
        "Gasolina",
        "Apps",
        "Comida",
        "Otros Gastos",
    ]

    columnas_movimientos = [
        "Efectivo",
        "Nequi",
    ]

    ingresos = [
        columna for columna in columnas_ingresos
        if columna in df.columns
    ]

    gastos = [
        columna for columna in columnas_gastos
        if columna in df.columns
    ]

    movimientos = [
        columna for columna in columnas_movimientos
        if columna in df.columns
    ]

    return ingresos, gastos, movimientos


def resumen_periodo(df):
    """
    Calcula los indicadores generales del período seleccionado.

    Total Disp se acumula sumando los valores diarios.
    Efectivo y Nequi corresponden al último registro.
    """
    df = preparar(df)

    if df.empty:
        return {
            "ingresos": 0,
            "gastos": 0,
            "ganancia": 0,
            "disponible": 0,
            "diferencia": 0,
            "promedio_dia": 0,
            "mejor_dia": None,
            "peor_dia": None,
            "por_plataforma": {},
            "por_categoria": {},
            "ultimo_registro": None,
        }

    ingresos_cols, gastos_cols, _ = grupos_columnas(df)

    total_ingresos = (
        df["Total Ingresos"].sum()
        if "Total Ingresos" in df.columns else 0
    )

    total_gastos = (
        df["Total Gastos"].sum()
        if "Total Gastos" in df.columns else 0
    )

    ganancia = total_ingresos - total_gastos

    # Suma de los valores diarios de dinero disponible.
    disponible = (
        df["Total Disp"].sum()
        if "Total Disp" in df.columns else 0
    )

    # La diferencia también se acumula durante el período.
    diferencia = (
        df["Diferencia"].sum()
        if "Diferencia" in df.columns else 0
    )

    dias_trabajados = df[df["Trabajado"]]

    if not dias_trabajados.empty:
        promedio_dia = (
            dias_trabajados["Total Disp"].mean()
            if "Total Disp" in dias_trabajados.columns else 0
        )

        mejor_dia = (
            dias_trabajados.loc[
                dias_trabajados["Ganancia Est"].idxmax()
            ]
            if "Ganancia Est" in dias_trabajados.columns else None
        )

        peor_dia = (
            dias_trabajados.loc[
                dias_trabajados["Ganancia Est"].idxmin()
            ]
            if "Ganancia Est" in dias_trabajados.columns else None
        )
    else:
        promedio_dia = 0
        mejor_dia = None
        peor_dia = None

    ultimo_registro = df.iloc[-1]

    por_plataforma = {
        columna: float(df[columna].sum())
        for columna in ingresos_cols
    }

    por_categoria = {
        columna: float(df[columna].sum())
        for columna in gastos_cols
    }

    return {
        "ingresos": float(total_ingresos),
        "gastos": float(total_gastos),
        "ganancia": float(ganancia),
        "disponible": float(disponible),
        "diferencia": float(diferencia),
        "promedio_dia": float(promedio_dia),
        "mejor_dia": mejor_dia,
        "peor_dia": peor_dia,
        "por_plataforma": por_plataforma,
        "por_categoria": por_categoria,
        "ultimo_registro": ultimo_registro,
    }


def resumen_por_mes(df):
    """
    Genera un resumen independiente para cada mes.

    Total Disp se suma entre todos los registros del mes.
    Efectivo y Nequi se conservan como saldos del último
    registro de cada mes.
    """
    df = preparar(df)

    if df.empty:
        return pd.DataFrame()

    columnas = [
        "Total Ingresos",
        "Total Gastos",
        "Ganancia Est",
        "Total Disp",
        "Diferencia",
    ]

    for columna in columnas:
        if columna not in df.columns:
            df[columna] = 0

    resumen = (
        df.groupby("AñoMes")
        .agg(
            Ingresos=("Total Ingresos", "sum"),
            Gastos=("Total Gastos", "sum"),
            Ganancia=("Ganancia Est", "sum"),
            Disponible=("Total Disp", "sum"),
            Diferencia=("Diferencia", "sum"),
            Dias=("Trabajado", "sum"),
        )
        .reset_index()
    )

    # Promedio del dinero disponible en días trabajados.
    promedios = (
        df[df["Trabajado"]]
        .groupby("AñoMes")["Total Disp"]
        .mean()
    )

    resumen["Promedio"] = (
        resumen["AñoMes"].map(promedios).fillna(0)
    )

    return resumen


def dia_anterior_trabajado(df, fecha):
    """
    Obtiene el registro del día trabajado inmediatamente
    anterior a la fecha indicada.
    """
    df = preparar(df)

    if df.empty:
        return None

    fecha = pd.to_datetime(fecha)

    anteriores = df[
        (df["Fecha"] < fecha) & (df["Trabajado"])
    ]

    if anteriores.empty:
        return None

    return anteriores.iloc[-1]
