"""
Fix stress_200 news map impact_strength from string to decimal.
Also recalculate manifest checksums.
"""
import json
import os
import hashlib
import glob

STRENGTH_MAP = {"low": 0.3, "medium": 0.6, "high": 0.9}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    staging_files = sorted(glob.glob("crawler/staging/stress_200/e2e_news_raw_*.json"))
    print(f"[INFO] Found {len(staging_files)} news staging files")

    fixed_staging = []
    for sf in staging_files:
        with open(sf, "r", encoding="utf-8") as f:
            data = json.load(f)

        modified = False
        for map_key in ["news_industry_maps", "news_company_maps"]:
            maps = data["payload"].get(map_key, {})
            for key, items in maps.items():
                for item in items:
                    val = item.get("impact_strength")
                    if isinstance(val, str):
                        item["impact_strength"] = STRENGTH_MAP.get(val, 0.6)
                        modified = True

        if modified:
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            fixed_staging.append(os.path.basename(sf))
            print(f"  [FIXED] {os.path.basename(sf)}")

    # Recalculate sha256 and update manifests
    manifest_dir = "ingest_center/manifests_stress_200"
    updated_manifests = []
    for sf in staging_files:
        new_sha = sha256_file(sf)
        basename = os.path.basename(sf)
        # e.g. e2e_news_raw_01.json -> stress_200_research_report_01.json
        num_part = basename.replace("e2e_news_raw_", "").replace(".json", "")
        manifest_name = f"stress_200_research_report_{num_part}.json"
        manifest_path = os.path.join(manifest_dir, manifest_name)

        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            manifest["checksum"]["staging_sha256"] = new_sha
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
                f.write("\n")
            updated_manifests.append(manifest_name)
            print(f"  [CHECKSUM] {manifest_name} -> {new_sha[:16]}...")
        else:
            print(f"  [WARN] manifest not found: {manifest_name}")

    print(f"\n[SUMMARY]")
    print(f"  Fixed staging files: {len(fixed_staging)}")
    print(f"  Updated manifests:   {len(updated_manifests)}")
    print("  Done")


if __name__ == "__main__":
    main()
