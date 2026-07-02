from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptLayer:
    name: str
    content: str


def compose_layers(layers: list[PromptLayer]) -> str:
    return "\n\n".join(layer.content.strip() for layer in layers if layer.content.strip()).strip()

