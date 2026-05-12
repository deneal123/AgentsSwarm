from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FAQSearchResult(BaseModel):
    question: str = Field(..., description="Вопрос из базы данных FAQ")
    answer: str = Field(..., description="Ответ из базы данных FAQ")
    confidence: float = Field(..., description="Уверенность в ответе")


class UserContext(BaseModel):
    user_id: str = Field(..., description="Идентификатор пользователя")
    request_time: datetime = Field(..., description="Время запроса")
    thread_id: str | None = Field(None, description="Идентификатор треда/разговора")
    previous_questions: list[dict] | None = Field(
        None, description="Список предыдущих запросов пользователя"
    )
    session: Any | None = Field(
        None, description="Объект сессии (RedisSession, PseudoSession и т.д.)"
    )
    session_id: str | None = Field(
        None, description="Идентификатор разговорной сессии для хранения истории"
    )
    session_store: dict[str, Any] | None = Field(None, description="Метаданные о backend'е сессии")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class RoutingDecision(BaseModel):
    category: str = Field(..., description="Выбранная категория запроса")


class FAQlookup(BaseModel):
    query: str = Field(..., description="Запрос пользователя")


class FetchContext(BaseModel):
    pass
