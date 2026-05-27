import json
import os
import requests
import pandas as pd
from pydub import AudioSegment
import io
import csv

filtered_folder = "filtered_transcripts_json"
output_folder = "audio_segments"
checkpoint_file = "checkpoint.json"
manifest_file = "manifest.csv"

os.makedirs(output_folder, exist_ok=True)

def load_manifest(path="corrected_output.xlsx"):
    df = pd.read_excel(path)
    manifest = {}
    recording_id_count = {}

    for _, row in df.iterrows():
        recording_id = str(row["recording_id"])
        count = recording_id_count.get(recording_id, 0)

        key = recording_id if count == 0 else f"{recording_id}_{count}"
        transcript_name = (
            f"{recording_id}_transcription.json" if count == 0
            else f"{recording_id}_transcription_{count}.json"
        )

        recording_id_count[recording_id] = count + 1

        manifest[key] = {
            "audio_url": row["rec_url_gcp"],
            "recording_id": recording_id,
            "transcript_filename": transcript_name
        }

    return manifest

def load_checkpoint():
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            return json.load(f)
    return {"completed": [], "failed": []}

def save_checkpoint(checkpoint):
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f, indent=2)

def download_audio(url):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return io.BytesIO(response.content)

def init_manifest():
    if not os.path.exists(manifest_file):
        with open(manifest_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "audio_path", "text", "duration",
                "user_id", "recording_id", "segment_index"
            ])

def append_manifest(rows):
    with open(manifest_file, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

def main():
    url_map = load_manifest()
    checkpoint = load_checkpoint()
    init_manifest()

    completed = set(checkpoint["completed"])
    failed = checkpoint["failed"]
    total = len(url_map)

    for idx, (recording_id, info) in enumerate(url_map.items()):
        if recording_id in completed:
            print(f"[{idx+1}/{total}] Skipping {recording_id}")
            continue

        transcript_path = os.path.join(
            filtered_folder,
            info["transcript_filename"]
        )

        if not os.path.exists(transcript_path):
            print(f"[{idx+1}/{total}] No transcript: {recording_id}")
            failed.append(recording_id)
            save_checkpoint({"completed": list(completed), "failed": failed})
            continue

        with open(transcript_path, "r", encoding="utf-8") as f:
            segments = json.load(f)

        print(f"[{idx+1}/{total}] {recording_id} | {len(segments)} segments")

        try:
            audio_bytes = download_audio(info["audio_url"])

            # Load ONCE — fix for previous bug
            audio_bytes.seek(0)
            audio = AudioSegment.from_file(audio_bytes)

            manifest_rows = []
            seg_success = 0

            for seg_idx, seg in enumerate(segments):
                try:
                    start = float(seg["start"])
                    end = float(seg["end"])
                    text = seg["text"].strip()
                    duration = round(end - start, 3)

                    seg_filename = f"{recording_id}_{seg_idx:04d}.wav"
                    seg_path = os.path.join(output_folder, seg_filename)

                    sliced = audio[int(start * 1000):int(end * 1000)]
                    sliced = sliced.set_frame_rate(16000).set_channels(1)
                    sliced.export(seg_path, format="wav")

                    manifest_rows.append([
                        seg_path, text, duration,
                        recording_id, info["recording_id"], seg_idx
                    ])
                    seg_success += 1

                except Exception as e:
                    print(f"  Segment {seg_idx} failed: {type(e).__name__}: {e}")
                    continue

            append_manifest(manifest_rows)
            completed.add(recording_id)
            save_checkpoint({"completed": list(completed), "failed": failed})
            print(f"  Saved {seg_success}/{len(segments)} segments")

        except Exception as e:
            print(f"  File failed: {type(e).__name__}: {e}")
            failed.append(recording_id)
            save_checkpoint({"completed": list(completed), "failed": failed})

if __name__ == "__main__":
    main()