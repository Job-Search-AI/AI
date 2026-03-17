def evaluate_crawl_kpis(
    records: list[dict], warn: dict | None = None, crit: dict | None = None
) -> dict:
    warn_set = {"csr": 0.85, "vpcr": 0.75}
    crit_set = {"csr": 0.70, "vpcr": 0.60}

    if warn is not None:
        for key in warn:
            warn_set[key] = warn[key]
    if crit is not None:
        for key in crit:
            crit_set[key] = crit[key]

    sum_all = {
        "attempt": 0,
        "success": 0,
        "valid": 0,
        "duplicate": 0,
        "invalid": 0,
    }
    group_map = {}

    idx = 0
    while idx < len(records):
        row = records[idx]
        day = row["date"]
        src = row["source"]
        key = (day, src)

        if key not in group_map:
            group_map[key] = {
                "date": day,
                "source": src,
                "attempt": 0,
                "success": 0,
                "valid": 0,
                "duplicate": 0,
                "invalid": 0,
            }

        group_map[key]["attempt"] += row["attempt"]
        group_map[key]["success"] += row["success"]
        group_map[key]["valid"] += row["valid"]
        group_map[key]["duplicate"] += row["duplicate"]
        group_map[key]["invalid"] += row["invalid"]

        sum_all["attempt"] += row["attempt"]
        sum_all["success"] += row["success"]
        sum_all["valid"] += row["valid"]
        sum_all["duplicate"] += row["duplicate"]
        sum_all["invalid"] += row["invalid"]
        idx += 1

    by_day_source = []
    keys = sorted(group_map.keys())
    for key in keys:
        row = group_map[key]

        if row["attempt"] == 0:
            csr = 0.0
        else:
            csr = row["success"] / row["attempt"]

        if row["success"] == 0:
            vpcr = 0.0
            dup_rate = 0.0
            invalid_rate = 0.0
        else:
            vpcr = row["valid"] / row["success"]
            dup_rate = row["duplicate"] / row["success"]
            invalid_rate = row["invalid"] / row["success"]

        status = "ok"
        if csr < crit_set["csr"] or vpcr < crit_set["vpcr"]:
            status = "crit"
        elif csr < warn_set["csr"] or vpcr < warn_set["vpcr"]:
            status = "warn"

        by_day_source.append(
            {
                "date": row["date"],
                "source": row["source"],
                "attempt": row["attempt"],
                "success": row["success"],
                "valid": row["valid"],
                "duplicate": row["duplicate"],
                "invalid": row["invalid"],
                "csr": round(csr, 4),
                "vpcr": round(vpcr, 4),
                "duplicate_rate": round(dup_rate, 4),
                "invalid_rate": round(invalid_rate, 4),
                "status": status,
            }
        )

    if sum_all["attempt"] == 0:
        all_csr = 0.0
    else:
        all_csr = sum_all["success"] / sum_all["attempt"]

    if sum_all["success"] == 0:
        all_vpcr = 0.0
        all_dup_rate = 0.0
        all_invalid_rate = 0.0
    else:
        all_vpcr = sum_all["valid"] / sum_all["success"]
        all_dup_rate = sum_all["duplicate"] / sum_all["success"]
        all_invalid_rate = sum_all["invalid"] / sum_all["success"]

    all_status = "ok"
    if all_csr < crit_set["csr"] or all_vpcr < crit_set["vpcr"]:
        all_status = "crit"
    elif all_csr < warn_set["csr"] or all_vpcr < warn_set["vpcr"]:
        all_status = "warn"

    return {
        "overall": {
            "attempt": sum_all["attempt"],
            "success": sum_all["success"],
            "valid": sum_all["valid"],
            "duplicate": sum_all["duplicate"],
            "invalid": sum_all["invalid"],
            "csr": round(all_csr, 4),
            "vpcr": round(all_vpcr, 4),
            "duplicate_rate": round(all_dup_rate, 4),
            "invalid_rate": round(all_invalid_rate, 4),
            "status": all_status,
        },
        "by_day_source": by_day_source,
        "thresholds": {
            "warn": {"csr": warn_set["csr"], "vpcr": warn_set["vpcr"]},
            "crit": {"csr": crit_set["csr"], "vpcr": crit_set["vpcr"]},
        },
    }
