"""
Backward-compatible shim for CRF-BERT helpers.

Source of truth:
- predict node: src.node
- utility functions: src.tools.slices.url_exchanger
"""

from src.node import predict_crf_bert as predict_crf_bert_node
from src.tools.slices.url_exchanger import (
    build_tag_map,
    get_bert_model_tokenizer,
    train_crf_bert,
)


def predict_crf_bert(user_input, bert_model, crf, tokenizer, device):
    """
    Legacy entity-dict API wrapper.
    """
    result = predict_crf_bert_node(
        {
            "user_input": user_input,
            "bert_model": bert_model,
            "crf": crf,
            "tokenizer": tokenizer,
            "device": device,
        }
    )
    return result["entities"]


__all__ = [
    "build_tag_map",
    "get_bert_model_tokenizer",
    "train_crf_bert",
    "predict_crf_bert_node",
    "predict_crf_bert",
]
