from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """
    모델 정의에 포함되지 않은 추가 필드가 입력 데이터에 존재할 경우
    ValidationError를 발생시켜 엄격한 데이터 검증을 수행하는 설정
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )
