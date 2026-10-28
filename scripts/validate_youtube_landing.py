
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "landing" / "youtube_data_api"

# Select the latest completed extraction directory
run_dir = sorted(
    path for path in LANDING.iterdir() if path.is_dir()
)[-1]

with (run_dir / "manifest.json").open(encoding="utf-8") as f:
    manifest = json.load(f)

with (run_dir / "videos.jsonl").open(encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]

ids = [record["video_id"] for record in records]
missing = manifest["missing_video_ids"]

assert len(records) == manifest["video_records"]
assert len(ids) == len(set(ids)), "Duplicate video IDs found"
assert len(ids) + len(missing) == manifest["playlist_video_ids"]
assert not (set(ids) & set(missing))

for record in records:
    assert record["video_id"] == record["payload"]["id"]
    assert record["extract_run_id"] == manifest["extract_run_id"]
    assert record["channel_id"] == manifest["channel_id"]
    assert record["ingested_at_utc"]
    assert record["source_endpoint"] == "youtube.videos.list"

print("Landing data validation PASSED")
print("Records:", len(records))
print("Duplicate IDs:", len(ids) - len(set(ids)))
print("Missing video details:", len(missing))
print("Manifest run:", manifest["extract_run_id"])
