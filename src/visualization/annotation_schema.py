from pydantic import BaseModel
from typing import List


class Structure(BaseModel):
    name: str


class AnnotationOutput(BaseModel):
    structures: List[Structure]
