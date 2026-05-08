"""Kimi 2.6 Q4 Long Agent component.

This component avoids LangFlow provider dropdown issues by calling the local
OpenAI-compatible proxy directly.
"""

import requests

from langflow.custom import Component
from langflow.io import BoolInput, FloatInput, IntInput, MessageTextInput, MultilineInput, Output, StrInput
from langflow.schema.message import Message


DEFAULT_SYSTEM_PROMPT = """Eres Kimi 2.6 Q4 actuando como cerebro de agente largo para QA empresarial.

Tu trabajo no es contestar como bot suelto: debes planear, dividir trabajo, pedir herramientas al runner,
usar memoria externa cuando haga falta y mantener continuidad durante corridas largas.

Reglas:
- Responde en espanol.
- Si el usuario pide trabajo real, devuelve un plan ejecutable por fases y el siguiente paso concreto.
- No afirmes que ejecutaste herramientas si solo razonaste.
- Para corridas de muchas horas, resume estado, riesgos, checkpoints y proxima accion.
- Usa el concepto de enjambre como especializacion logica: director, analistas, validadores y auditores,
  no como miles de procesos simultaneos sin control.
"""


class KimiQ4LongAgent(Component):
    display_name = "Kimi Q4 Long Agent"
    description = "Chat directo con Kimi 2.6 Q4 local via proxy OpenAI-compatible, preparado para agentes largos."
    icon = "BrainCircuit"
    name = "KimiQ4LongAgent"

    inputs = [
        MultilineInput(
            name="input_value",
            display_name="Mensaje",
            input_types=["Message", "Text"],
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="System Prompt",
            value=DEFAULT_SYSTEM_PROMPT,
            required=False,
            advanced=True,
        ),
        StrInput(
            name="base_url",
            display_name="Base URL",
            value="http://kimi-q4-proxy.local:8031/v1",
            required=True,
            advanced=True,
        ),
        StrInput(
            name="model",
            display_name="Model",
            value="kimi-k2.6-q4",
            required=True,
            advanced=True,
        ),
        FloatInput(
            name="temperature",
            display_name="Temperature",
            value=0.6,
            required=False,
            advanced=True,
        ),
        IntInput(
            name="max_tokens",
            display_name="Max Tokens",
            value=1600,
            required=False,
            advanced=True,
        ),
        IntInput(
            name="timeout_seconds",
            display_name="Timeout Seconds",
            value=900,
            required=False,
            advanced=True,
        ),
        BoolInput(
            name="thinking",
            display_name="Thinking",
            value=False,
            required=False,
            advanced=True,
        ),
        MessageTextInput(
            name="extra_context",
            display_name="Contexto Extra",
            value="",
            required=False,
            advanced=True,
        ),
    ]

    outputs = [Output(display_name="Respuesta", name="message", method="run_agent")]

    def _text(self, value) -> str:
        if hasattr(value, "text"):
            return value.text
        return str(value or "")

    def run_agent(self) -> Message:
        user_text = self._text(self.input_value).strip()
        extra_context = self._text(self.extra_context).strip()

        if not user_text:
            message = Message(text="No llego mensaje para Kimi Q4.")
            self.status = message
            return message

        content = user_text
        if extra_context:
            content = f"Contexto extra:\n{extra_context}\n\nPedido del usuario:\n{user_text}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt or DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": float(self.temperature or 0.6),
            "max_tokens": int(self.max_tokens or 1600),
            "chat_template_kwargs": {"thinking": bool(self.thinking)},
        }

        url = f"{str(self.base_url).rstrip('/')}/chat/completions"
        response = requests.post(url, json=payload, timeout=int(self.timeout_seconds or 900))
        response.raise_for_status()
        data = response.json()
        assistant = data["choices"][0]["message"]
        text = (assistant.get("content") or assistant.get("reasoning_content") or "").strip()
        if not text:
            text = "Kimi Q4 respondio sin contenido visible. Sube max_tokens o desactiva thinking."

        message = Message(text=text)
        self.status = message
        return message
