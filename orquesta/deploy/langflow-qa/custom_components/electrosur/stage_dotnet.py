"""04 Restore Build Test .NET - Compila y prueba proyectos .NET."""

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema.data import Data

from .common import as_dict, post_stage


class StageDotnet(Component):
    display_name = "04 Restore Build Test .NET"
    description = "Ejecuta dotnet restore/build/test cuando el repo es .NET."
    icon = "Terminal"
    name = "ElectroSurStageDotnet"
    inputs = [DataInput(name="input_data", display_name="Entrada JSON", required=True)]
    outputs = [Output(display_name="Salida JSON", name="stage_data", method="run_stage")]

    def run_stage(self) -> Data:
        result = post_stage(self.display_name, "/pipeline/dotnet", as_dict(self.input_data))
        self.status = result.data.get("message") or result.data.get("status") or str(result.data)[:200]
        return result
