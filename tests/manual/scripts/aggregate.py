import json
from collections import defaultdict

data = json.load(open("C:/dev/projects/aegis/tests/manual/results/comparison.json"))
groups = defaultdict(list)
for d in data:
    key = d["scenario"] + "-" + d["mode"]
    groups[key].append(d["total_tokens"])

print("=== PER-SCENARIO SAVINGS ===")
for s in ["S1", "S2", "S3", "S4"]:
    wk = [k for k in groups if k.startswith(s) and "with" in k]
    wok = [k for k in groups if k.startswith(s) and "without" in k]
    if wk and wok:
        w = groups[wk[0]]
        wo = groups[wok[0]]
        aw, awo = sum(w) / len(w), sum(wo) / len(wo)
        sav = (1 - aw / awo) * 100
        print(
            f"  {s}: WITH={aw:,.0f}t (n={len(w)}), WITHOUT={awo:,.0f}t (n={len(wo)}), {sav:+.1f}%"
        )
