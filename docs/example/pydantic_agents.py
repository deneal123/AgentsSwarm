from datetime import datetime
from pydantic import BaseModel, Field, StrictStr
from typing import Optional, List, Dict, Any


class FAQSearchResult(BaseModel):
    question: str = Field(
        ...,
        description="Вопрос из базы данных FAQ"
    )
    answer: str = Field(
        ...,
        description="Ответ из базы данных FAQ"
    )
    confidence: float = Field(
        ...,
        description="Уверенность в ответе"
    )


class UserContext(BaseModel):
    user_id: str = Field(
        ...,
        description="Идентификатор пользователя"
    )
    request_time: datetime = Field(
        ...,
        description="Время запроса"
    )
    previous_questions: Optional[List[Dict]] = Field(
        None,
        description="Список предыдущих запросов пользователя"
    )
    session: Optional[Any] = Field(
        None,
        description="Опциональный объект сессии (например RedisSession или PseudoSession)"
    )
    # Идентификатор разговорной сессии (отличается от auth/session в RedisSessionStore)
    session_id: Optional[str] = Field(
        None,
        description="Идентификатор разговорной сессии, используемый для хранения истории"
    )
    # Информация о хранилище сессии — позволяет быстро понять, где лежит история
    session_store: Optional[Dict[str, Any]] = Field(
        None,
        description="Метаданные о backend'е сессии (например backend type, настройки)"
    )


class RoutingDecision(BaseModel):
    category: str = Field(...,
        description="Выбранная категория запроса"
    )


class FAQlookup(BaseModel):
    query: str = Field(
        ...,
        description="Запрос пользователя"
    )


class FetchContext(BaseModel):
    pass


class MealEntry(BaseModel):
    date: str = Field(..., description="Дата в формате YYYY-MM-DD")

    class MealItem(BaseModel):
        name: StrictStr = Field(..., description="Название блюда")
        calories: int = Field(..., description="Калорийность в ккал")
        ingredients: list[StrictStr] = Field(..., description="Список ингредиентов")

    meals: list[MealItem] = Field(..., description="Список приёмов пищи с полями name, calories, ingredients")


class MealCalendarOutput(BaseModel):
    calendar: list[MealEntry] = Field(..., description="План питания — список дней и приёмов пищи")