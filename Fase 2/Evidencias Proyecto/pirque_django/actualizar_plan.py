"""Copia los resultados de las pruebas automáticas al Plan de pruebas.

Uso:  python actualizar_plan.py Plan_de_pruebas.xlsx
Lee resultados_pruebas.json (lo genera: python manage.py test panel --testrunner=panel.test_runner.PlanRunner)
y llena «Resultado obtenido» y «Estado» en las hojas Funcionalidades, Seguridad, Rendimiento y Compatibilidad.
Además actualiza:
- «Registro de fallos»: agrega cada prueba que falló y todavía no estaba registrada (ID, fallo y «Razón» para que la completes),
  y en la columna «Estado actual» indica si la prueba ya fue «Corregida» o «Sigue fallando».
- «Resumen»: correctas, manuales, fallaron, corregidas y total de automatizadas, y las listas de pruebas que fallaron,
  que quedaron pendientes y que son manuales. Los contadores que ya son fórmulas (pendientes, cantidad por hoja) se respetan,
  igual que el texto de «¿Qué pruebas requirieron intervención manual?», que se escribe a mano.
Guarda una copia: <nombre del archivo>_resultados.xlsx
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
archivo_resultados = Path(__file__).parent / "resultados_pruebas.json"
if not archivo_resultados.exists():
    sys.exit("No existe resultados_pruebas.json: primero ejecuta las pruebas, que son las que crean ese archivo:\n"
             "    python manage.py test panel --testrunner=panel.test_runner.PlanRunner\n"
             "y después vuelve a ejecutar:  python actualizar_plan.py " + str(plan))
if not plan.exists():
    sys.exit(f"No se encontró el Excel «{plan}». Copia el plan de pruebas en la carpeta del proyecto o escribe su ruta completa.")
resultados = json.loads(archivo_resultados.read_text(encoding="utf-8"))
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


# ---------------------------------------------------------------- Registro de fallos y Resumen
PENDIENTES = ("Pendiente", "Pendiente (prueba manual)", "No ejecutado")
HOJAS = [ws for ws in wb.worksheets if ws["G1"].value == "Resultado obtenido"]


def orden(pid):
    letra = {"P": 0, "S": 1, "R": 2, "C": 3}.get(pid[:1], 9)
    return letra, int(pid[1:]) if pid[1:].isdigit() else 0


def lista(ids):
    """['R9', 'C3', 'S21'] -> «R9, C3 y S21»"""
    ids = list(ids)
    if not ids:
        return "ninguna"
    return ids[0] if len(ids) == 1 else ", ".join(ids[:-1]) + " y " + ids[-1]


def estado_en_excel():
    """{ID: estado de la columna H} de todas las hojas de pruebas."""
    estados = {}
    for ws in HOJAS:
        for fila in range(2, ws.max_row + 1):
            pid = ws[f"A{fila}"].value
            if pid:
                estados[str(pid).strip()] = str(ws[f"H{fila}"].value or "").strip()
    return estados


fallos_nuevos, corregidas_ahora = 0, 0
if "Registro de fallos" in wb.sheetnames:
    reg = wb["Registro de fallos"]
    if not reg["D1"].value:                         # columna nueva «Estado actual» con el formato del encabezado
        reg["D1"]._style = reg["C1"]._style
        reg["D1"] = "Estado actual"
        reg.column_dimensions["D"].width = 16
    filas_reg = {str(reg[f"A{f}"].value).strip(): f for f in range(2, reg.max_row + 1) if reg[f"A{f}"].value}
    ultima = max(filas_reg.values(), default=1)
    for pid in sorted((p for p, r in resultados.items() if r["estado"] in ("Fallido", "Error")), key=orden):
        if pid in filas_reg:
            continue
        ultima += 1
        modelo = max(ultima - 1, 2) if ultima > 2 else None
        for col in range(1, 5):
            if modelo and reg.cell(modelo, col).has_style:
                reg.cell(ultima, col)._style = reg.cell(modelo, col)._style
        reg[f"A{ultima}"] = pid
        reg[f"B{ultima}"] = limpio(resultados[pid]["obtenido"])
        reg[f"C{ultima}"] = "Pendiente de analizar: escribe aquí la causa y cómo se corrigió."
        filas_reg[pid] = ultima
        fallos_nuevos += 1
    estados = estado_en_excel()
    for pid, f in filas_reg.items():
        actual = resultados.get(pid, {}).get("estado")
        if actual in ("Fallido", "Error"):
            texto = "Sigue fallando"
        elif actual == "Aprobado" or estados.get(pid) == "Aprobado":
            texto = "Corregida"
            corregidas_ahora += 1
        else:
            texto = estados.get(pid) or "Sin ejecutar"
        reg[f"D{f}"] = texto
    registradas = sorted(filas_reg, key=orden)
else:
    registradas = []

if "Resumen" in wb.sheetnames:
    res = wb["Resumen"]
    estados = estado_en_excel()
    automaticas = {p: r for p, r in resultados.items() if r["estado"] != "Manual"}
    correctas = sum(1 for r in automaticas.values() if r["estado"] == "Aprobado")
    # Manuales: las que la prueba automática marca como manuales y las que existen solo en el Excel (sin prueba automática)
    manuales = sorted({p for p, r in resultados.items() if r["estado"] == "Manual"} | {p for p in estados if p not in resultados}, key=orden)
    fallando = sorted((p for p, r in resultados.items() if r["estado"] in ("Fallido", "Error")), key=orden)
    pendientes = sorted((p for p, e in estados.items() if e in PENDIENTES), key=orden)

    def poner(celda, valor):
        if not (isinstance(res[celda].value, str) and res[celda].value.startswith("=")):   # nunca se pisa una fórmula
            res[celda] = valor

    poner("B14", correctas)
    poner("C14", len(manuales))
    poner("D14", len(registradas))
    poner("E14", corregidas_ahora)
    poner("B15", len(automaticas))
    texto = f"Fallaron las pruebas: {lista(registradas)}"
    if registradas:
        texto += (". Hoy siguen fallando: " + lista(fallando)) if fallando else ". Todas ya fueron corregidas"
    poner("A20", texto)
    poner("A26", lista(pendientes))
    poner("A29", lista(manuales))

destino = plan.with_name(plan.stem + "_resultados.xlsx")
wb.save(destino)
print(f"{n} pruebas actualizadas ({conservadas} manuales ya registradas se conservaron, {agregadas} filas nuevas agregadas) → {destino}")
print(f"Registro de fallos: {fallos_nuevos} fallo(s) nuevo(s) agregado(s), {corregidas_ahora} prueba(s) marcadas como corregidas. "
      "Resumen actualizado.")
