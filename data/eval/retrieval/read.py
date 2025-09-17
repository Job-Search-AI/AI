data_path = "/content/drive/MyDrive/ai_enginner/job_search/AI/data/eval/retrieval/data.jsonl"

import json

with open(data_path, "r", encoding="utf-8") as f:
    for line in f.readlines()[10:15]:
        json_obj = json.loads(line.strip())
        print("=" * 110)
        print(f"문서번호: {json_obj['id']}")
        print(f"문서내용: {json_obj['data']}")

# 지역, 경력, 학력, 직무