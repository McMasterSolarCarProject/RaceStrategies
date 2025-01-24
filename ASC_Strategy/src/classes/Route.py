from __future__ import annotations
from classes import Checkpoint


class Route:
    def __init__(self, name: str, checkpoints: list[Checkpoint]):
        self.name = name
        self.checkpoints = checkpoints

    def __str__(self):
        return f"{self.name}: {self.checkpoints}"

    def __repr__(self):
        return f"{self.name}: {self.checkpoints}"