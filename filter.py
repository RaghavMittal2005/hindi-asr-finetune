import json
import os
import re
import pandas as pd

input_folder = "transcripts_json"
filtered_folder = "filtered_transcripts_json"
os.makedirs(filtered_folder, exist_ok=True)

# Load Excel for recording_id mapping
df = pd.read_excel("corrected_output.xlsx")
# index 0 = transcript_1, index 1 = transcript_2, etc.
index_to_recording_id = {
    i + 1: str(row["recording_id"])
    for i, row in df.iterrows()
}

FILLERS = {
    "अ", "उम", "उह", "आ", "ओ",
    "हम्म", "म्म", "हूं", "हूँ","REDACTED"
}

KEEP_WORDS = {
    "हां", "हाँ", "जी", "नहीं",
    "अच्छा", "ओके", "ठीक"
}

def remove_fillers(text):
    words = str(text).split()
    cleaned = []
    for word in words:
        cleaned_word = re.sub(r"[^\u0900-\u097F\w]", "", word)
        if cleaned_word in KEEP_WORDS:
            cleaned.append(word)
            continue
        if cleaned_word in FILLERS:
            continue
        cleaned.append(word)
    return re.sub(r"\s+", " ", " ".join(cleaned)).strip()

def clean_text(text):
    text = str(text).strip()
    return re.sub(r"[^\u0900-\u097F\w\s]", "", text)

def is_valid_segment(segment):
    try:
        start = float(segment.get("start", 0))
        end = float(segment.get("end", 0))
        duration = end - start

        text = remove_fillers(segment.get("text", ""))
        text = clean_text(text)
        words = text.split()

        if duration < 1.5:
            return False, text
        if duration > 29.0:
            return False, text
        if len(words) == 0:
            return False, text
        if len(words) == 1 and words[0] in FILLERS:
            return False, text

        return True, text
    except:
        return False, ""

overall_original = 0
overall_filtered = 0

# Get all transcript files sorted by index
transcript_files = sorted(
    [f for f in os.listdir(input_folder) if f.endswith(".json")],
    key=lambda x: int(x.replace("transcript_", "").replace(".json", ""))
)

for file_name in transcript_files:
    # Extract index from filename
    try:
        idx = int(file_name.replace("transcript_", "").replace(".json", ""))
    except ValueError:
        print(f"Skipping unexpected filename: {file_name}")
        continue

    recording_id = index_to_recording_id.get(idx)
    if not recording_id:
        print(f"No recording_id for index {idx}")
        continue

    input_path = os.path.join(input_folder, file_name)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        original_count = len(data)
        overall_original += original_count

        filtered_data = []
        for seg in data:
            valid, cleaned_text = is_valid_segment(seg)
            if valid:
                seg["text"] = cleaned_text
                filtered_data.append(seg)

        filtered_count = len(filtered_data)
        overall_filtered += filtered_count

        # Save as recording_id
        output_path = os.path.join(
            filtered_folder,
            f"{recording_id}_transcription.json"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)

        print(
            f"{file_name} → {recording_id}_transcription.json | "
            f"Original: {original_count} | "
            f"Filtered: {filtered_count}"
        )

    except Exception as e:
        print(f"Failed: {file_name} | {e}")

print("\n========== DONE ==========")
print("Original segments :", overall_original)
print("Filtered segments :", overall_filtered)
print("Removed segments  :", overall_original - overall_filtered)