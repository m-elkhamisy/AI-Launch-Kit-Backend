"""Shared Pydantic configuration for canonical domain models."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DomainModel(BaseModel):
    """Strict model with Python attributes and TypeScript-compatible aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )


class PythonSourceModel(BaseModel):
    """Strict model for shapes whose source already uses snake_case fields."""

    model_config = ConfigDict(extra="forbid")
