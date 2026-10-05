"""
importador.py — Lee los Excel/CSV mensuales y los convierte en días del sistema.

Qué hace:
  - Acepta .xlsx (todas sus hojas) y .csv (separado por coma, punto y coma o tab).
  - Busca solita la fila de encabezados (la que tiene la columna "Fecha"),
    aunque haya títulos arriba.
  - Ignora las columnas calculadas (Total Ingresos, etc.) y las usa para
    COMPROBAR que lo leído cuadra con el Excel.
  - Descarta con aviso las filas que no son un día (por ejemplo "Total Mes").
  - Compara cada día con lo que ya hay en el sistema: nuevo, igual o diferente.
    Así subir dos veces el mismo mes no duplica nada.
  - Si las fechas de adentro del Excel no son las del mes real (porque se duplicó
    un archivo y no se le cambiaron), se puede indicar el mes correcto: entonces
    solo se usa el NÚMERO DE DÍA de cada fila.
"""

import calendar
import csv
import io
import re
import unicodedata
from datetime import date, datetime

import pandas as pd

import db

# Nombre de la columna en el Excel (normalizado) -> (grupo, nombre en el sistema)
COLUMNAS = {
    "didi": ("ingresos", "Didi"),
    "indrive": ("ingresos", "InDrive"),
    "uber": ("ingresos", "Uber"),
    "extras": ("ingresos", "Extras"),
    "gasolina": ("gastos", "Gasolina"),
    "apps": ("gastos", "Apps"),
    "comida": ("gastos", "Comida"),
    "otros gastos": ("gastos", "Otros Gastos"),
    "otros": ("gastos", "Otros Gastos"),
    "efectivo": ("movimientos", "Efectivo"),
    "nequi": ("movimientos", "Nequi"),
}
COLUMNAS_OBSERVACIONES = {"observaciones", "observacion", "notas", "nota"}

# Columnas calculadas del Excel -> nombre de la columna de resumen
COLUMNAS_TOTALES = {
    "total ingresos": "Total Ingresos",
    "total gastos": "Total Gastos",
    "ganancia est": "Ganancia Est",
    "ganancia estimada": "Ganancia Est",
    "total disp": "Total Disp",
    "total disponible": "Total Disp",
    "diferencia": "Diferencia",
}


# ---------------------------------------------------------------------------
# Lectura de archivos
# ---------------------------------------------------------------------------
def _norm(valor):
    """Texto en minúsculas, sin tildes ni guiones bajos ('Otros_Gastos' -> 'otros gastos')."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    texto = unicodedata.normalize("NFD", str(valor))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto.replace("_", " ")).strip().lower()


def leer_archivo(nombre, contenido):
    """Devuelve una lista de (nombre_hoja, DataFrame sin encabezado) del archivo."""
    if nombre.lower().endswith(".csv"):
        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = contenido.decode("latin-1")
        try:
            dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t")
        except csv.Error:
            dialecto = csv.excel
        filas = list(csv.reader(io.StringIO(texto), dialecto))
        ancho = max((len(f) for f in filas), default=0)
        filas = [f + [None] * (ancho - len(f)) for f in filas]
        return [("CSV", pd.DataFrame(filas, dtype=object))]

    hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None, header=None, dtype=object)
    return list(hojas.items())


# ---------------------------------------------------------------------------
# Detectar el mes por el nombre del archivo u hoja
# ---------------------------------------------------------------------------
_NOMBRES_MES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def detectar_mes(*textos):
    """Busca (año, mes) en nombres como 'Octubre 2025' o 'Control_Oct_2025.xlsx'.

    Se revisan los textos en orden (por ejemplo: nombre de la hoja y luego del archivo).
    Devuelve None si no encuentra el mes Y el año.
    """
    mes = anio = None
    for texto in textos:
        normal = _norm(texto)
        if mes is None:
            for palabra in re.findall(r"[a-z]+", normal):
                if palabra in _NOMBRES_MES:
                    mes = _NOMBRES_MES[palabra]
                    break
        if anio is None:
            encontrado = re.search(r"(?<!\d)(20\d{2})(?!\d)", normal)
            if encontrado:
                anio = int(encontrado.group(1))
    return (anio, mes) if mes and anio else None


# ---------------------------------------------------------------------------
# Conversión de celdas
# ---------------------------------------------------------------------------
def _vacio(valor):
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    return bool(pd.isna(valor))


def _a_fecha(valor):
    """Convierte una celda a fecha. Devuelve None si no es una fecha válida."""
    if _vacio(valor):
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        f = valor.date()
    elif isinstance(valor, date):
        f = valor
    else:
        texto = str(valor).strip()
        f = None
        for formato in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
            try:
                f = datetime.strptime(texto, formato).date()
                break
            except ValueError:
                continue
    if f is None or not (2000 <= f.year <= 2100):
        return None
    return f


def _a_entero(valor):
    """Convierte una celda a pesos enteros. Vacío = 0. Lanza ValueError si no es número."""
    if _vacio(valor):
        return 0
    if isinstance(valor, (int, float)):
        return int(round(valor))
    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if texto in {"", "-", "–"}:
        return 0
    negativo = texto.startswith("-") or (texto.startswith("(") and texto.endswith(")"))
    texto = texto.strip("()-")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", texto):  # 1.234.567 o 1,234,567
        texto = re.sub(r"[.,]", "", texto)
    elif re.fullmatch(r"\d+,\d{1,2}", texto):  # 1234,5
        texto = texto.replace(",", ".")
    numero = float(texto)  # lanza ValueError si no es número
    return int(round(-numero if negativo else numero))


# ---------------------------------------------------------------------------
# Análisis de una hoja
# ---------------------------------------------------------------------------
def totales_dia(d):
    """Totales calculados de un día (mismas fórmulas del Excel)."""
    ing, gas, mov = (sum(d[g].values()) for g in ("ingresos", "gastos", "movimientos"))
    return {
        "Total Ingresos": ing,
        "Total Gastos": gas,
        "Ganancia Est": ing - gas,
        "Total Disp": mov,
        "Diferencia": (ing - gas) - mov,
    }


def analizar_hoja(crudo, mes_forzado=None):
    """Lee una hoja. Devuelve None si no tiene columna Fecha; si no, un diccionario con:

    dias            : días con movimiento, listos para guardar
    sin_movimiento  : cuántos días venían en cero (descanso) y se omiten
    descartadas     : [(número de fila, motivo)] filas que no se pudieron leer
    avisos          : textos de advertencia (columnas ignoradas, descuadres...)
    comparacion     : [(etiqueta, calculado, valor_del_excel)] contra la fila de totales
    meses_en_fechas : {(año, mes)} que aparecen en la columna Fecha del Excel

    mes_forzado = (año, mes): ignora el mes y el año escritos en la columna Fecha y
    usa ese mes, tomando solo el número de día de cada fila.
    """
    # 1) Buscar la fila de encabezados
    fila_enc = None
    for i in range(min(15, len(crudo))):
        if any(_norm(c) == "fecha" for c in crudo.iloc[i].tolist()):
            fila_enc = i
            break
    if fila_enc is None:
        return None

    encabezados = [_norm(c) for c in crudo.iloc[fila_enc].tolist()]
    posicion = {}
    for j, nombre in enumerate(encabezados):
        if nombre and nombre not in posicion:
            posicion[nombre] = j

    conocidas = (
        set(COLUMNAS) | set(COLUMNAS_TOTALES) | COLUMNAS_OBSERVACIONES | {"fecha"}
    )
    if not (set(posicion) & set(COLUMNAS)):
        return None  # tiene Fecha pero ninguna columna de ingresos/gastos conocida

    avisos = []
    ignoradas = [n for n in posicion if n not in conocidas]
    if ignoradas:
        avisos.append("Columnas no reconocidas (se ignoran): " + ", ".join(ignoradas))

    j_fecha = posicion["fecha"]
    dias, descartadas, sin_movimiento = [], [], 0
    fila_totales = None
    vistas = set()
    meses_en_fechas = set()

    for pos in range(fila_enc + 1, len(crudo)):
        fila = crudo.iloc[pos]
        numero_fila = pos + 1  # número de fila como se ve en Excel
        if all(_vacio(c) for c in fila.tolist()):
            continue

        celda_fecha = fila.iloc[j_fecha]
        fecha = _a_fecha(celda_fecha)
        if fecha is None:
            if _norm(celda_fecha).startswith("total"):
                fila_totales = fila
            elif not _vacio(celda_fecha):
                descartadas.append((numero_fila, f"fecha no válida: «{celda_fecha}»"))
            else:
                descartadas.append((numero_fila, "tiene datos pero no tiene fecha"))
            continue

        meses_en_fechas.add((fecha.year, fecha.month))
        fecha_original = fecha
        d = {"fecha": fecha, "ingresos": {}, "gastos": {}, "movimientos": {}, "observaciones": ""}
        try:
            for nombre, (grupo, destino) in COLUMNAS.items():
                if nombre in posicion:
                    valor = _a_entero(fila.iloc[posicion[nombre]])
                    if valor != 0:
                        d[grupo][destino] = d[grupo].get(destino, 0) + valor
        except ValueError:
            descartadas.append((numero_fila, f"valor que no es un número (día {fecha})"))
            continue

        for nombre in COLUMNAS_OBSERVACIONES & set(posicion):
            texto = fila.iloc[posicion[nombre]]
            if not _vacio(texto):
                d["observaciones"] = str(texto).strip()

        # Usar el mes elegido en lugar del que trae la columna Fecha
        if mes_forzado:
            anio_f, mes_f = mes_forzado
            if fecha_original.day > calendar.monthrange(anio_f, mes_f)[1]:
                if d["ingresos"] or d["gastos"] or d["movimientos"]:
                    descartadas.append((
                        numero_fila,
                        f"tiene datos del día {fecha_original.day}, pero {mes_f:02d}/{anio_f} no tiene ese día",
                    ))
                continue
            fecha = date(anio_f, mes_f, fecha_original.day)
            d["fecha"] = fecha

        if fecha in vistas:
            descartadas.append((numero_fila, f"fecha repetida en el archivo: {fecha}"))
            continue
        vistas.add(fecha)

        # Comprobar contra las columnas calculadas del Excel (si existen)
        calc = totales_dia(d)
        for nombre, etiqueta in COLUMNAS_TOTALES.items():
            if nombre in posicion and etiqueta in ("Total Ingresos", "Total Gastos", "Total Disp"):
                try:
                    en_excel = _a_entero(fila.iloc[posicion[nombre]])
                except ValueError:
                    continue
                if en_excel != calc[etiqueta]:
                    avisos.append(
                        f"{fecha:%d/%m/%Y}: {etiqueta} en el Excel es {en_excel:,}, "
                        f"calculado {calc[etiqueta]:,}".replace(",", ".")
                    )

        if not (d["ingresos"] or d["gastos"] or d["movimientos"]):
            sin_movimiento += 1
            continue
        dias.append(d)

    # Comparar el total del mes contra la fila "Total" del Excel
    comparacion = []
    if fila_totales is not None and dias is not None:
        suma = {k: 0 for k in ("Total Ingresos", "Total Gastos", "Ganancia Est", "Total Disp", "Diferencia")}
        for d in dias:
            for k, v in totales_dia(d).items():
                suma[k] += v
        for nombre, etiqueta in COLUMNAS_TOTALES.items():
            if nombre in posicion:
                try:
                    en_excel = _a_entero(fila_totales.iloc[posicion[nombre]])
                except ValueError:
                    continue
                if not _vacio(fila_totales.iloc[posicion[nombre]]):
                    comparacion.append((etiqueta, suma[etiqueta], en_excel))

    return {
        "dias": dias,
        "sin_movimiento": sin_movimiento,
        "descartadas": descartadas,
        "avisos": avisos,
        "comparacion": comparacion,
        "meses_en_fechas": meses_en_fechas,
    }


# ---------------------------------------------------------------------------
# Comparar con la base de datos e importar
# ---------------------------------------------------------------------------
def clasificar(dias):
    """Marca cada día como 'nuevo', 'igual' (ya está idéntico) o 'distinto'."""
    for d in dias:
        actual = db.cargar_dia(d["fecha"])
        if actual is None:
            d["estado"] = "nuevo"
        elif all(actual[g] == d[g] for g in ("ingresos", "gastos", "movimientos")):
            d["estado"] = "igual"
        else:
            d["estado"] = "distinto"
    return dias


def importar(dias, reemplazar_distintos=False):
    """Guarda los días nuevos (y los diferentes, si se pide). Devuelve (nuevos, reemplazados, omitidos)."""
    a_guardar = [
        d for d in dias
        if d["estado"] == "nuevo" or (d["estado"] == "distinto" and reemplazar_distintos)
    ]
    db.guardar_varios_dias(a_guardar)
    nuevos = sum(d["estado"] == "nuevo" for d in a_guardar)
    reemplazados = sum(d["estado"] == "distinto" for d in a_guardar)
    return nuevos, reemplazados, len(dias) - len(a_guardar)
