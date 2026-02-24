import os

import torch

from src.state import (
    GraphState,
    NormalizeAndValidateEntitiesResultState,
    NormalizeAndValidateEntitiesState,
    NormalizeEntityInputState,
    PredictCrfBertResultState,
)

from .tools import check_missing_entities, generate_missing_message, normalize_entities


def predict_crf_bert(state: GraphState) -> PredictCrfBertResultState:
    """
    사용자 입력을 "직무", "경력", "학력", "지역" 4가지 항목 NER 인식

    state: 사용자 입력/모델 객체가 포함된 상태

    return
    1. entities + 개별 슬롯 키(직무/경력/학력/지역)를 포함한 결과
    """
    sentence = state.get("user_input")
    model = state.get("bert_model")
    crf = state.get("crf")
    tokenizer = state.get("tokenizer")
    device = state.get("device")

    if not isinstance(sentence, str):
        raise ValueError("state['user_input'] must be a string")
    if model is None or crf is None or tokenizer is None or device is None:
        raise ValueError("state must include bert_model, crf, tokenizer, device")

    label_to_slot = {
        "O": "O",
        "B-JOB": "직무",
        "I-JOB": "직무",
        "B-CAR": "경력",
        "I-CAR": "경력",
        "B-EDU": "학력",
        "I-EDU": "학력",
        "B-LOC": "지역",
        "I-LOC": "지역",
    }

    tokenized_input = tokenizer(sentence, return_tensors="pt", truncation=True)
    input_data = {k: v.to(device) for k, v in tokenized_input.items()}

    with torch.no_grad():
        logits = model(**input_data).logits
        predictions = crf.decode(logits)[0]
        predicted_token_class = [model.config.id2label[t] for t in predictions]

    decode = tokenizer.convert_ids_to_tokens(tokenized_input["input_ids"][0])

    entity: NormalizeEntityInputState = {
        "직무": "",
        "경력": "",
        "학력": "",
        "지역": "",
    }

    for word, pred in zip(decode, predicted_token_class):
        cleaned_word = word.replace("#", "")
        slot = label_to_slot.get(pred)
        if slot and slot != "O":
            current = entity.get(slot) or ""
            entity[slot] = current + cleaned_word

    return {
        "entities": entity,
        "지역": entity.get("지역"),
        "직무": entity.get("직무"),
        "경력": entity.get("경력"),
        "학력": entity.get("학력"),
    }


def normalize_and_validate_entities(
    state: GraphState,
) -> NormalizeAndValidateEntitiesResultState:
    """
    LangGraph 노드 형태의 엔티티 정규화/검증 함수.
    """
    typed_state: NormalizeAndValidateEntitiesState = {
        "entities": state.get("entities"),
        "지역": state.get("지역"),
        "직무": state.get("직무"),
        "경력": state.get("경력"),
        "학력": state.get("학력"),
    }

    entities = typed_state.get("entities")
    if isinstance(entities, dict):
        entity_dict: NormalizeEntityInputState = {
            "지역": entities.get("지역"),
            "직무": entities.get("직무"),
            "경력": entities.get("경력"),
            "학력": entities.get("학력"),
        }
    else:
        entity_dict = {
            "지역": typed_state.get("지역"),
            "직무": typed_state.get("직무"),
            "경력": typed_state.get("경력"),
            "학력": typed_state.get("학력"),
        }

    base_dir = os.getenv("JOB_SEARCH_ROOT")
    synonym_dict_path = os.path.join(base_dir, "data", "url_exchanger", "synonym_dict.json")

    normalized_entities = normalize_entities(entity_dict, synonym_dict_path)
    missing_fields = check_missing_entities(normalized_entities)

    if missing_fields:
        message = generate_missing_message(missing_fields)
        return {
            "status": "incomplete",
            "message": message,
            "missing_fields": missing_fields,
            "normalized_entities": normalized_entities,
        }

    return {
        "status": "complete",
        "message": "모든 정보가 확인되었습니다.",
        "missing_fields": None,
        "normalized_entities": normalized_entities,
    }
