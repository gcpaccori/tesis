"""03 Inventario C#/Front/Gateway - Detecta la estructura del repositorio."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageInspect(Component):
    display_name = "03 Inventario C#/Front/Gateway"
    description = "Detecta soluciones, csproj, package.json, gateway, controladores, endpoints y NuGets."
    icon = "Search"
    name = "ElectroSurStageInspect"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/inspect", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
