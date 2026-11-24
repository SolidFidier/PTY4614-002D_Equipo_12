"""Copia los resultados de las pruebas automáticas al Plan de pruebas.

Uso:  python actualizar_plan.py Plan_de_pruebas.xlsx
Lee resultados_pruebas.json (lo genera: python manage.py test panel --testrunner=panel.test_runner.PlanRunner)
y llena «Resultado obtenido» y «Estado» en las hojas Pruebas, Seguridad, Rendimiento y Compatibilidad.
Guarda una copia: Plan_de_pruebas_resultados.xlsx
- Las pruebas manuales que ya llenaste a mano en el Excel NO se sobrescriben.
- Si hay pruebas nuevas que aún no tienen fila en el Excel (por ejemplo P81 en adelante), se agregan al final de la hoja
  que corresponde (ID en la columna A y el nombre de la prueba en «Descripción», con el formato de la fila anterior);
  las demás columnas (funcionalidad, precondiciones, datos, resultado esperado) las completas tú.
Necesita openpyxl:  pip install openpyxl
"""
import json
import sys
from pathlib import Path

import re

import openpyxl
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

ESTADOS = {"Aprobado": "Aprobado", "Fallido": "Fallido", "Error": "Fallido", "Manual": "Pendiente (prueba manual)"}
SIN_EJECUTAR = (None, "", "No ejecutado")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def limpio(texto):
    """Quita colores de consola y caracteres de control que Excel no acepta."""
    return ILLEGAL_CHARACTERS_RE.sub("", ANSI.sub("", texto))


plan = Path(sys.argv[1] if len(sys.argv) > 1 else "Plan_de_pruebas.xlsx")
resultados = json.loads((Path(__file__).parent / "resultados_pruebas.json").read_text(encoding="utf-8"))
wb = openpyxl.load_workbook(plan)
def titulo(nombre):
    """test_P81_pantalla_muestra_datos_actuales -> «Pantalla muestra datos actuales»"""
    partes = nombre.split("_", 2)
    return partes[2].replace("_", " ").capitalize() if len(partes) == 3 else nombre


def agregar_filas_nuevas(ws):
    """Agrega después de la última prueba de la hoja las pruebas de resultados_pruebas.json que todavía no tienen fila.
    Devuelve cuántas agregó. (Se usa la última fila CON ID, no max_row: las hojas traen cientos de filas vacías con formato.)"""
    filas = [f for f in range(2, ws.max_row + 1) if ws[f"A{f}"].value]
    if not filas:
        return 0
    ids = [str(ws[f"A{f}"].value) for f in filas]
    prefijo = ids[-1][0]
    nuevas = sorted((p for p in resultados if p[0] == prefijo and p not in ids), key=lambda p: int(p[1:]))
    ultima = filas[-1]
    for pid in nuevas:
        ultima += 1
        for col in range(1, ws.max_column + 1):
            ws.cell(ultima, col)._style = ws.cell(filas[-1], col)._style
        ws[f"A{ultima}"] = pid
        ws[f"C{ultima}"] = titulo(resultados[pid].get("prueba", pid))   # columna «Descripción»; la funcionalidad (Hxx) la completas tú
    return len(nuevas)


n, conservadas, agregadas = 0, 0, 0
for ws in wb.worksheets:
    if ws["G1"].value != "Resultado obtenido":
        continue
    agregadas += agregar_filas_nuevas(ws)
    for fila in range(2, ws.max_row + 1):
        pid = ws[f"A{fila}"].value
        if pid not in resultados:
            continue
        r = resultados[pid]
        if r["estado"] == "Manual" and ws[f"G{fila}"].value not in SIN_EJECUTAR:
            conservadas += 1          # prueba manual ya registrada a mano: se respeta
            continue
        ws[f"G{fila}"] = limpio(r["obtenido"])
        ws[f"H{fila}"] = ESTADOS.get(r["estado"], r["estado"])
        n += 1
destino = plan.with_name(plan.stem + "_resultados.xlsx")
wb.save(destino)
print(f"{n} pruebas actualizadas ({conservadas} manuales ya registradas se conservaron, {agregadas} filas nuevas agregadas) → {destino}")
