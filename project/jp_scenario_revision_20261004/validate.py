from pathlib import Path
import hashlib
import json
import re

root = Path(__file__).resolve().parents[2]
here = Path(__file__).resolve().parent
files = [
    "countries/JP/model/JP_milp_formulation.md",
    "countries/JP/model/JP_activation_data_spec_M4.md",
    "countries/JP/README.md",
    "countries/JP/research/model_handoff.md",
    "countries/JP/research/README.md",
]
read = lambda p: p.read_text(encoding="utf-8-sig")
main = read(root / files[0])
old = read(here / "before" / files[0].replace("/", "__"))
checks = {}
checks["section13_unchanged"] = (
    main[main.index("## 13."):main.index("## 14.")].strip()
    == old[old.index("## 13."):].strip()
)
for scenario in ["LV_FCR", "HV_SPOT_FCR", "HV_SPOT_S1_T1"]:
    checks["scenario_" + scenario] = all(scenario in read(root / f) for f in files[:2])
scope = read(here / "user_scope.md")
checks["user_clarifications_recorded"] = all(
    s in scope for s in ["只忽略激活收入", "两个产品容量允许不同并由模型优化", "用户已回复确认"]
)
checks["joint_response_not_assumed_calibrated"] = "不是已闭合可运行模型" in main
checks["no_automatic_EDC_reallocation"] = "不得因此把" in main and "$w_{T1}$设为1" in main
checks["no_scope_optimality_claim"] = "尚未证明是所有可行组合中的最优" in main
checks["review_scope_bounded"] = "此次为范围和数学设计修订，未独立审核" in main
checks["LV_physics_retained"] = "不得据此令" in main and "删除激活能量" in main
checks["exact_max_formulation_examples"] = True
samples = 0
for qs in [0, 0.001, 1, 3, 5]:
    for qt in [0, 0.001, 1, 3, 5]:
        feasible = []
        for z in [0, 1]:
            lo = max(qs, qt)
            hi = min(qs + 5 * (1-z), qt + 5 * z)
            if lo <= hi + 1e-12:
                feasible.append((lo, hi))
        checks["exact_max_formulation_examples"] &= bool(feasible) and all(
            abs(lo-max(qs, qt)) < 1e-12 and abs(hi-lo) < 1e-12 for lo, hi in feasible
        )
        samples += 1
link_checks = []
for rel in files + ["project/jp_scenario_revision_20261004/change_log.md"]:
    p = root / rel
    current = read(p)
    if rel in files:
        previous = read(here / "before" / rel.replace("/", "__"))
        old_links = set(re.findall(r"\]\(([^)]+)\)", previous))
    else:
        old_links = set()
    for target in set(re.findall(r"\]\(([^)]+)\)", current)) - old_links:
        if "://" in target or target.startswith("#"):
            continue
        link_checks.append({"file": rel, "target": target,
                            "exists": (p.parent / target.split("#")[0]).resolve().exists()})
checks["new_local_link_targets_exist"] = all(x["exists"] for x in link_checks)
hashes = []
for rel in files:
    p = root / rel
    before = here / "before" / rel.replace("/", "__")
    hashes.append({"path": rel,
                   "before_sha256": hashlib.sha256(before.read_bytes()).hexdigest(),
                   "after_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
result = {
    "date": "2026-10-04",
    "scope": "document consistency and illustrative max linearization only; no solver or independent review",
    "passed": all(checks.values()),
    "checks": checks,
    "max_linearization_capacity_pairs": samples,
    "new_local_links": link_checks,
    "hashes": hashes,
}
(here / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"passed": result["passed"], "checks": checks, "capacity_pairs": samples}, ensure_ascii=False))
raise SystemExit(0 if result["passed"] else 1)

