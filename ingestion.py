import pandas as pd
import requests
import json
import os

# =========================
# SETTINGS
# =========================
input_file = "corrected_output.xlsx"

# Column containing transcript URLs
transcript_url_col = "transcription_url_gcp"

# Folder where JSON files will be stored
output_folder = "transcripts_json"
os.makedirs(output_folder, exist_ok=True)

# =========================
# LOAD EXCEL
# =========================
df = pd.read_excel(input_file)

# =========================
# DOWNLOAD TRANSCRIPTS
# =========================
overall_segments = 0

for idx, url in enumerate(df[transcript_url_col]):

    try:

        # Download JSON transcript
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

        # Count segments
        segment_count = len(data)
        overall_segments += segment_count

        # Create filename
        filename = f"transcript_{idx + 1}.json"

        # Full save path
        filepath = os.path.join(output_folder, filename)

        # Save JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved: {filename} | Segments: {segment_count}")

    except Exception as e:

        print(f"Failed row {idx + 1}: {e}")

# =========================
# FINAL SUMMARY
# =========================
print("\n========== DONE ==========")
print("Total transcripts:", len(df))
print("Overall segments:", overall_segments)
print("Saved folder:", output_folder)