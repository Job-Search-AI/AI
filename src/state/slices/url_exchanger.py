from typing import Any, Literal, TypedDict

from pydantic import Field

from ..base import StrictBaseModel


class Ask(StrictBaseModel):
    user_input: str


class Ner(StrictBaseModel):
    loc: str = Field(alias="지역")
    job: str = Field(alias="직무")
    exp: str = Field(alias="경력")
    edu: str = Field(alias="학력")


class Norm(StrictBaseModel):
    loc: str | None = Field(default=None, alias="지역")
    job: str | None = Field(default=None, alias="직무")
    exp: str | None = Field(default=None, alias="경력")
    edu: str | None = Field(default=None, alias="학력")


class Reply(StrictBaseModel):
    response: str


class Result(StrictBaseModel):
    user_input: str
    query: str
    status: Literal["complete", "incomplete"]
    message: str | None = None
    entities: Ner | None = None
    loc: str | None = Field(default=None, alias="지역")
    job: str | None = Field(default=None, alias="직무")
    exp: str | None = Field(default=None, alias="경력")
    edu: str | None = Field(default=None, alias="학력")
    missing_fields: list[str] | None = None
    normalized_entities: Norm | None = None
    url: str | None = None
    crawled_count: int | None = None
    job_info_list: list[str] | None = None
    retrieved_job_info_list: list[str] | None = None
    retrieved_scores: list[float] | None = None
    user_response: str | None = None


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
