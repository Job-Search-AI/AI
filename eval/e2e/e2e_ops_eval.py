import datetime
import json
import math
import os
import subprocess
import time

import requests


def run():
    base = os.getenv("EVAL_BASE_URL", "https://35-206-120-191.sslip.io").rstrip("/")
    text = os.getenv("EVAL_QUERY", "서울 백엔드 신입 대졸 채용공고 찾아줘")
    warm = 2
    size = 20
    conc = 2
    poll = float(os.getenv("EVAL_POLL_SEC", "0.5"))
    jobtimeout = float(os.getenv("EVAL_JOB_TIMEOUT_SEC", "180"))
    httptimeout = float(os.getenv("EVAL_HTTP_TIMEOUT_SEC", "20"))

    runstart = time.time()
    runstarttxt = (
        datetime.datetime.fromtimestamp(runstart, datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )

    sess = requests.Session()
    rows = []
    errs = []

    phases = [("warmup", warm), ("measure", size)]
    phasei = 0
    while phasei < len(phases):
        phase = phases[phasei][0]
        total = phases[phasei][1]
        sent = 0
        done = 0
        num = 0
        active = []

        while done < total:
            while sent < total and len(active) < conc:
                tcreate = time.time()
                payload = {"user_input": text + " #" + str(num)}
                try:
                    post = sess.post(
                        base + "/query/jobs",
                        json=payload,
                        timeout=httptimeout,
                    )
                    taccept = time.time()
                except Exception as exc:
                    taccept = time.time()
                    row = {
                        "phase": phase,
                        "num": num,
                        "job_id": None,
                        "t_create": tcreate,
                        "t_accepted": taccept,
                        "t_running": None,
                        "t_terminal": taccept,
                        "final_status": "failed",
                        "result_status": None,
                        "error": "post_exception",
                    }
                    rows.append(row)
                    errs.append(
                        {
                            "type": "post_exception",
                            "phase": phase,
                            "num": num,
                            "detail": str(exc),
                        }
                    )
                    sent += 1
                    done += 1
                    num += 1
                    continue

                if post.status_code != 202:
                    row = {
                        "phase": phase,
                        "num": num,
                        "job_id": None,
                        "t_create": tcreate,
                        "t_accepted": taccept,
                        "t_running": None,
                        "t_terminal": taccept,
                        "final_status": "failed",
                        "result_status": None,
                        "error": "post_non_202",
                    }
                    rows.append(row)
                    errs.append(
                        {
                            "type": "post_non_202",
                            "phase": phase,
                            "num": num,
                            "status_code": post.status_code,
                            "body": post.text,
                        }
                    )
                    sent += 1
                    done += 1
                    num += 1
                    continue

                body = {}
                try:
                    body = post.json()
                except Exception as exc:
                    row = {
                        "phase": phase,
                        "num": num,
                        "job_id": None,
                        "t_create": tcreate,
                        "t_accepted": taccept,
                        "t_running": None,
                        "t_terminal": taccept,
                        "final_status": "failed",
                        "result_status": None,
                        "error": "post_json_exception",
                    }
                    rows.append(row)
                    errs.append(
                        {
                            "type": "post_json_exception",
                            "phase": phase,
                            "num": num,
                            "detail": str(exc),
                            "body": post.text,
                        }
                    )
                    sent += 1
                    done += 1
                    num += 1
                    continue

                jobid = body.get("job_id")
                if not isinstance(jobid, str) or not jobid:
                    row = {
                        "phase": phase,
                        "num": num,
                        "job_id": None,
                        "t_create": tcreate,
                        "t_accepted": taccept,
                        "t_running": None,
                        "t_terminal": taccept,
                        "final_status": "failed",
                        "result_status": None,
                        "error": "job_id_missing",
                    }
                    rows.append(row)
                    errs.append(
                        {
                            "type": "job_id_missing",
                            "phase": phase,
                            "num": num,
                            "body": body,
                        }
                    )
                    sent += 1
                    done += 1
                    num += 1
                    continue

                row = {
                    "phase": phase,
                    "num": num,
                    "job_id": jobid,
                    "t_create": tcreate,
                    "t_accepted": taccept,
                    "t_running": None,
                    "t_terminal": None,
                    "final_status": None,
                    "result_status": None,
                    "error": None,
                }
                active.append(row)
                sent += 1
                num += 1

            nextactive = []
            ai = 0
            while ai < len(active):
                row = active[ai]
                now = time.time()
                if now - row["t_create"] > jobtimeout:
                    row["t_terminal"] = now
                    row["final_status"] = "failed"
                    row["error"] = "poll_timeout"
                    rows.append(row)
                    errs.append(
                        {
                            "type": "poll_timeout",
                            "phase": row["phase"],
                            "num": row["num"],
                            "job_id": row["job_id"],
                        }
                    )
                    done += 1
                    ai += 1
                    continue

                try:
                    pollres = sess.get(
                        base + "/query/jobs/" + row["job_id"],
                        timeout=httptimeout,
                    )
                    now = time.time()
                except Exception as exc:
                    errs.append(
                        {
                            "type": "poll_exception",
                            "phase": row["phase"],
                            "num": row["num"],
                            "job_id": row["job_id"],
                            "detail": str(exc),
                        }
                    )
                    nextactive.append(row)
                    ai += 1
                    continue

                if pollres.status_code != 200:
                    errs.append(
                        {
                            "type": "poll_non_200",
                            "phase": row["phase"],
                            "num": row["num"],
                            "job_id": row["job_id"],
                            "status_code": pollres.status_code,
                            "body": pollres.text,
                        }
                    )
                    nextactive.append(row)
                    ai += 1
                    continue

                payload = {}
                try:
                    payload = pollres.json()
                except Exception as exc:
                    errs.append(
                        {
                            "type": "poll_json_exception",
                            "phase": row["phase"],
                            "num": row["num"],
                            "job_id": row["job_id"],
                            "detail": str(exc),
                        }
                    )
                    nextactive.append(row)
                    ai += 1
                    continue

                state = payload.get("status")
                if state == "running" and row["t_running"] is None:
                    row["t_running"] = now

                if state == "done" or state == "failed":
                    row["t_terminal"] = now
                    row["final_status"] = state
                    if state == "done":
                        result = payload.get("result")
                        if isinstance(result, dict):
                            status = result.get("status")
                            if isinstance(status, str):
                                row["result_status"] = status
                    if state == "failed":
                        msg = payload.get("message")
                        if isinstance(msg, str):
                            row["error"] = msg
                    rows.append(row)
                    done += 1
                    ai += 1
                    continue

                nextactive.append(row)
                ai += 1

            active = nextactive

            if done < total:
                time.sleep(poll)

        phasei += 1

    runend = time.time()
    runendtxt = (
        datetime.datetime.fromtimestamp(runend, datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )

    measured = []
    ri = 0
    while ri < len(rows):
        row = rows[ri]
        if row["phase"] == "measure":
            measured.append(row)
        ri += 1

    accepts = []
    waits = []
    e2es = []
    works = []
    items = []

    mi = 0
    while mi < len(measured):
        row = measured[mi]
        accept = None
        wait = None
        e2e = None
        work = None

        if row["t_accepted"] is not None and row["t_create"] is not None:
            accept = round((row["t_accepted"] - row["t_create"]) * 1000, 2)
            accepts.append(accept)

        if row["t_terminal"] is not None and row["t_create"] is not None:
            e2e = round((row["t_terminal"] - row["t_create"]) * 1000, 2)
            e2es.append(e2e)

        if row["t_running"] is not None and row["t_accepted"] is not None:
            wait = round((row["t_running"] - row["t_accepted"]) * 1000, 2)
            waits.append(wait)

        if row["t_terminal"] is not None and row["t_running"] is not None:
            work = round((row["t_terminal"] - row["t_running"]) * 1000, 2)
            works.append(work)

        item = {
            "num": row["num"],
            "job_id": row["job_id"],
            "final_status": row["final_status"],
            "result_status": row["result_status"],
            "error": row["error"],
            "accept_latency_ms": accept,
            "queue_wait_ms": wait,
            "e2e_latency_ms": e2e,
            "processing_ms": work,
        }
        items.append(item)
        mi += 1

    lat = {}
    groups = [
        ("accept_latency_ms", accepts),
        ("queue_wait_ms", waits),
        ("e2e_latency_ms", e2es),
        ("processing_ms", works),
    ]

    gi = 0
    while gi < len(groups):
        name = groups[gi][0]
        vals = groups[gi][1]

        ordered = []
        vi = 0
        while vi < len(vals):
            ordered.append(vals[vi])
            vi += 1
        ordered.sort()

        count = len(ordered)
        block = {"count": count, "avg": None, "p50": None, "p95": None, "p99": None}
        if count > 0:
            total = 0.0
            ti = 0
            while ti < count:
                total += ordered[ti]
                ti += 1

            i50 = int(math.ceil(count * 0.50) - 1)
            i95 = int(math.ceil(count * 0.95) - 1)
            i99 = int(math.ceil(count * 0.99) - 1)
            if i50 < 0:
                i50 = 0
            if i95 < 0:
                i95 = 0
            if i99 < 0:
                i99 = 0

            block["avg"] = round(total / count, 2)
            block["p50"] = ordered[i50]
            block["p95"] = ordered[i95]
            block["p99"] = ordered[i99]

        lat[name] = block
        gi += 1

    total = len(measured)
    done = 0
    failed = 0
    complete = 0
    incomplete = 0

    si = 0
    while si < len(measured):
        row = measured[si]
        if row["final_status"] == "done":
            done += 1
        if row["final_status"] == "failed":
            failed += 1
        if row["result_status"] == "complete":
            complete += 1
        if row["result_status"] == "incomplete":
            incomplete += 1
        si += 1

    success = {
        "total_count": total,
        "done_count": done,
        "failed_count": failed,
        "complete_count": complete,
        "incomplete_count": incomplete,
        "system_success_rate": None,
        "business_success_rate": None,
        "incomplete_rate": None,
    }

    if total > 0:
        success["system_success_rate"] = round(1 - (failed / total), 4)
        success["business_success_rate"] = round(complete / total, 4)
        success["incomplete_rate"] = round(incomplete / total, 4)

    memory = {
        "available": False,
        "reason": None,
        "record_count": 0,
        "stage_count": {},
        "mem_peak_cgroup_mb": None,
        "mem_p95_cgroup_mb": None,
        "mem_peak_rss_mb": None,
    }

    stage = ["start", "after_crawl", "after_parse", "after_retrieval", "end"]
    bi = 0
    while bi < len(stage):
        memory["stage_count"][stage[bi]] = 0
        bi += 1

    startwin = runstart - 30
    endwin = runend + 30
    starttxt = (
        datetime.datetime.fromtimestamp(startwin, datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    endtxt = (
        datetime.datetime.fromtimestamp(endwin, datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )

    filt = 'timestamp >= "' + starttxt + '" AND timestamp <= "' + endtxt + '" AND ('
    fi = 0
    while fi < len(stage):
        name = stage[fi]
        if fi > 0:
            filt += " OR "
        filt += 'jsonPayload.stage="' + name + '"'
        filt += ' OR textPayload:"\\"stage\\": \\"' + name + '\\""'
        fi += 1
    filt += ")"

    ext = os.getenv("EVAL_GCLOUD_FILTER", "").strip()
    if ext:
        filt = "(" + ext + ") AND (" + filt + ")"

    limit = os.getenv("EVAL_GCLOUD_LIMIT", "10000")
    proj = os.getenv("EVAL_GCP_PROJECT", "").strip()

    cmd = [
        "gcloud",
        "logging",
        "read",
        filt,
        "--format=json",
        "--limit",
        limit,
    ]

    if proj:
        cmd.append("--project")
        cmd.append(proj)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logs = json.loads(res.stdout)

        if not isinstance(logs, list):
            logs = []

        cgroups = []
        rsses = []

        li = 0
        while li < len(logs):
            one = logs[li]
            data = None

            if isinstance(one, dict):
                payload = one.get("jsonPayload")
                if isinstance(payload, dict):
                    data = payload

                if data is None:
                    textpayload = one.get("textPayload")
                    if isinstance(textpayload, str):
                        textpayload = textpayload.strip()
                        if textpayload.startswith("{") and textpayload.endswith("}"):
                            parsed = json.loads(textpayload)
                            if isinstance(parsed, dict):
                                data = parsed

            if isinstance(data, dict):
                st = data.get("stage")
                if isinstance(st, str) and st in memory["stage_count"]:
                    memory["stage_count"][st] += 1
                    memory["record_count"] += 1

                    cgroup = data.get("cgroup_mb")
                    if isinstance(cgroup, int) or isinstance(cgroup, float):
                        cgroups.append(float(cgroup))
                    if isinstance(cgroup, str):
                        cgroups.append(float(cgroup))

                    rss = data.get("rss_mb")
                    if isinstance(rss, int) or isinstance(rss, float):
                        rsses.append(float(rss))
                    if isinstance(rss, str):
                        rsses.append(float(rss))

            li += 1

        if len(cgroups) > 0 or len(rsses) > 0:
            memory["available"] = True

        if len(cgroups) > 0:
            cgroups.sort()
            memory["mem_peak_cgroup_mb"] = cgroups[len(cgroups) - 1]
            ip95 = int(math.ceil(len(cgroups) * 0.95) - 1)
            if ip95 < 0:
                ip95 = 0
            memory["mem_p95_cgroup_mb"] = cgroups[ip95]

        if len(rsses) > 0:
            rsses.sort()
            memory["mem_peak_rss_mb"] = rsses[len(rsses) - 1]

        if not memory["available"]:
            memory["reason"] = "no_memory_records_in_window"

    except Exception as exc:
        memory["available"] = False
        memory["reason"] = str(exc)

    report = {
        "run_meta": {
            "started_at_utc": runstarttxt,
            "ended_at_utc": runendtxt,
            "target_url": base,
            "concurrency": conc,
            "warmup_count": warm,
            "measure_count": size,
            "query": text,
        },
        "latency": lat,
        "success": success,
        "memory": memory,
        "raw_errors": errs,
        "jobs": items,
    }

    report_path = os.path.join(os.path.dirname(__file__), "e2e_ops_eval_report.md")
    report["run_meta"]["report_path"] = report_path

    errtypes = {}
    ei = 0
    while ei < len(errs):
        one = errs[ei]
        key = "unknown"
        if isinstance(one, dict):
            val = one.get("type")
            if isinstance(val, str) and val:
                key = val
        if key in errtypes:
            errtypes[key] += 1
        else:
            errtypes[key] = 1
        ei += 1

    lines = []
    lines.append("# E2E 운영 성능 평가 보고서")
    lines.append("")
    lines.append("## 실행 메타")
    lines.append("| 항목 | 값 |")
    lines.append("| --- | --- |")
    lines.append("| started_at_utc | " + str(runstarttxt) + " |")
    lines.append("| ended_at_utc | " + str(runendtxt) + " |")
    lines.append("| target_url | " + str(base) + " |")
    lines.append("| warmup_count | " + str(warm) + " |")
    lines.append("| measure_count | " + str(size) + " |")
    lines.append("| concurrency | " + str(conc) + " |")
    lines.append("| query | " + str(text) + " |")
    lines.append("")
    lines.append("## 지연 지표")
    lines.append("| metric | count | avg | p50 | p95 | p99 |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")

    keys = ["accept_latency_ms", "queue_wait_ms", "e2e_latency_ms", "processing_ms"]
    ki = 0
    while ki < len(keys):
        key = keys[ki]
        block = lat.get(key)
        if not isinstance(block, dict):
            block = {}

        count = block.get("count")
        avg = block.get("avg")
        p50 = block.get("p50")
        p95 = block.get("p95")
        p99 = block.get("p99")

        counttxt = "-"
        if count is not None:
            counttxt = str(count)
        avgtxt = "-"
        if avg is not None:
            avgtxt = str(avg)
        p50txt = "-"
        if p50 is not None:
            p50txt = str(p50)
        p95txt = "-"
        if p95 is not None:
            p95txt = str(p95)
        p99txt = "-"
        if p99 is not None:
            p99txt = str(p99)

        lines.append(
            "| "
            + key
            + " | "
            + counttxt
            + " | "
            + avgtxt
            + " | "
            + p50txt
            + " | "
            + p95txt
            + " | "
            + p99txt
            + " |"
        )
        ki += 1

    lines.append("")
    lines.append("## 성공률 지표")
    lines.append("| 항목 | 값 |")
    lines.append("| --- | ---: |")
    lines.append("| total_count | " + str(success.get("total_count")) + " |")
    lines.append("| done_count | " + str(success.get("done_count")) + " |")
    lines.append("| failed_count | " + str(success.get("failed_count")) + " |")
    lines.append("| complete_count | " + str(success.get("complete_count")) + " |")
    lines.append("| incomplete_count | " + str(success.get("incomplete_count")) + " |")
    lines.append("| system_success_rate | " + str(success.get("system_success_rate")) + " |")
    lines.append("| business_success_rate | " + str(success.get("business_success_rate")) + " |")
    lines.append("| incomplete_rate | " + str(success.get("incomplete_rate")) + " |")

    lines.append("")
    lines.append("## 메모리 지표")
    lines.append("| 항목 | 값 |")
    lines.append("| --- | --- |")
    lines.append("| available | " + str(memory.get("available")) + " |")
    lines.append("| reason | " + str(memory.get("reason")) + " |")
    lines.append("| record_count | " + str(memory.get("record_count")) + " |")
    lines.append("| mem_peak_cgroup_mb | " + str(memory.get("mem_peak_cgroup_mb")) + " |")
    lines.append("| mem_p95_cgroup_mb | " + str(memory.get("mem_p95_cgroup_mb")) + " |")
    lines.append("| mem_peak_rss_mb | " + str(memory.get("mem_peak_rss_mb")) + " |")
    lines.append("")
    lines.append("### stage_count")
    lines.append("| stage | count |")
    lines.append("| --- | ---: |")

    stagecount = memory.get("stage_count")
    if isinstance(stagecount, dict):
        skeys = list(stagecount.keys())
        skeys.sort()
        si = 0
        while si < len(skeys):
            skey = skeys[si]
            sval = stagecount.get(skey)
            lines.append("| " + str(skey) + " | " + str(sval) + " |")
            si += 1
    else:
        lines.append("| - | - |")

    lines.append("")
    lines.append("## 오류 요약")
    lines.append("| type | count |")
    lines.append("| --- | ---: |")
    if len(errtypes) == 0:
        lines.append("| none | 0 |")
    else:
        ekeys = list(errtypes.keys())
        ekeys.sort()
        ek = 0
        while ek < len(ekeys):
            ekey = ekeys[ek]
            evals = errtypes.get(ekey)
            lines.append("| " + str(ekey) + " | " + str(evals) + " |")
            ek += 1

    lines.append("")
    lines.append("### 대표 오류 샘플")
    if len(errs) == 0:
        lines.append("- 없음")
    else:
        em = 0
        printed = 0
        while em < len(errs):
            one = errs[em]
            lines.append("- `" + json.dumps(one, ensure_ascii=False) + "`")
            printed += 1
            if printed >= 5:
                break
            em += 1

    lines.append("")
    lines.append("## 부록: JSON 원문")
    lines.append("```json")
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    mdtext = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(mdtext)

    print("[e2e_ops_eval] target:", base)
    print("[e2e_ops_eval] warmup:", warm, "measure:", size, "concurrency:", conc)
    print("[e2e_ops_eval] success(system/business):", success["system_success_rate"], success["business_success_rate"])
    print(
        "[e2e_ops_eval] e2e(ms) p50/p95/p99:",
        lat["e2e_latency_ms"]["p50"],
        lat["e2e_latency_ms"]["p95"],
        lat["e2e_latency_ms"]["p99"],
    )
    print("[e2e_ops_eval] memory available:", memory["available"], "reason:", memory["reason"])
    print("[e2e_ops_eval] report md:", report_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
