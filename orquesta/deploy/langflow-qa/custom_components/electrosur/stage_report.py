"""07 Reporte Final - Obtiene el resumen y rutas de los reportes generados."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageReport(Component):
    display_name = "07 Reporte Final"
    description = "Obtiene el resumen final y rutas de reportes."
    icon = "FileCheck"
    name = "ElectroSurStageReport"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/report", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
