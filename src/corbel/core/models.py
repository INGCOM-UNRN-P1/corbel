"""Modelos de datos para la generación de documentación en CORBEL."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class FunctionParam(BaseModel):
    name: str
    description: str


class DocumentedFunction(BaseModel):
    name: str
    return_type: str
    signature: str
    brief: str
    description: str = ""
    params: List[FunctionParam] = Field(default_factory=list)
    returns: str = ""
    preconditions: List[str] = Field(default_factory=list)
    postconditions: List[str] = Field(default_factory=list)


class ModuleDoc(BaseModel):
    header_name: str
    brief: str = ""
    description: str = ""
    functions: List[DocumentedFunction] = Field(default_factory=list)
