"""
CRF-BERT helper를 기존 호출 방식과 함께 제공한다.

Source of truth:
- predict node: src.node
- utility functions: src.tools.slices.bert_crf
"""

from src.node import predict_crf_bert as predict_crf_bert_node
from src.tools.slices.bert_crf import (
    build_tag_map,
    get_bert_model_tokenizer,
    train_crf_bert,
)


def predict_crf_bert(user_input, bert_model, crf, tokenizer, device):
    """
    Legacy entity-dict API wrapper.
    """
    # node 함수는 state dict 입력을 받으므로, 기존 함수 시그니처를 유지하면서 형식을 변환한다.
    result = predict_crf_bert_node(
        {
            "user_input": user_input,
            "bert_model": bert_model,
            "crf": crf,
            "tokenizer": tokenizer,
            "device": device,
        }
    )
    # 외부 API 호환을 위해 기존과 동일하게 entities 딕셔너리만 반환한다.
    return result["entities"]


__all__ = [
    "build_tag_map",
    "get_bert_model_tokenizer",
    "train_crf_bert",
    "predict_crf_bert_node",
    "predict_crf_bert",
]
