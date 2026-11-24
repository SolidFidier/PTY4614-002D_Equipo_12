"""Lanzador de las pruebas del Plan de pruebas.

Uso:  python manage.py test panel --testrunner=panel.test_runner.PlanRunner
      (solo un tipo:  python manage.py test panel.tests.test_seguridad --testrunner=panel.test_runner.PlanRunner)

Archivos de pruebas (carpeta panel/tests/):
  test_funciones.py       → hoja «Pruebas»         (P1 a P93)
  test_seguridad.py       → hoja «Seguridad»       (S1 a S18)
  test_rendimiento.py     → hoja «Rendimiento»     (R1 a R11)
  test_compatibilidad.py  → hoja «Compatibilidad»  (C1 a C6; C7 en adelante son manuales)

- Las tablas del proyecto son `managed=False`; aquí se marcan como administradas SOLO durante las pruebas para que
  Django las cree en la base de datos temporal de pruebas. Tu base real no se toca.
- Al terminar escribe `resultados_pruebas.json` en la carpeta del proyecto con el resultado concreto de cada prueba.
  Si ya existía, conserva los resultados de las pruebas que no se ejecutaron esta vez.
"""
import json
import re
import unittest
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test.runner import DiscoverRunner

ORDEN = {"P": 0, "S": 1, "R": 2, "C": 3}


def _id(test):
    m = re.search(r"test_([PSRC])(\d+)_", getattr(test, "_testMethodName", ""))
    return f"{m.group(1)}{int(m.group(2))}" if m else None


def _clave(pid):
    return ORDEN[pid[0]], int(pid[1:])


class PlanResult(unittest.TextTestResult):
    registros = {}

    def _guardar(self, test, estado, detalle):
        pid = _id(test)
        if not pid:
            return
        notas = getattr(test, "notas", [])
        self.registros[pid] = {"estado": estado, "obtenido": " ".join([detalle, *notas]).strip(),
                               "prueba": test._testMethodName}

    def addSuccess(self, test):
        super().addSuccess(test)
        self._guardar(test, "Aprobado", getattr(test, "obtenido", "") or "Se obtuvo el resultado esperado.")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._guardar(test, "Fallido", f"Falló: {str(err[1]).splitlines()[0]}")

    def addError(self, test, err):
        super().addError(test, err)
        self._guardar(test, "Error", f"Error al ejecutar: {err[0].__name__}: {err[1]}")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._guardar(test, "Manual", reason)


class PlanRunner(DiscoverRunner):
    def get_resultclass(self):
        return PlanResult

    def setup_databases(self, **kwargs):
        for m in apps.get_app_config("panel").get_models():
            m._meta.managed = True
        return super().setup_databases(**kwargs)

    def suite_result(self, suite, result, **kwargs):
        destino = Path(settings.BASE_DIR) / "resultados_pruebas.json"
        previos = {}
        if destino.exists():
            try:
                previos = json.loads(destino.read_text(encoding="utf-8"))
            except ValueError:
                previos = {}
        previos.update(PlanResult.registros)
        regs = dict(sorted(previos.items(), key=lambda kv: _clave(kv[0])))
        destino.write_text(json.dumps(regs, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== RESUMEN DEL PLAN DE PRUEBAS (esta ejecución) ===")
        cuenta = {}
        for pid in sorted(PlanResult.registros, key=_clave):
            r = PlanResult.registros[pid]
            cuenta[r["estado"]] = cuenta.get(r["estado"], 0) + 1
            print(f"{pid:>4}  {r['estado']:<9} {r['obtenido'][:110]}")
        print("Totales:", cuenta)
        print(f"Resultados guardados en: {destino}")
        return super().suite_result(suite, result, **kwargs)
