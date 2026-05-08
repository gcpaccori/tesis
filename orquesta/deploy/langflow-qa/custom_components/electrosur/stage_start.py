"""01 Crear Corrida QA - Inicia un job en qa-runner."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageStart(Component):
    display_name = "01 Crear Corrida QA"
    description = "Crea el job y carpeta de trabajo en qa-runner."
    icon = "Workflow"
    name = "ElectroSurStageStart"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/start", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
