import os
import csv

wav_files = [f for f in os.listdir("audio_segments") if f.endswith(".wav")]
print(f"WAV files: {len(wav_files)}")

with open("manifest.csv", "r", encoding="utf-8") as f:
    rows = list(csv.reader(f))
print(f"Manifest rows: {len(rows) - 1}")