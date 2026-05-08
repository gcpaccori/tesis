"""02 Descargar Repos - Clona los repositorios definidos en el job."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageClone(Component):
    display_name = "02 Descargar Repos"
    description = "Clona los repos definidos para la corrida."
    icon = "GitBranch"
    name = "ElectroSurStageClone"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/clone", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
