import json

try:
    from torchcrf import CRF as _CRF
except ModuleNotFoundError:
    _CRF = None


def build_tag_map(all_labels):
    label2id = {}
    id2label = {}
    for idx, label in enumerate(all_labels):
        label2id[label] = idx
        id2label[idx] = label
    return label2id, id2label


def get_bert_model_tokenizer(device, model_name, label2id, id2label):
    from transformers import AutoTokenizer, BertForTokenClassification

    model = BertForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(id2label),
        id2label=id2label,
        label2id=label2id,
    ).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)

    return model, tokenizer


def train_crf_bert(data_path, model_name):
    if _CRF is None:
        raise ModuleNotFoundError("torchcrf is required to train CRF-BERT models.")

    import torch
    from datasets import Dataset
    from torch.optim import AdamW
    from torch.utils.data import DataLoader
    from transformers import DataCollatorForTokenClassification, get_scheduler

    label_list = [
        'O',
        "B-JOB",  # 직무
        "I-JOB",
        "B-CAR",  # 경력
        "I-CAR",
        "B-EDU",  # 학력
        "I-EDU",
        "B-LOC",  # 지역
        "I-LOC",
    ]

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    dataset = Dataset.from_list(data)

    # 5) 토큰화 + 라벨 정렬 (첫 서브워드만 라벨, 나머지는 -100)
    def tokenize_and_extend_labels(batch):
        tokenized_input = tokenizer(batch["input"], truncation=True)
        aligned = []

        for word_labels in batch["labels_ids"]:
            label_ids = [0] + word_labels + [0]
            aligned.append(label_ids)

        tokenized_input["labels"] = aligned
        return tokenized_input

    def label2ids(batch):
        if isinstance(batch["label"][0][0], str):
            return {"labels_ids": [[label2id[t] for t in seq] for seq in batch["label"]]}
        return {"labels_ids": batch["label"]}

    label2id, id2label = build_tag_map(label_list)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model, tokenizer = get_bert_model_tokenizer(device, model_name, label2id, id2label)

    dataset = dataset.map(label2ids, batched=True, remove_columns='label')
    tokenized_dataset = dataset.map(
        tokenize_and_extend_labels,
        batched=True,
        remove_columns=dataset.column_names,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)
    train_dataloader = DataLoader(
        tokenized_dataset,
        shuffle=True,
        batch_size=2,
        collate_fn=data_collator,
    )

    crf = _CRF(len(id2label), batch_first=True).to(device)

    optimizer = AdamW(list(model.parameters()) + list(crf.parameters()), lr=5e-5)

    num_epochs = 30
    num_training_steps = num_epochs * len(train_dataloader)
    scheduler = get_scheduler(
        "linear",
        optimizer=optimizer,
        num_warmup_steps=int(0.1 * num_training_steps),
        num_training_steps=num_training_steps,
    )

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0.0
        for batch in train_dataloader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch)  # out.loss, out.logits
            logits = out.logits

            # 토크나이저/데이터콜레이터는 padding 토큰에 -100을 할당한다. CRF는 -100을 허용하지 않으므로 대체한다.
            labels_for_crf = batch["labels"].clone()  # 원본 라벨 복제
            labels_for_crf[labels_for_crf == -100] = 0  # 패딩(-100)을 'O' 인덱스(여기서는 0)로 대체

            # attention_mask를 bool으로 변환 (torchcrf는 bool mask를 기대)
            mask = batch["attention_mask"].bool()

            # CRF 손실 (음의 로그우도)
            loss = -crf(logits, labels_for_crf, mask=mask, reduction="mean")

            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            total_loss += loss.item()

        print(f"epoch {epoch+1} train_loss={total_loss/len(train_dataloader):.4f}")
