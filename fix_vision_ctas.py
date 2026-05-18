"""One-time migration: fix /try CTA in existing vision posts to /investors with UTM."""
import glob
import json

OLD = "thesmartpro.io/try"
NEW = "thesmartpro.io/investors?utm_source=linkedin&utm_medium=social&utm_campaign=vision"

updated = 0
for path in sorted(glob.glob("posts_history/*.json")):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("pillar") != "vision":
        continue
    post = data.get("post", "")
    if OLD not in post:
        continue
    data["post"] = post.replace(OLD, NEW)
    if "cta_url" in data:
        data["cta_url"] = data["cta_url"].replace(OLD, NEW)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Fixed: {path}")
    updated += 1

print(f"\nDone — {updated} vision post(s) updated.")
