from typing import Any, Tuple, Union, Optional, List, Type, Callable, Dict
from pydantic import (BaseModel, Field, StrictStr, condecimal, StrictInt, StrictBool, StrictFloat,
                      FilePath, DirectoryPath, ValidationError, root_validator, ConfigDict)
from fastapi import HTTPException, status
from functools import wraps
from datetime import datetime, timezone
from uuid import uuid4
from logging import getLogger
log = getLogger(__name__)


def validate_with_pydantic(model_cls):
    """
    Декоратор для валидации данных с использованием Pydantic-модели.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = kwargs.get("entry", args[0] if args else None)
                if not data:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="No data provided for validation.")
                if isinstance(data, BaseModel):
                    data = data.model_dump()
                validated_data = model_cls(**data)
                kwargs["entry"] = validated_data
                return func(*args, **kwargs)
            except ValidationError as ve:
                log.warning("Validation failed: %s", ve)
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Invalid data for Pydantic model.") from ve

        return wrapper

    return decorator


def auto_generate_docstring(cls: Type[BaseModel]) -> Type[BaseModel]:
    """
    Декоратор для автоматического добавления docstring в классы Pydantic.
    """

    def generate_docstring(model: Type[BaseModel]) -> str:
        """
        Генерация строки документации из описания полей модели Pydantic.
        Поддерживает Pydantic v1 (model.__fields__) и v2 (model.model_fields).
        """
        docstring = []
        # Поддержка обеих версий Pydantic: предпочитаем model_fields (v2),
        # fallback на __fields__ для совместимости с v1.
        fields = getattr(model, "model_fields", None)
        if fields is None:
            fields = getattr(model, "__fields__", {})

        for field_name, field_info in fields.items():
            field_details = f"Field '{field_name}':\n"
            # field_info может быть разного типа в зависимости от версии Pydantic.
            description = getattr(field_info, "description", None)
            examples = getattr(field_info, "examples", None)

            # Некоторые реализации хранят примеры в attribute 'example' или в extra.
            if description:
                field_details += f"  Description: {description}\n"
            if examples:
                field_details += f"  Examples: {examples}\n"
            docstring.append(field_details)
        return "\n".join(docstring)

    # Добавляем описание к существующему docstring
    cls.__doc__ = (cls.__doc__ or "") + "\n\n" + generate_docstring(cls)
    return cls
    


@auto_generate_docstring
class AgentsQuery(BaseModel):

    query: StrictStr = Field(
        ...,
        alias="query",
        examples=["Какой сегодня день?"],
        description="Запрос к ассистенту."
    )

    user_id: Optional[StrictStr] = Field(
        default_factory=lambda: str(uuid4()),
        alias="user_id",
        examples=['134244'],
        description="ID пользователя"
    )

    request_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="request_time",
        examples=[datetime.now(timezone.utc)],
        description="Время запроса к ассистенту."
    )


@auto_generate_docstring
class AgentsResponse(BaseModel):

    answer: StrictStr = Field(
        ...,
        alias="answer",
        examples=["Сегодня понедельник."],
        description="Ответ ассистента на запрос."
    )

    user_id: StrictStr = Field(
        ...,
        alias="user_id",
        examples=['134244'],
        description="ID пользователя"
    )

    answer_time: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="answer_time",
        examples=[datetime.now(timezone.utc)],
        description="Время ответа ассистента."
    )