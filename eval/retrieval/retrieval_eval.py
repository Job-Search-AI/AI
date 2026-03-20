import json
import math
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from src.tools.retrieval.bm25_retriever import BM25Retriever
from src.tools.retrieval.query_processor import QueryProcessor


def evaluate_retrieval_methods(
    data_path: str = "data/retrieval/data.jsonl",
    ground_truth_path: str = "data/retrieval/ground_truth.json",
    embedding_model: str = "text-embedding-3-small",
    top_k: int = 5,
    use_query_expansion: bool = True,
    output_json_path: str | None = "eval/retrieval/results/retrieval_eval.json",
    report_md_path: str | None = "eval/retrieval/results/retrieval_eval_report.md",
) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        if api_key.startswith("export OPENAI_API_KEY="):
            api_key = api_key.split("=", 1)[1].strip()
        if "\n" in api_key:
            api_key = api_key.splitlines()[0].strip()
        if api_key.startswith("export OPENAI_API_KEY="):
            api_key = api_key.split("=", 1)[1].strip()
        api_key = api_key.strip("'").strip('"').strip()
        os.environ["OPENAI_API_KEY"] = api_key

    data_file = Path(data_path)
    if not data_file.is_absolute():
        data_file = root / data_file

    gt_file = Path(ground_truth_path)
    if not gt_file.is_absolute():
        gt_file = root / gt_file

    docs = []
    with data_file.open("r", encoding="utf-8") as file:
        for line in file:
            value = line.strip()
            if not value:
                continue
            docs.append(json.loads(value))

    doc_ids = []
    doc_texts = []
    for doc in docs:
        doc_ids.append(int(doc["id"]))
        doc_texts.append(str(doc["data"]))

    with gt_file.open("r", encoding="utf-8") as file:
        gt_list = json.load(file)

    ndcg_key = f"ndcg_at_{top_k}"
    recall_key = f"recall_at_{top_k}"
    mrr_key = f"mrr_at_{top_k}"

    methods = ["bm25", "openai_embedding", "hybrid"]
    macro_sum: dict[str, dict[str, float]] = {}
    for method in methods:
        macro_sum[method] = {}
        macro_sum[method][ndcg_key] = 0.0
        macro_sum[method][recall_key] = 0.0
        macro_sum[method][mrr_key] = 0.0

    per_query: dict[str, object] = {}
    raw_rankings: dict[str, object] = {}

    bm25 = BM25Retriever()
    bm25.build_index(doc_texts)
    query_proc = QueryProcessor()

    embedder = OpenAIEmbeddings(model=embedding_model)
    doc_vecs = np.array(embedder.embed_documents(doc_texts), dtype=np.float32)

    query_count = 0
    for item in gt_list:
        query = str(item.get("query", "")).strip()
        if not query:
            continue

        search_query = query
        if use_query_expansion:
            expanded_query = query_proc.get_expanded_query_string(query)
            if expanded_query.strip():
                search_query = expanded_query

        relevant_doc_ids = set()
        raw_indices = item.get("relevant_doc_indices", [])
        for raw_idx in raw_indices:
            if not isinstance(raw_idx, int):
                continue
            idx = raw_idx - 1
            if idx < 0:
                continue
            if idx >= len(doc_ids):
                continue
            relevant_doc_ids.add(doc_ids[idx])

        bm25_pairs: list[tuple[int, float]] = []
        query_tokens = bm25._tokenize(search_query)
        if query_tokens:
            doc_idx = 0
            while doc_idx < bm25.num_documents:
                score = bm25._calculate_bm25_score(query_tokens, doc_idx)
                if score > 0:
                    bm25_pairs.append((doc_idx, float(score)))
                doc_idx += 1
        bm25_pairs.sort(key=lambda pair: pair[1], reverse=True)

        bm25_ids = []
        idx = 0
        while idx < len(bm25_pairs) and idx < top_k:
            bm25_ids.append(doc_ids[bm25_pairs[idx][0]])
            idx += 1

        query_vec = np.array(embedder.embed_query(search_query), dtype=np.float32)
        query_norm = float(np.linalg.norm(query_vec))

        emb_pairs: list[tuple[int, float]] = []
        doc_idx = 0
        while doc_idx < len(doc_ids):
            doc_vec = doc_vecs[doc_idx]
            doc_norm = float(np.linalg.norm(doc_vec))
            score = 0.0
            denom = query_norm * doc_norm
            if denom > 0:
                score = float(np.dot(query_vec, doc_vec) / denom)
            emb_pairs.append((doc_idx, score))
            doc_idx += 1
        emb_pairs.sort(key=lambda pair: pair[1], reverse=True)

        emb_ids = []
        idx = 0
        while idx < len(emb_pairs) and idx < top_k:
            emb_ids.append(doc_ids[emb_pairs[idx][0]])
            idx += 1

        bm_top = bm25_pairs[: top_k * 2]
        emb_top = emb_pairs[: top_k * 2]

        bm_map: dict[int, float] = {}
        for doc_idx, score in bm_top:
            bm_map[doc_idx] = score

        emb_map: dict[int, float] = {}
        for doc_idx, score in emb_top:
            emb_map[doc_idx] = score

        union_idxs = set()
        for doc_idx, _score in bm_top:
            union_idxs.add(doc_idx)
        for doc_idx, _score in emb_top:
            union_idxs.add(doc_idx)

        hybrid_pairs: list[tuple[int, float]] = []
        if union_idxs:
            union_list = []
            bm_vals = []
            emb_vals = []
            for doc_idx in union_idxs:
                union_list.append(doc_idx)
                bm_vals.append(bm_map.get(doc_idx, 0.0))
                emb_vals.append(emb_map.get(doc_idx, 0.0))

            bm_arr = np.array(bm_vals, dtype=np.float32)
            emb_arr = np.array(emb_vals, dtype=np.float32)

            bm_max = float(np.max(bm_arr))
            bm_min = float(np.min(bm_arr))
            emb_max = float(np.max(emb_arr))
            emb_min = float(np.min(emb_arr))

            if bm_max == bm_min:
                bm_norm = np.ones(len(bm_arr), dtype=np.float32)
            else:
                bm_norm = (bm_arr - bm_min) / (bm_max - bm_min)

            if emb_max == emb_min:
                emb_norm = np.ones(len(emb_arr), dtype=np.float32)
            else:
                emb_norm = (emb_arr - emb_min) / (emb_max - emb_min)

            hybrid_arr = (0.5 * bm_norm) + (0.5 * emb_norm)
            idx = 0
            while idx < len(union_list):
                hybrid_pairs.append((union_list[idx], float(hybrid_arr[idx])))
                idx += 1
            hybrid_pairs.sort(key=lambda pair: pair[1], reverse=True)

        hybrid_ids = []
        idx = 0
        while idx < len(hybrid_pairs) and idx < top_k:
            hybrid_ids.append(doc_ids[hybrid_pairs[idx][0]])
            idx += 1

        def calc(rank_ids: list[int]) -> dict[str, float]:
            hit = 0
            for doc_id in rank_ids:
                if doc_id in relevant_doc_ids:
                    hit += 1

            recall = 0.0
            if len(relevant_doc_ids) > 0:
                recall = hit / len(relevant_doc_ids)

            mrr = 0.0
            rank = 1
            for doc_id in rank_ids:
                if doc_id in relevant_doc_ids:
                    mrr = 1.0 / rank
                    break
                rank += 1

            dcg = 0.0
            rank = 1
            for doc_id in rank_ids:
                if doc_id in relevant_doc_ids:
                    dcg += 1.0 / math.log2(rank + 1)
                rank += 1

            idcg = 0.0
            max_rel = len(relevant_doc_ids)
            if max_rel > top_k:
                max_rel = top_k
            rank = 1
            while rank <= max_rel:
                idcg += 1.0 / math.log2(rank + 1)
                rank += 1

            ndcg = 0.0
            if idcg > 0:
                ndcg = dcg / idcg

            out = {}
            out[ndcg_key] = float(ndcg)
            out[recall_key] = float(recall)
            out[mrr_key] = float(mrr)
            return out

        method_rankings: dict[str, list[int]] = {}
        method_rankings["bm25"] = bm25_ids
        method_rankings["openai_embedding"] = emb_ids
        method_rankings["hybrid"] = hybrid_ids

        query_result: dict[str, object] = {}
        relevant_sorted = sorted(relevant_doc_ids)
        query_result["relevant_doc_ids"] = relevant_sorted

        method = "bm25"
        score = calc(method_rankings[method])
        query_result[method] = score
        macro_sum[method][ndcg_key] += score[ndcg_key]
        macro_sum[method][recall_key] += score[recall_key]
        macro_sum[method][mrr_key] += score[mrr_key]

        method = "openai_embedding"
        score = calc(method_rankings[method])
        query_result[method] = score
        macro_sum[method][ndcg_key] += score[ndcg_key]
        macro_sum[method][recall_key] += score[recall_key]
        macro_sum[method][mrr_key] += score[mrr_key]

        method = "hybrid"
        score = calc(method_rankings[method])
        query_result[method] = score
        macro_sum[method][ndcg_key] += score[ndcg_key]
        macro_sum[method][recall_key] += score[recall_key]
        macro_sum[method][mrr_key] += score[mrr_key]

        per_query[query] = query_result
        raw_rankings[query] = method_rankings
        query_count += 1

    macro_avg: dict[str, object] = {}
    for method in methods:
        macro_avg[method] = {}
        if query_count == 0:
            macro_avg[method][ndcg_key] = 0.0
            macro_avg[method][recall_key] = 0.0
            macro_avg[method][mrr_key] = 0.0
            continue
        macro_avg[method][ndcg_key] = macro_sum[method][ndcg_key] / query_count
        macro_avg[method][recall_key] = macro_sum[method][recall_key] / query_count
        macro_avg[method][mrr_key] = macro_sum[method][mrr_key] / query_count

    result: dict[str, object] = {}
    result["meta"] = {
        "run_at": datetime.now().astimezone().isoformat(),
        "data_path": str(data_file),
        "ground_truth_path": str(gt_file),
        "embedding_model": embedding_model,
        "top_k": top_k,
        "use_query_expansion": use_query_expansion,
        "query_count": query_count,
    }
    result["macro_avg"] = macro_avg
    result["per_query"] = per_query
    result["raw_rankings"] = raw_rankings

    if output_json_path is not None:
        out_json = Path(output_json_path)
        if not out_json.is_absolute():
            out_json = root / out_json
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with out_json.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

    if report_md_path is not None:
        out_md = Path(report_md_path)
        if not out_md.is_absolute():
            out_md = root / out_md
        out_md.parent.mkdir(parents=True, exist_ok=True)
        report = build_markdown_report(result)
        with out_md.open("w", encoding="utf-8") as file:
            file.write(report)

    return result


def build_markdown_report(result: dict[str, object]) -> str:
    def to_text(values: list[object]) -> str:
        text = ""
        idx = 0
        while idx < len(values):
            if idx > 0:
                text += ", "
            text += str(values[idx])
            idx += 1
        return text

    meta = result.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    macro_avg = result.get("macro_avg", {})
    if not isinstance(macro_avg, dict):
        macro_avg = {}

    per_query = result.get("per_query", {})
    if not isinstance(per_query, dict):
        per_query = {}

    raw_rankings = result.get("raw_rankings", {})
    if not isinstance(raw_rankings, dict):
        raw_rankings = {}

    top_k = int(meta.get("top_k", 5))
    ndcg_key = f"ndcg_at_{top_k}"
    recall_key = f"recall_at_{top_k}"
    mrr_key = f"mrr_at_{top_k}"

    methods = ["bm25", "openai_embedding", "hybrid"]
    labels = {
        "bm25": "BM25",
        "openai_embedding": "OpenAI Embedding",
        "hybrid": "Hybrid",
    }

    lines = []
    lines.append("# 검색/랭킹 오프라인 평가 리포트")
    lines.append("")
    lines.append("## 1) 실험 메타정보")
    lines.append("")
    lines.append(f"- 실행 시각: {meta.get('run_at', '')}")
    lines.append(f"- 데이터: `{meta.get('data_path', '')}`")
    lines.append(f"- 정답셋: `{meta.get('ground_truth_path', '')}`")
    lines.append(f"- 임베딩 모델: `{meta.get('embedding_model', '')}`")
    lines.append(f"- top_k: `{top_k}`")
    lines.append(f"- 쿼리 확장: `{meta.get('use_query_expansion', False)}`")
    lines.append(f"- 쿼리 수: `{meta.get('query_count', 0)}`")
    lines.append("")

    lines.append("## 2) 방법별 매크로 평균")
    lines.append("")
    lines.append(f"| 방법 | nDCG@{top_k} | Recall@{top_k} | MRR@{top_k} |")
    lines.append("| --- | ---: | ---: | ---: |")
    for method in methods:
        row = macro_avg.get(method, {})
        if not isinstance(row, dict):
            row = {}
        ndcg = float(row.get(ndcg_key, 0.0))
        recall = float(row.get(recall_key, 0.0))
        mrr = float(row.get(mrr_key, 0.0))
        lines.append(
            f"| {labels[method]} | {ndcg:.4f} | {recall:.4f} | {mrr:.4f} |"
        )
    lines.append("")

    rank_sum: dict[str, float] = {}
    for method in methods:
        rank_sum[method] = 0.0

    metric_keys = [ndcg_key, recall_key, mrr_key]
    for metric_key in metric_keys:
        metric_pairs = []
        for method in methods:
            row = macro_avg.get(method, {})
            if not isinstance(row, dict):
                row = {}
            metric_pairs.append((method, float(row.get(metric_key, 0.0))))
        metric_pairs.sort(key=lambda pair: pair[1], reverse=True)

        rank = 1
        for method, _score in metric_pairs:
            rank_sum[method] += rank
            rank += 1

    avg_rank: dict[str, float] = {}
    for method in methods:
        avg_rank[method] = rank_sum[method] / len(metric_keys)

    rank_pairs = []
    for method in methods:
        rank_pairs.append((method, avg_rank[method]))
    rank_pairs.sort(key=lambda pair: pair[1])

    lines.append("## 3) 방법별 평균 순위")
    lines.append("")
    lines.append("| 방법 | 평균 순위(낮을수록 좋음) |")
    lines.append("| --- | ---: |")
    for method, value in rank_pairs:
        lines.append(f"| {labels[method]} | {value:.2f} |")
    lines.append("")

    lines.append("## 4) 해석")
    lines.append("")
    if rank_pairs:
        best_method = rank_pairs[0][0]
        lines.append(f"- 평균 순위 1위: **{labels[best_method]}**")
    else:
        best_method = ""
        lines.append("- 평균 순위 계산 불가")

    ndcg_pairs = []
    for method in methods:
        row = macro_avg.get(method, {})
        if not isinstance(row, dict):
            row = {}
        ndcg_pairs.append((method, float(row.get(ndcg_key, 0.0))))
    ndcg_pairs.sort(key=lambda pair: pair[1], reverse=True)

    if len(ndcg_pairs) >= 2:
        gap = ndcg_pairs[0][1] - ndcg_pairs[1][1]
        lines.append(
            f"- nDCG@{top_k} 기준 1위와 2위 차이: **{gap:.4f}** "
            f"({labels[ndcg_pairs[0][0]]} vs {labels[ndcg_pairs[1][0]]})"
        )
    lines.append("")

    lines.append("## 5) 쿼리별 지표")
    lines.append("")
    lines.append(
        f"| Query | 방법 | nDCG@{top_k} | Recall@{top_k} | MRR@{top_k} | Retrieved IDs | Relevant IDs |"
    )
    lines.append("| --- | --- | ---: | ---: | ---: | --- | --- |")

    for query, item in per_query.items():
        if not isinstance(item, dict):
            continue

        relevant_ids = item.get("relevant_doc_ids", [])
        if not isinstance(relevant_ids, list):
            relevant_ids = []
        relevant_text = to_text(relevant_ids)

        ranking_item = raw_rankings.get(query, {})
        if not isinstance(ranking_item, dict):
            ranking_item = {}

        for method in methods:
            method_scores = item.get(method, {})
            if not isinstance(method_scores, dict):
                method_scores = {}
            method_ids = ranking_item.get(method, [])
            if not isinstance(method_ids, list):
                method_ids = []
            lines.append(
                f"| {query} | {labels[method]} | "
                f"{float(method_scores.get(ndcg_key, 0.0)):.4f} | "
                f"{float(method_scores.get(recall_key, 0.0)):.4f} | "
                f"{float(method_scores.get(mrr_key, 0.0)):.4f} | "
                f"{to_text(method_ids)} | {relevant_text} |"
            )

    lines.append("")
    return "\n".join(lines)
