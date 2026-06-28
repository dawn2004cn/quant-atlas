from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar('T')
U = TypeVar('U')

class GenericResponseDTO(BaseModel, Generic[T, U]):
    ok: bool = True
    message: str = ""
    data: Any = None
    error: str | None = None

class BatchOperationResultDTO(BaseModel):
    total: int
    success: int
    failed: int
    details: list[Any] = []
