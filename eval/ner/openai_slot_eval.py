def run_eval(max_count=None, root_dir=None, out_path=None):
    import json
    import os
    import re
    import warnings
    from datetime import datetime

    from src.node import predict_crf_bert
    from src.tools.slices.entity_normalizer import normalize_entities

    if root_dir is None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    data_path = os.path.join(root_dir, "data", "url_llm_data.json")
    syn_path = os.path.join(root_dir, "data", "url_exchager", "synonym_dict.json")

    if out_path is None:
        out_path = os.path.join(root_dir, "eval", "ner", "openai_slot_eval_result.md")

    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    os.environ["USE_OPENAI_MODELS"] = "true"
    os.environ["NER_MODEL_NAME"] = "gpt-5-nano"

    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        key = key.splitlines()[0].strip()
    if not key:
        raise ValueError("OPENAI_API_KEY is empty")
    os.environ["OPENAI_API_KEY"] = key

    with open(data_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    with open(syn_path, "r", encoding="utf-8") as f:
        syn = json.load(f)

    if isinstance(max_count, int):
        if max_count > 0 and max_count < len(rows):
            rows = rows[:max_count]

    warnings.filterwarnings("ignore", message="Pydantic serializer warnings*")

    slots = ("지역", "직무", "경력", "학력")

    slot_stat = {}
    slot_cov = {}
    for slot in slots:
        slot_stat[slot] = {"support": 0, "correct": 0, "tp": 0, "fp": 0, "fn": 0}
        slot_cov[slot] = 0

    miss_rows = []
    fail_rows = []
    run_time = datetime.now().isoformat(timespec="seconds")
    call_fail = 0
    full_support = 0
    full_hit = 0

    idx = 0
    while idx < len(rows):
        row = rows[idx]

        text = ""
        raw_text = row.get("input")
        if isinstance(raw_text, str):
            text = raw_text
        text_n = text.lower().replace(" ", "")

        gold = {}
        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            best_val = None
            best_len = 0
            map_data = syn.get(slot, {})

            for can_val, syn_list in map_data.items():
                word_idx = 0
                found_word = ""
                while word_idx < len(syn_list):
                    word_raw = syn_list[word_idx]
                    if isinstance(word_raw, str):
                        word = word_raw.strip().lower().replace(" ", "")
                        if word and word in text_n:
                            found_word = word
                            break
                    word_idx += 1

                if found_word:
                    now_len = len(found_word)
                    if now_len > best_len:
                        best_len = now_len
                        best_val = can_val

            gold[slot] = best_val
            slot_idx += 1

        exp_num = None
        exp_pat = re.search(r"(\d{1,2})\s*년차", text)
        if exp_pat is None:
            exp_pat = re.search(r"(\d{1,2})\s*년", text)
        if exp_pat is not None:
            num_text = exp_pat.group(1)
            num_val = int(num_text)
            if num_val >= 1 and num_val <= 20:
                exp_num = str(num_val) + "년차"
        if exp_num is not None:
            gold["경력"] = exp_num

        pred_raw = {"지역": None, "직무": None, "경력": None, "학력": None}
        fail_name = ""
        try:
            out = predict_crf_bert({"user_input": text})
            if isinstance(out, dict):
                slot_idx = 0
                while slot_idx < len(slots):
                    slot = slots[slot_idx]
                    now_val = out.get(slot)
                    if isinstance(now_val, str):
                        now_val = now_val.strip()
                        if now_val:
                            pred_raw[slot] = now_val
                    slot_idx += 1
        except Exception as err:
            call_fail += 1
            fail_name = type(err).__name__
            fail_rows.append({"idx": idx, "error": fail_name})

        pred_norm = normalize_entities(pred_raw, syn_path)
        if not isinstance(pred_norm, dict):
            pred_norm = {"지역": None, "직무": None, "경력": None, "학력": None}

        row_bad = False

        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            gold_val = gold.get(slot)
            pred_val = pred_norm.get(slot)

            if gold_val is not None:
                slot_cov[slot] = slot_cov[slot] + 1
                st = slot_stat[slot]
                st["support"] = st["support"] + 1

                if pred_val == gold_val:
                    st["correct"] = st["correct"] + 1
                    st["tp"] = st["tp"] + 1
                else:
                    row_bad = True
                    if pred_val is None:
                        st["fn"] = st["fn"] + 1
                    else:
                        st["fp"] = st["fp"] + 1
                        st["fn"] = st["fn"] + 1
            slot_idx += 1

        full_ready = True
        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            if gold.get(slot) is None:
                full_ready = False
                break
            slot_idx += 1

        if full_ready:
            full_support += 1
            full_same = True
            slot_idx = 0
            while slot_idx < len(slots):
                slot = slots[slot_idx]
                if pred_norm.get(slot) != gold.get(slot):
                    full_same = False
                    break
                slot_idx += 1
            if full_same:
                full_hit += 1
            else:
                row_bad = True

        if row_bad and len(miss_rows) < 30:
            miss_rows.append(
                {
                    "idx": idx,
                    "text": text,
                    "gold": gold,
                    "pred": pred_norm,
                    "error": fail_name,
                }
            )

        now_count = idx + 1

        slot_metric = {}
        micro_tp = 0
        micro_fp = 0
        micro_fn = 0
        macro_p_sum = 0.0
        macro_r_sum = 0.0
        macro_f_sum = 0.0
        macro_n = 0

        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            st = slot_stat[slot]
            support = st["support"]
            correct = st["correct"]
            tp = st["tp"]
            fp = st["fp"]
            fn = st["fn"]

            acc = 0.0
            if support > 0:
                acc = correct / support

            p = 0.0
            r = 0.0
            f1 = 0.0
            if tp + fp > 0:
                p = tp / (tp + fp)
            if tp + fn > 0:
                r = tp / (tp + fn)
            if p + r > 0:
                f1 = 2 * p * r / (p + r)

            slot_metric[slot] = {
                "support": support,
                "correct": correct,
                "accuracy": acc,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": p,
                "recall": r,
                "f1": f1,
            }

            micro_tp += tp
            micro_fp += fp
            micro_fn += fn
            macro_p_sum += p
            macro_r_sum += r
            macro_f_sum += f1
            macro_n += 1
            slot_idx += 1

        micro_p = 0.0
        micro_r = 0.0
        micro_f1 = 0.0
        if micro_tp + micro_fp > 0:
            micro_p = micro_tp / (micro_tp + micro_fp)
        if micro_tp + micro_fn > 0:
            micro_r = micro_tp / (micro_tp + micro_fn)
        if micro_p + micro_r > 0:
            micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r)

        macro_p = 0.0
        macro_r = 0.0
        macro_f1 = 0.0
        if macro_n > 0:
            macro_p = macro_p_sum / macro_n
            macro_r = macro_r_sum / macro_n
            macro_f1 = macro_f_sum / macro_n

        full_acc = 0.0
        if full_support > 0:
            full_acc = full_hit / full_support

        coverage = {}
        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            cov_cnt = slot_cov[slot]
            cov_rate = 0.0
            if now_count > 0:
                cov_rate = cov_cnt / now_count
            coverage[slot] = {"count": cov_cnt, "rate": cov_rate}
            slot_idx += 1

        lines = []
        lines.append("# LangGraph OpenAI NER Evaluation")
        lines.append("")
        lines.append("## Run")
        lines.append("")
        lines.append("- Path: `predict_crf_bert` -> `predict_ner` (OpenAI json_schema)")
        lines.append(f"- Status: `running`")
        lines.append(f"- Processed: `{now_count}/{len(rows)}`")
        lines.append(f"- Model: `{os.getenv('NER_MODEL_NAME', '')}`")
        lines.append(f"- Time: `{run_time}`")
        lines.append(f"- Failed calls: `{call_fail}`")
        lines.append("")
        lines.append("## Coverage (Gold From Raw Text Rules)")
        lines.append("")
        lines.append("| Slot | Covered | Coverage |")
        lines.append("| --- | ---: | ---: |")
        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            cov_data = coverage[slot]
            cov_cnt = cov_data["count"]
            cov_rate = cov_data["rate"] * 100
            lines.append(f"| {slot} | {cov_cnt} | {cov_rate:.2f}% |")
            slot_idx += 1
        full_rate = 0.0
        if now_count > 0:
            full_rate = full_support / now_count
        lines.append("")
        lines.append(f"- Fully covered samples (4 slots): `{full_support}` / `{now_count}` ({full_rate*100:.2f}%)")
        lines.append("")
        lines.append("## Slot Exact Accuracy")
        lines.append("")
        lines.append("| Slot | Support | Correct | Accuracy |")
        lines.append("| --- | ---: | ---: | ---: |")
        slot_idx = 0
        while slot_idx < len(slots):
            slot = slots[slot_idx]
            st = slot_metric[slot]
            lines.append(
                f"| {slot} | {st['support']} | {st['correct']} | {st['accuracy']*100:.2f}% |"
            )
            slot_idx += 1
        lines.append("")
        lines.append("## Micro / Macro (Slot Value)")
        lines.append("")
        lines.append("| Type | Precision | Recall | F1 |")
        lines.append("| --- | ---: | ---: | ---: |")
        lines.append(f"| Micro | {micro_p:.6f} | {micro_r:.6f} | {micro_f1:.6f} |")
        lines.append(f"| Macro | {macro_p:.6f} | {macro_r:.6f} | {macro_f1:.6f} |")
        lines.append("")
        lines.append("## Sentence Exact Match")
        lines.append("")
        lines.append(f"- Exact Match on fully covered samples: `{full_hit}` / `{full_support}` ({full_acc*100:.2f}%)")
        lines.append("")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).strip() + "\n")

        idx += 1

    slot_metric = {}
    micro_tp = 0
    micro_fp = 0
    micro_fn = 0
    macro_p_sum = 0.0
    macro_r_sum = 0.0
    macro_f_sum = 0.0
    macro_n = 0

    slot_idx = 0
    while slot_idx < len(slots):
        slot = slots[slot_idx]
        st = slot_stat[slot]
        support = st["support"]
        correct = st["correct"]
        tp = st["tp"]
        fp = st["fp"]
        fn = st["fn"]

        acc = 0.0
        if support > 0:
            acc = correct / support

        p = 0.0
        r = 0.0
        f1 = 0.0
        if tp + fp > 0:
            p = tp / (tp + fp)
        if tp + fn > 0:
            r = tp / (tp + fn)
        if p + r > 0:
            f1 = 2 * p * r / (p + r)

        slot_metric[slot] = {
            "support": support,
            "correct": correct,
            "accuracy": acc,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": p,
            "recall": r,
            "f1": f1,
        }

        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        macro_p_sum += p
        macro_r_sum += r
        macro_f_sum += f1
        macro_n += 1
        slot_idx += 1

    micro_p = 0.0
    micro_r = 0.0
    micro_f1 = 0.0
    if micro_tp + micro_fp > 0:
        micro_p = micro_tp / (micro_tp + micro_fp)
    if micro_tp + micro_fn > 0:
        micro_r = micro_tp / (micro_tp + micro_fn)
    if micro_p + micro_r > 0:
        micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r)

    macro_p = 0.0
    macro_r = 0.0
    macro_f1 = 0.0
    if macro_n > 0:
        macro_p = macro_p_sum / macro_n
        macro_r = macro_r_sum / macro_n
        macro_f1 = macro_f_sum / macro_n

    full_acc = 0.0
    if full_support > 0:
        full_acc = full_hit / full_support

    total_count = len(rows)
    coverage = {}
    slot_idx = 0
    while slot_idx < len(slots):
        slot = slots[slot_idx]
        cov_cnt = slot_cov[slot]
        cov_rate = 0.0
        if total_count > 0:
            cov_rate = cov_cnt / total_count
        coverage[slot] = {"count": cov_cnt, "rate": cov_rate}
        slot_idx += 1

    lines = []
    lines.append("# LangGraph OpenAI NER Evaluation")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append("- Path: `predict_crf_bert` -> `predict_ner` (OpenAI json_schema)")
    lines.append(f"- Model: `{os.getenv('NER_MODEL_NAME', '')}`")
    lines.append(f"- Time: `{run_time}`")
    lines.append(f"- Total samples: `{total_count}`")
    lines.append(f"- Failed calls: `{call_fail}`")
    lines.append("")
    lines.append("## Coverage (Gold From Raw Text Rules)")
    lines.append("")
    lines.append("| Slot | Covered | Coverage |")
    lines.append("| --- | ---: | ---: |")
    slot_idx = 0
    while slot_idx < len(slots):
        slot = slots[slot_idx]
        cov_data = coverage[slot]
        cov_cnt = cov_data["count"]
        cov_rate = cov_data["rate"] * 100
        lines.append(f"| {slot} | {cov_cnt} | {cov_rate:.2f}% |")
        slot_idx += 1
    full_rate = 0.0
    if total_count > 0:
        full_rate = full_support / total_count
    lines.append("")
    lines.append(f"- Fully covered samples (4 slots): `{full_support}` / `{total_count}` ({full_rate*100:.2f}%)")
    lines.append("")
    lines.append("## Slot Exact Accuracy")
    lines.append("")
    lines.append("| Slot | Support | Correct | Accuracy |")
    lines.append("| --- | ---: | ---: | ---: |")
    slot_idx = 0
    while slot_idx < len(slots):
        slot = slots[slot_idx]
        st = slot_metric[slot]
        lines.append(
            f"| {slot} | {st['support']} | {st['correct']} | {st['accuracy']*100:.2f}% |"
        )
        slot_idx += 1
    lines.append("")
    lines.append("## Micro / Macro (Slot Value)")
    lines.append("")
    lines.append("| Type | Precision | Recall | F1 |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append(f"| Micro | {micro_p:.6f} | {micro_r:.6f} | {micro_f1:.6f} |")
    lines.append(f"| Macro | {macro_p:.6f} | {macro_r:.6f} | {macro_f1:.6f} |")
    lines.append("")
    lines.append("## Sentence Exact Match")
    lines.append("")
    lines.append(f"- Exact Match on fully covered samples: `{full_hit}` / `{full_support}` ({full_acc*100:.2f}%)")
    lines.append("")
    lines.append("## Error Samples (up to 30)")
    lines.append("")
    if not miss_rows:
        lines.append("- No mismatch")
    else:
        miss_idx = 0
        while miss_idx < len(miss_rows):
            row_data = miss_rows[miss_idx]
            lines.append(f"### idx={row_data['idx']}")
            lines.append(f"- text: {row_data['text']}")
            lines.append(f"- gold: `{json.dumps(row_data['gold'], ensure_ascii=False)}`")
            lines.append(f"- pred: `{json.dumps(row_data['pred'], ensure_ascii=False)}`")
            if row_data["error"]:
                lines.append(f"- error: `{row_data['error']}`")
            lines.append("")
            miss_idx += 1

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")

    result = {
        "time": run_time,
        "model": os.getenv("NER_MODEL_NAME", ""),
        "count": total_count,
        "fail": call_fail,
        "coverage": coverage,
        "slot_metric": slot_metric,
        "micro": {"precision": micro_p, "recall": micro_r, "f1": micro_f1},
        "macro": {"precision": macro_p, "recall": macro_r, "f1": macro_f1},
        "sent_exact": {"hit": full_hit, "support": full_support, "acc": full_acc},
        "out_path": out_path,
    }
    return result
