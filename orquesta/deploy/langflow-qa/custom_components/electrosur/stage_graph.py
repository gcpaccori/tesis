"""06 Escribir Memgraph - Escribe relaciones en el grafo de conocimiento."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageGraph(Component):
    display_name = "06 Escribir Memgraph"
    description = "Destila la corrida y escribe relaciones en Memgraph."
    icon = "Network"
    name = "ElectroSurStageGraph"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/graph", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
