import hashlib
import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQ_KEYS = ("case_id", "query", "user_response", "retrieved_job_info_list")

THRESHOLD = {
    "balanced": {"evidence": 85.0, "recommendation": 75.0},
    "strict": {"evidence": 90.0, "recommendation": 80.0},
    "lenient": {"evidence": 80.0, "recommendation": 70.0},
}

REGION = [
    "서울",
    "경기",
    "인천",
    "부산",
    "대구",
    "대전",
    "광주",
    "울산",
    "세종",
    "강원",
    "충남",
    "충북",
    "전남",
    "전북",
    "경남",
    "경북",
    "제주",
]

EDU = ["고졸", "대졸", "학력무관", "2년제", "3년제", "4년제", "석사", "박사"]

JOB = [
    "백엔드",
    "프론트엔드",
    "데이터",
    "AI",
    "NLP",
    "RAG",
    "CV",
    "컴퓨터비전",
    "소프트웨어",
    "개발자",
    "연구원",
    "엔지니어",
]


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^0-9a-z가-힣]+", "", text)
    return text


def _uniq(values: list[str]) -> list[str]:
    out = []
    seen = set()
    for value in values:
        if not value:
            continue
        key = value.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _find_words(text: str, words: list[str]) -> list[str]:
    found = []
    for word in words:
        if word in text:
            found.append(word)
    return _uniq(found)


def _find_regex(text: str, pattern: str) -> list[str]:
    hits = re.findall(pattern, text, flags=re.IGNORECASE)
    out = []
    for hit in hits:
        if isinstance(hit, tuple):
            if len(hit) > 0:
                out.append(str(hit[0]))
            continue
        out.append(str(hit))
    return _uniq(out)


def _first(values: list[str]) -> str:
    if not values:
        return ""
    return values[0]


def _num(text: str) -> list[int]:
    out = []
    hits = re.findall(r"\d+", text)
    for hit in hits:
        out.append(int(hit))
    return out


def _is_support(claim: str, all_norm: str) -> bool:
    claim_norm = _norm(claim)
    if not claim_norm:
        return False
    return claim_norm in all_norm


def _exp_ok(claim: str, top_exp: str) -> bool:
    if not claim:
        return True
    if "무관" in top_exp:
        return True
    if claim == "신입":
        return "신입" in top_exp
    if claim == "무관":
        return "무관" in top_exp
    if claim.endswith("년"):
        if claim in top_exp:
            return True
        top_num = _num(top_exp)
        claim_num = _num(claim)
        if not claim_num:
            return False
        n = claim_num[0]
        if len(top_num) >= 2:
            low = top_num[0]
            high = top_num[1]
            if low <= n <= high:
                return True
        if len(top_num) == 1:
            return n == top_num[0]
        return False
    return claim in top_exp


def _doc_info(docs: list[str]) -> dict[str, Any]:
    all_text = ""
    idx = 0
    while idx < len(docs):
        all_text += docs[idx]
        all_text += "\n"
        idx += 1

    top = ""
    if docs:
        top = docs[0]

    top_company = _first(_find_regex(top, r"회사명[:\s]*([^\n|]+)"))
    top_title = _first(_find_regex(top, r"공고제목[:\s]*([^\n]+)"))
    top_loc = _first(_find_regex(top, r"(?:근무지역|근무지)\s*[:：]\s*([^\n]+)"))
    top_exp = _first(_find_regex(top, r"경력[:\s]*([^\n]+)"))
    top_edu = _first(_find_regex(top, r"학력[:\s]*([^\n]+)"))
    top_regions = _find_words(top, REGION)

    all_loc = _find_regex(all_text, r"(?:근무지역|근무지)\s*[:：]\s*([^\n]+)")
    all_exp = _find_regex(all_text, r"경력[:\s]*([^\n]+)")
    all_edu = _find_regex(all_text, r"학력[:\s]*([^\n]+)")
    all_deadline = _find_regex(all_text, r"마감일[:\s]*([^\n]+)")
    all_salary = _find_regex(all_text, r"급여[:\s]*([^\n]+)")
    all_regions = _find_words(all_text, REGION)

    return {
        "top_text": top,
        "top_company": top_company,
        "top_title": top_title,
        "top_loc": top_loc,
        "top_exp": top_exp,
        "top_edu": top_edu,
        "top_regions": top_regions,
        "all_loc": all_loc,
        "all_exp": all_exp,
        "all_edu": all_edu,
        "all_deadline": all_deadline,
        "all_salary": all_salary,
        "all_regions": all_regions,
        "all_text": all_text,
        "all_norm": _norm(all_text),
    }


def _query_info(query: str) -> dict[str, Any]:
    query_region = ""
    for word in REGION:
        if word in query:
            query_region = word
            break

    query_exp = ""
    if "신입" in query:
        query_exp = "신입"
    elif "무관" in query:
        query_exp = "무관"
    else:
        hits = _find_regex(query, r"(\d+)\s*년")
        if hits:
            query_exp = hits[0] + "년"

    query_edu = ""
    for word in EDU:
        if word in query:
            query_edu = word
            break

    query_job = _find_words(query, JOB)
    if not query_job:
        raw = re.split(r"[,\s/]+", query)
        stop = set(REGION + EDU + ["신입", "무관", "경력", "대졸"])
        for token in raw:
            token = token.strip()
            if not token:
                continue
            if token in stop:
                continue
            if re.search(r"\d", token):
                continue
            query_job.append(token)
            if len(query_job) >= 3:
                break

    return {
        "region": query_region,
        "exp": query_exp,
        "edu": query_edu,
        "job": _uniq(query_job),
    }


def _resp_info(response: str) -> dict[str, Any]:
    region = _find_words(response, REGION)

    exp = []
    if "경력 무관" in response:
        exp.append("무관")
    if "신입" in response:
        exp.append("신입")
    year = _find_regex(response, r"(\d+)\s*년")
    for y in year:
        exp.append(y + "년")
    exp = _uniq(exp)

    edu = _find_words(response, EDU)
    date = _find_regex(response, r"\d{4}[./-]\d{1,2}[./-]\d{1,2}")
    mmdd = _find_regex(response, r"\d{1,2}월\s*\d{1,2}일")
    for item in mmdd:
        date.append(item)
    date = _uniq(date)
    salary = _find_regex(response, r"(?:연봉\s*)?\d[\d,]*(?:\.\d+)?\s*(?:만원|원)")
    job = _find_words(response, JOB)

    has_apply = False
    if "지원" in response:
        has_apply = True
    if "접수" in response:
        has_apply = True
    if "이력서" in response:
        has_apply = True
    if "지원방법" in response:
        has_apply = True

    has_deadline = "마감" in response

    return {
        "region": region,
        "exp": exp,
        "edu": edu,
        "date": date,
        "salary": salary,
        "job": job,
        "has_apply": has_apply,
        "has_deadline": has_deadline,
    }


def _score_case(case: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    query = str(case["query"])
    response = str(case["user_response"])
    raw_docs = case["retrieved_job_info_list"]

    docs = []
    idx = 0
    while idx < len(raw_docs):
        docs.append(str(raw_docs[idx]))
        idx += 1

    doc = _doc_info(docs)
    q = _query_info(query)
    r = _resp_info(response)

    response_norm = _norm(response)

    anchors = []
    if doc["top_company"]:
        anchors.append(doc["top_company"])
    if doc["top_title"]:
        anchors.append(doc["top_title"])
    if doc["top_loc"]:
        anchors.append(doc["top_loc"])

    top1 = 0.0
    i = 0
    while i < len(anchors):
        token = _norm(anchors[i])
        if token and token in response_norm:
            top1 = 1.0
            break
        i += 1

    supported = 0
    claim_total = 0
    claim_list = []
    for key in ("region", "exp", "edu", "date", "salary"):
        values = r[key]
        j = 0
        while j < len(values):
            claim_list.append(values[j])
            j += 1

    k = 0
    while k < len(claim_list):
        claim_total += 1
        if _is_support(claim_list[k], doc["all_norm"]):
            supported += 1
        k += 1

    support_ratio = 1.0
    if claim_total > 0:
        support_ratio = supported / claim_total

    num_claim = []
    j = 0
    while j < len(r["date"]):
        num_claim.append(r["date"][j])
        j += 1
    j = 0
    while j < len(r["salary"]):
        num_claim.append(r["salary"][j])
        j += 1

    hall = 0
    j = 0
    while j < len(num_claim):
        if not _is_support(num_claim[j], doc["all_norm"]):
            hall += 1
        j += 1

    non_hall = 1.0
    if num_claim:
        non_hall = 1.0 - (hall / len(num_claim))

    contra = 0
    contra_check = 0

    j = 0
    while j < len(r["region"]):
        contra_check += 1
        if doc["top_regions"]:
            if r["region"][j] not in doc["top_regions"]:
                contra += 1
        j += 1

    j = 0
    while j < len(r["exp"]):
        if doc["top_exp"]:
            contra_check += 1
            if not _exp_ok(r["exp"][j], doc["top_exp"]):
                contra += 1
        j += 1

    j = 0
    while j < len(r["edu"]):
        if doc["top_edu"]:
            contra_check += 1
            if r["edu"][j] not in doc["top_edu"]:
                contra += 1
        j += 1

    non_contra = 1.0
    if contra_check > 0:
        non_contra = 1.0 - (contra / contra_check)

    evidence = 100.0 * (0.4 * support_ratio + 0.2 * non_contra + 0.2 * non_hall + 0.2 * top1)

    slot_total = 0
    slot_match = 0

    if q["region"]:
        slot_total += 1
        if q["region"] in doc["top_text"] or q["region"] in doc["top_regions"]:
            slot_match += 1

    if q["exp"]:
        slot_total += 1
        if _exp_ok(q["exp"], doc["top_exp"]):
            slot_match += 1

    if q["edu"]:
        slot_total += 1
        if q["edu"] in doc["top_edu"] or q["edu"] in doc["top_text"]:
            slot_match += 1

    if q["job"]:
        slot_total += 1
        ok = False
        j = 0
        while j < len(q["job"]):
            if q["job"][j].lower() in doc["top_text"].lower():
                ok = True
                break
            j += 1
        if ok:
            slot_match += 1

    slot_ratio = 1.0
    if slot_total > 0:
        slot_ratio = slot_match / slot_total

    axis_hit = 0

    job_axis = False
    if r["job"]:
        j = 0
        while j < len(r["job"]):
            if r["job"][j].lower() in doc["top_text"].lower():
                job_axis = True
                break
            j += 1
    if job_axis:
        axis_hit += 1

    region_axis = False
    if r["region"]:
        j = 0
        while j < len(r["region"]):
            if _is_support(r["region"][j], doc["all_norm"]):
                region_axis = True
                break
            j += 1
    if region_axis:
        axis_hit += 1

    exp_axis = False
    if r["exp"]:
        j = 0
        while j < len(r["exp"]):
            if _is_support(r["exp"][j], doc["all_norm"]):
                exp_axis = True
                break
            j += 1
    if exp_axis:
        axis_hit += 1

    edu_axis = False
    if r["edu"]:
        j = 0
        while j < len(r["edu"]):
            if _is_support(r["edu"][j], doc["all_norm"]):
                edu_axis = True
                break
            j += 1
    if edu_axis:
        axis_hit += 1

    deadline_axis = False
    if r["date"]:
        j = 0
        while j < len(r["date"]):
            if _is_support(r["date"][j], doc["all_norm"]):
                deadline_axis = True
                break
            j += 1
    elif r["has_deadline"] and "마감" in doc["all_text"]:
        deadline_axis = True
    if deadline_axis:
        axis_hit += 1

    reason = axis_hit / 5.0

    action = 0
    if r["has_apply"]:
        action += 1
    if region_axis:
        action += 1
    if deadline_axis:
        action += 1

    salary_axis = False
    if r["salary"]:
        j = 0
        while j < len(r["salary"]):
            if _is_support(r["salary"][j], doc["all_norm"]):
                salary_axis = True
                break
            j += 1
    if salary_axis:
        action += 1
    action_ratio = action / 4.0

    recommendation = 100.0 * (0.45 * slot_ratio + 0.35 * reason + 0.20 * action_ratio)
    overall = (0.6 * evidence) + (0.4 * recommendation)

    hard_hall = hall > 0
    hard_contra = contra > 0

    passed = True
    reason_code = []

    if hard_hall:
        passed = False
        reason_code.append("hard_hallucination")
    if hard_contra:
        passed = False
        reason_code.append("hard_contradiction")
    if evidence < thresholds["evidence"]:
        passed = False
        reason_code.append("low_evidence")
    if recommendation < thresholds["recommendation"]:
        passed = False
        reason_code.append("low_recommendation")

    return {
        "case_id": str(case["case_id"]),
        "evaluated": True,
        "pass": passed,
        "reason_codes": reason_code,
        "scores": {
            "evidence_score": evidence,
            "recommendation_score": recommendation,
            "overall_score": overall,
        },
        "breakdown": {
            "support_ratio": support_ratio,
            "non_contradiction_ratio": non_contra,
            "non_hallucination_ratio": non_hall,
            "top1_alignment": top1,
            "slot_match_ratio": slot_ratio,
            "reason_coverage": reason,
            "actionability": action_ratio,
        },
        "counts": {
            "claims": claim_total,
            "supported_claims": supported,
            "numeric_claims": len(num_claim),
            "hallucinations": hall,
            "contradictions": contra,
        },
    }


def _mean_ci(values: list[float], bootstrap_iter: int, seed: int) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "low": 0.0, "high": 0.0}

    total = 0.0
    i = 0
    while i < len(values):
        total += values[i]
        i += 1
    mean = total / len(values)

    rnd = random.Random(seed)
    samples = []
    b = 0
    while b < bootstrap_iter:
        one = 0.0
        i = 0
        while i < len(values):
            pick = rnd.randrange(0, len(values))
            one += values[pick]
            i += 1
        one = one / len(values)
        samples.append(one)
        b += 1

    samples.sort()
    low_i = int((bootstrap_iter - 1) * 0.025)
    high_i = int((bootstrap_iter - 1) * 0.975)

    return {"mean": mean, "low": samples[low_i], "high": samples[high_i]}


def load_cases_jsonl(path: str) -> list[dict[str, object]]:
    rows = []
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        line_no = 0
        for line in f:
            line_no += 1
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid json line at {line_no}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"line {line_no} is not an object")
            rows.append(obj)
    return rows


def evaluate_final_llm_responses(
    cases: list[dict[str, object]],
    *,
    threshold_profile: str = "balanced",
    min_cases: int = 50,
    bootstrap_iter: int = 10000,
    seed: int = 42,
) -> dict[str, object]:
    if threshold_profile not in THRESHOLD:
        raise ValueError("threshold_profile must be one of balanced, strict, lenient")
    if bootstrap_iter <= 0:
        raise ValueError("bootstrap_iter must be > 0")
    if min_cases <= 0:
        raise ValueError("min_cases must be > 0")

    thresholds = THRESHOLD[threshold_profile]

    case_rows = []
    evidence = []
    recommend = []
    overall = []
    fail_reason = Counter()
    skip_reason = Counter()

    idx = 0
    while idx < len(cases):
        row = cases[idx]
        if not isinstance(row, dict):
            case_rows.append(
                {
                    "case_id": f"case_{idx + 1}",
                    "evaluated": False,
                    "pass": False,
                    "reason_codes": ["invalid_case_type"],
                }
            )
            skip_reason["invalid_case_type"] += 1
            idx += 1
            continue

        missing = []
        for key in REQ_KEYS:
            if key not in row:
                missing.append(key)
        if missing:
            case_rows.append(
                {
                    "case_id": str(row.get("case_id", f"case_{idx + 1}")),
                    "evaluated": False,
                    "pass": False,
                    "reason_codes": ["missing_required_fields"],
                    "missing_fields": missing,
                }
            )
            skip_reason["missing_required_fields"] += 1
            idx += 1
            continue

        if not isinstance(row["query"], str):
            case_rows.append(
                {
                    "case_id": str(row["case_id"]),
                    "evaluated": False,
                    "pass": False,
                    "reason_codes": ["invalid_query_type"],
                }
            )
            skip_reason["invalid_query_type"] += 1
            idx += 1
            continue

        if not isinstance(row["user_response"], str):
            case_rows.append(
                {
                    "case_id": str(row["case_id"]),
                    "evaluated": False,
                    "pass": False,
                    "reason_codes": ["invalid_response_type"],
                }
            )
            skip_reason["invalid_response_type"] += 1
            idx += 1
            continue

        if not isinstance(row["retrieved_job_info_list"], list) or not row["retrieved_job_info_list"]:
            case_rows.append(
                {
                    "case_id": str(row["case_id"]),
                    "evaluated": False,
                    "pass": False,
                    "reason_codes": ["invalid_retrieved_docs"],
                }
            )
            skip_reason["invalid_retrieved_docs"] += 1
            idx += 1
            continue

        one = _score_case(row, thresholds)
        case_rows.append(one)

        score_obj = one["scores"]
        evidence.append(float(score_obj["evidence_score"]))
        recommend.append(float(score_obj["recommendation_score"]))
        overall.append(float(score_obj["overall_score"]))

        if not one["pass"]:
            codes = one["reason_codes"]
            j = 0
            while j < len(codes):
                fail_reason[codes[j]] += 1
                j += 1

        idx += 1

    eva_count = len(evidence)
    pass_count = 0
    i = 0
    while i < len(case_rows):
        row = case_rows[i]
        if row.get("evaluated") and row.get("pass"):
            pass_count += 1
        i += 1

    fail_count = eva_count - pass_count
    pass_rate = 0.0
    if eva_count > 0:
        pass_rate = (pass_count / eva_count) * 100.0

    evidence_ci = _mean_ci(evidence, bootstrap_iter, seed)
    recommend_ci = _mean_ci(recommend, bootstrap_iter, seed + 1)
    overall_ci = _mean_ci(overall, bootstrap_iter, seed + 2)
    official = eva_count >= min_cases

    fail_dist = {}
    fail_total = 0
    for value in fail_reason.values():
        fail_total += value
    for key, value in fail_reason.items():
        rate = 0.0
        if fail_total > 0:
            rate = (value / fail_total) * 100.0
        fail_dist[key] = {"count": value, "rate": rate}

    skip_dist = {}
    skip_total = 0
    for value in skip_reason.values():
        skip_total += value
    for key, value in skip_reason.items():
        rate = 0.0
        if skip_total > 0:
            rate = (value / skip_total) * 100.0
        skip_dist[key] = {"count": value, "rate": rate}

    out = {
        "summary": {
            "threshold_profile": threshold_profile,
            "thresholds": thresholds,
            "min_cases": min_cases,
            "total_cases": len(cases),
            "evaluated_cases": eva_count,
            "skipped_cases": len(cases) - eva_count,
            "official": official,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": pass_rate,
            "evidence_score": evidence_ci,
            "recommendation_score": recommend_ci,
            "overall_score": overall_ci,
            "failure_reason_distribution": fail_dist,
            "skip_reason_distribution": skip_dist,
        },
        "cases": case_rows,
        "meta": {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "bootstrap_iter": bootstrap_iter,
            "input_jsonl_path": None,
            "input_jsonl_sha256": None,
        },
    }
    return out


def build_markdown_report(result: dict[str, object]) -> str:
    summary = result["summary"]
    meta = result["meta"]
    cases = result["cases"]

    evidence = summary["evidence_score"]
    recommend = summary["recommendation_score"]
    overall = summary["overall_score"]
    thresholds = summary["thresholds"]

    fail_rows = []
    idx = 0
    while idx < len(cases):
        row = cases[idx]
        if row.get("evaluated") and not row.get("pass"):
            fail_rows.append(row)
        idx += 1

    fail_rows.sort(key=lambda x: x.get("scores", {}).get("overall_score", 999.0))
    if len(fail_rows) > 10:
        fail_rows = fail_rows[:10]

    lines = []
    lines.append("# 최종 LLM 평가 결과")
    lines.append("")
    lines.append("## 1. 실행 메타정보")
    lines.append(f"- 실행 시각(UTC): {meta['run_at']}")
    lines.append(f"- threshold profile: `{summary['threshold_profile']}`")
    lines.append(f"- sample 수: {summary['evaluated_cases']} / {summary['total_cases']}")
    lines.append(f"- official: `{str(summary['official']).lower()}`")
    lines.append("")
    lines.append("## 2. 핵심 결과")
    lines.append("| Metric | Mean | 95% CI |")
    lines.append("| --- | ---: | ---: |")
    lines.append(
        "| Evidence | "
        + f"{evidence['mean']:.2f}"
        + " | "
        + f"[{evidence['low']:.2f}, {evidence['high']:.2f}]"
        + " |"
    )
    lines.append(
        "| Recommendation | "
        + f"{recommend['mean']:.2f}"
        + " | "
        + f"[{recommend['low']:.2f}, {recommend['high']:.2f}]"
        + " |"
    )
    lines.append(
        "| Overall | "
        + f"{overall['mean']:.2f}"
        + " | "
        + f"[{overall['low']:.2f}, {overall['high']:.2f}]"
        + " |"
    )
    lines.append(f"| Pass Rate | {summary['pass_rate']:.1f}% | - |")
    lines.append("")
    lines.append("## 3. 게이트 판정 요약")
    lines.append(f"- Evidence threshold: {thresholds['evidence']:.2f}")
    lines.append(f"- Recommendation threshold: {thresholds['recommendation']:.2f}")
    lines.append(f"- 통과 건수: {summary['pass_count']}")
    lines.append(f"- 실패 건수: {summary['fail_count']}")
    lines.append(f"- 실패율: {100.0 - summary['pass_rate']:.1f}%")
    lines.append("")
    lines.append("## 4. 실패 사유 분포")
    lines.append("| Reason Code | Count | Rate |")
    lines.append("| --- | ---: | ---: |")
    reason_dist = summary["failure_reason_distribution"]
    if reason_dist:
        for key, value in reason_dist.items():
            lines.append(f"| `{key}` | {value['count']} | {value['rate']:.1f}% |")
    else:
        lines.append("| - | 0 | 0.0% |")
    lines.append("")
    lines.append("## 5. 주요 실패 케이스")
    lines.append("| Case ID | Evidence | Recommendation | Overall | Reasons |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    if fail_rows:
        idx = 0
        while idx < len(fail_rows):
            row = fail_rows[idx]
            score = row["scores"]
            codes = row["reason_codes"]
            code_text = ", ".join(codes)
            lines.append(
                f"| `{row['case_id']}` | {score['evidence_score']:.2f} | "
                + f"{score['recommendation_score']:.2f} | {score['overall_score']:.2f} | {code_text} |"
            )
            idx += 1
    else:
        lines.append("| - | 0.00 | 0.00 | 0.00 | - |")
    lines.append("")
    lines.append("## 6. 재현성 정보")
    lines.append(f"- input path: `{meta.get('input_jsonl_path')}`")
    lines.append(f"- input sha256: `{meta.get('input_jsonl_sha256')}`")
    lines.append(f"- seed: `{meta.get('seed')}`")
    lines.append(f"- bootstrap_iter: `{meta.get('bootstrap_iter')}`")
    lines.append("")

    return "\n".join(lines)


def write_markdown_report(result: dict[str, object], output_md_path: str) -> str:
    md_text = build_markdown_report(result)
    out = Path(output_md_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md_text, encoding="utf-8")
    return str(out.resolve())


def run_evaluation_to_markdown(
    input_jsonl_path: str,
    output_md_path: str | None = None,
    **kwargs: Any,
) -> dict[str, object]:
    cases = load_cases_jsonl(input_jsonl_path)
    result = evaluate_final_llm_responses(cases, **kwargs)

    src = Path(input_jsonl_path).resolve()
    result["meta"]["input_jsonl_path"] = str(src)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    result["meta"]["input_jsonl_sha256"] = digest

    out_path = output_md_path
    if not out_path:
        out_path = str((Path(__file__).resolve().parent / "final_eval_report.md"))

    saved_path = write_markdown_report(result, out_path)
    result["meta"]["output_md_path"] = saved_path
    return result
