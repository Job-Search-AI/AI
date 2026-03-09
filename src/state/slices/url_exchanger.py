from typing import Any, TypedDict

from ..base import StrictBaseModel


class EntitySlots(TypedDict, total=False):
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None


class NormalizedEntitySlots(TypedDict):
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None


class PredictCrfBertResultState(TypedDict):
    entities: EntitySlots
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None


class NormalizationResult(TypedDict):
    status: str
    message: str | None
    missing_fields: list[str] | None
    normalized_entities: NormalizedEntitySlots


class NormalizeAndValidateEntitiesResultState(NormalizationResult):
    pass


class PredictCrfBertState(StrictBaseModel):
    user_input: str
    bert_model: Any
    crf: Any
    tokenizer: Any
    device: str


class NormalizeEntityInputState(TypedDict, total=False):
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None


class NormalizeEntityOutputState(TypedDict):
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None


class NormalizeAndValidateEntitiesState(TypedDict, total=False):
    entities: NormalizeEntityInputState
    지역: str | None
    직무: str | None
    경력: str | None
    학력: str | None
