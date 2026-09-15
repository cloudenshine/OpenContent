"""Build auditable paired-result tables and a separate anonymous reader packet."""
import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    suite, execution, mapping = read("suite.json"), read("execution.json"), read("mapping.json")
    reviews = read("reviews.json")["reviews"] if (root / "reviews.json").exists() else []
    packet = ["# 匿名文章对照\n", "这些文章基于作者编写的虚构资料，不是事实报道；仅供评测，未获作者批准。A/B 标签在各题独立分配，不代表同一实验组。\n",
              "请先阅读受众、目标和资料，再判断中心意思、解释、衔接、声音及事实边界。允许平局。不要猜测生成规则。不要在提交判断前查看 mapping.json 或结果报告。\n"]
    rows = []
    for case in suite["cases"]:
        packet.extend([f"## {case['title']}\n", f"受众：{case['audience']}\n", f"目标：{case['goal']}\n", "### 资料\n"])
        packet.extend(body+"\n" for body in case["sources"])
        for label in ("A", "B"):
            path = root / "blind" / case["id"] / (label + ".md")
            packet.extend([f"### 文章 {label}\n", path.read_text(encoding="utf-8") if path.exists() else "生成失败，无可评审正文。", "\n"])
            rows.append({"reviewer": "", "case": case["id"], "label": label, "clarity_1_5": "", "explanation_1_5": "",
                         "flow_1_5": "", "voice_1_5": "", "unsupported_quote_and_reason": "", "priority_fix": "", "pair_winner_A_B_tie": "", "reason_with_excerpt": ""})
    (root / "blind" / "reader-packet.md").write_text("\n".join(packet), encoding="utf-8")
    # Never overwrite a form that a reader may already have filled out.
    form = root / "blind" / "human-review.csv"
    if not form.exists():
        with form.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {"human_review": "PENDING", "model_identities": [], "pairs": []}
    identities = {json.dumps(r.get("runtime", {}), sort_keys=True) for r in execution["runs"]}
    summary["model_identities"] = [json.loads(i) for i in identities]
    summary["same_observed_generation_model"] = len(identities) == 1 and bool(summary["model_identities"][0].get("model"))
    for case in suite["cases"]:
        runs = [r for r in execution["runs"] if r["case"] == case["id"]]
        judgments = [r for r in reviews if r["case"] == case["id"] and r["status"] == "REVIEWED"]
        votes = [mapping[case["id"]].get(r["result"]["winner"], "tie") for r in judgments]
        summary["pairs"].append({"case": case["id"], "runs": [{**r, "arm": mapping[case["id"]][r["label"]]} for r in runs],
                                 "votes": votes, "order_consistent": len(votes) == 2 and votes[0] == votes[1],
                                 "judgments": judgments})
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k != "pairs"}, ensure_ascii=False))
    for pair in summary["pairs"]:
        print(json.dumps({k:v for k,v in pair.items() if k not in ("runs", "judgments")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
