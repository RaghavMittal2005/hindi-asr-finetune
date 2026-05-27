# Hindi ASR Fine-Tuning: Whisper-Small

Fine-tuning OpenAI's Whisper-small model on a custom conversational Hindi dataset, evaluated against the FLEURS Hindi test benchmark.

---

## Project Overview

This project fine-tunes `openai/whisper-small` on ~10 hours of conversational Hindi speech data. The goal is to improve transcription accuracy on Hindi audio compared to the pretrained baseline, measured using Word Error Rate (WER) on the FLEURS `hi_in` test split.

---

## Dataset

- **Source**: Custom Hindi ASR dataset (~104 speakers, ~10 hours total)
- **Format**: Audio recordings (WAV) paired with JSON transcriptions
- **Content**: Conversational Hindi — topics include college life, movies, music, books
- **Structure**: Each transcription JSON contains timestamped segments with `start`, `end`, and `text` fields

---

## Pipeline

### 1. Data Collection & URL Handling

Audio and transcription files were hosted on Google Cloud Storage
Transcription JSONs were downloaded first (lightweight) to audit segment quality before downloading audio.

---

### 2. Transcript Filtering

Each transcription JSON was filtered for quality:

- **Duration filter**: Segments shorter than 1.5 seconds removed (too short for reliable ASR training)
- **Duration cap**: Segments longer than 29 seconds removed (Whisper's processing limit)
- **Filler word removal**: Hindi-specific fillers (`अ`, `उम`, `उह`, `हम्म` etc.) stripped from transcripts. Meaningful conversational markers (`हां`, `हाँ`, `अच्छा`) retained.
- **Empty segment removal**: Segments empty after cleaning dropped entirely
- **Redacted content**: Segments marked as redacted removed

**Results**:
| Stage | Segments |
|---|---|
| Raw | 5,941 |
| After filtering | 4,469 |
| Removed | 1,472 (24.8%) |

Primary removal reason: duration < 1.5s (87% of removed segments).

---

### 3. Audio Slicing

Full audio files (500–1150 seconds each) were downloaded one at a time and sliced into individual segments using timestamps from the filtered transcription JSONs.

- **Tool**: `pydub`
- **Output format**: 16kHz mono WAV (Whisper's required format)
- **Checkpointing**: Progress saved after each file to allow safe resumption on failure
- **Manifest**: `manifest.csv` generated mapping each WAV segment to its cleaned transcript

**Final dataset**: 4,469 WAV segments, ~2.2GB total

---

### 4. Text Normalisation

Applied to both training transcripts and FLEURS references before WER computation:

```python
def normalise_hindi(text):
    text = text.strip()
    text = re.sub(r'[\"\',\-!?;:()\.\[\]{}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
```

Devanagari danda (`।`) retained as Whisper may produce it naturally.

---

### 5. Train / Validation Split

- **Split**: 95% train / 5% validation (`sklearn` stratified split, `random_state=42`)
- **Train**: 4,245 segments
- **Validation**: 224 segments

---

### 6. Model & Processor

- **Base model**: `openai/whisper-small` (244M parameters)
- **Processor**: `WhisperProcessor` with `language=Hindi`, `task=transcribe`
- **Feature extraction**: Log-mel spectrograms (80 mel bins, 16kHz)
- **Tokenisation**: Whisper's multilingual tokenizer with Hindi forced decoder IDs

---

### 7. Data Loading

A custom PyTorch `Dataset` class was used to load and preprocess audio on-the-fly during training, bypassing HuggingFace's `datasets` audio decoding pipeline which caused compatibility issues with `torchcodec` in the training environment:

```python
class WhisperDataset(torch.utils.data.Dataset):
    def __getitem__(self, idx):
        audio_array, sr = sf.read(row["abs_path"])
        # resample if needed, convert to mono
        input_features = feature_extractor(audio_array, sampling_rate=16000).input_features[0]
        labels = tokenizer(row["text"]).input_ids
        return {"input_features": input_features, "labels": labels}
```

---

### 8. Training Configuration

| Parameter | Value |
|---|---|
| Base model | `openai/whisper-small` |
| Optimizer | AdamW |
| Learning rate | 1e-5 |
| Warmup steps | 50 |
| Max steps | 500 |
| Train batch size | 8 per device |
| Gradient accumulation | 4 steps (effective batch = 64 with DataParallel) |
| Mixed precision | fp16 |
| Gradient checkpointing | Enabled |
| Eval strategy | Every 100 steps |
| Best model metric | WER (lower is better) |
| Hardware | Kaggle T4 × 2 (DataParallel) |

---

### 9. Training Dynamics

| Step | Train Loss | Val Loss | Val WER |
|---|---|---|---|
| 100 | — | — | — |
| 200 | 1.94 | 0.327 | 35.02% |
| 400 | 0.89 | 0.357 | **31.96%** |
| 600 | 0.37 | 0.423 | 33.91% |
| 800 | 0.13 | 0.490 | 35.32% |
| 1000 | 0.05 | 0.531 | 35.31% |

Best checkpoint at **step 400**. Overfitting observed beyond step 400 — validation loss increases while training loss continues to fall, consistent with a small dataset fine-tuning scenario. `load_best_model_at_end=True` ensured the step 400 checkpoint was used for evaluation.

---

### 10. Evaluation

Both baseline and fine-tuned models evaluated on the **FLEURS `hi_in` test split** using direct `generate()` inference (not pipeline) to avoid internal chunking conflicts:

```python
predicted_ids = model.generate(
    input_features,
    attention_mask=attention_mask,
    forced_decoder_ids=forced_decoder_ids,  # language=Hindi, task=transcribe
)
```

---

## Results

| Model | Eval Set | Language | WER (%) | Δ WER (pp) | Relative Δ |
|---|---|---|---|---|---|
| Baseline `whisper-small` (pretrained) | FLEURS Hindi test | Hindi (hi) | 82.51% | — | — |
| Fine-tuned `whisper-small` (ours) | FLEURS Hindi test | Hindi (hi) | **40.23%** | -42.28 | **-51.2%** |

**Absolute WER reduction**: 42.28 percentage points  
**Relative WER reduction**: 51.2%

---

## Observations

- The high baseline WER (82.51%) reflects the domain gap between FLEURS (formal read speech) and Whisper-small's general multilingual pretraining on Hindi
- Fine-tuning on conversational Hindi significantly improved FLEURS performance despite the domain mismatch between training data (conversational) and test data (read speech)
- Overfitting at ~400 steps suggests the dataset size (~4,200 samples) is the primary bottleneck — more data would likely push WER below 30%
- Larger variants (`whisper-medium`, `whisper-large`) would be expected to yield further improvements

---
