from typing import Annotated

from fastapi import Query


class PaginationParams:
    """Параметры пагинации для API endpoints."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100, description="Количество элементов")] = 50,
        offset: Annotated[int, Query(ge=0, description="Смещение")] = 0,
    ):
        self.limit = limit
        self.offset = offset
