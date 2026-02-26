"""
legacy API 코드에서 기존 config 값을 그대로 재사용하기 위한 호환 모듈.
"""

# 루트 config.py를 유지한 채 레거시 import 경로(legacy.api.config)만 제공한다.
from config import EVAL_URL, PROMPT

__all__ = ["EVAL_URL", "PROMPT"]
