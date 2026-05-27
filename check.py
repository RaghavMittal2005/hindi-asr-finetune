import json
import os

filtered_folder = "filtered_transcripts_json"
total = 0
empty_files = []

for f in os.listdir(filtered_folder):
    path = os.path.join(filtered_folder, f)
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    total += len(data)
    if len(data) == 0:
        empty_files.append(f)

print(f"Total segments across all files: {total}")
print(f"Files with 0 segments: {len(empty_files)}")
for f in empty_files:
    print(f"  {f}")