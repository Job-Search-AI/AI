def keep_loading_job_model(bert_model_name="klue/bert-base", device=None):
    """
    모델과 tokenizer, CRF를 한 번만 초기화하고 _MODEL_CACHE에 저장
    """
    global _MODEL_CACHE
    if _MODEL_CACHE:
        # 이미 로드된 경우 그대로 반환
        return _MODEL_CACHE

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    # 라벨 맵 생성
    label_list = ['O','B-JOB','I-JOB','B-CAR','I-CAR','B-EDU','I-EDU','B-LOC','I-LOC']
    label2id, id2label = build_tag_map(label_list)

    # 모델과 tokenizer 로드
    model, tokenizer = get_bert_model_tokenizer(device, model_name, label2id, id2label)

    # CRF 초기화
    crf = CRF(len(label2id), batch_first=True).to(device)

    # 캐시에 저장
    _MODEL_CACHE = {
        "bert_model": model,
        "tokenizer": tokenizer,
        "crf": crf,
        "device": device,
    }

    print(f"[INFO] 모델, tokenizer, CRF가 {device}에 로드됨.")
    return _MODEL_CACHE