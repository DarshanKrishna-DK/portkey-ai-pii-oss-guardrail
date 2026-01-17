# PII Guardrail System

A production-ready PII (Personally Identifiable Information) detection guardrail using fine-tuned Llama 3.2-1B, designed for Portkey webhook integration.

## Features

- **Indian PII Support**: Aadhaar (12-digit UID), PAN (Tax ID)
- **General PII Detection**: Email, Phone, Names, SSN, Credit Cards
- **Risk-Aware Classification**: HIGH/MEDIUM/LOW risk levels with confidence scoring
- **Sub-100ms Inference**: Optimized with 4-bit quantization
- **Grounding Validation**: Prevents hallucination by verifying entities exist in input
- **Portkey Integration**: Webhook-compatible with fallback support
- **Parallel Data Generation**: 4-5x faster training data creation

## Project Structure

```
OSS-Guardrail/
├── api/                              # FastAPI webhook server
│   ├── main.py                       # FastAPI app entry point
│   ├── model.py                      # Model loading & inference
│   ├── schemas.py                    # Pydantic request/response models
│   └── actions.py                    # BLOCK/FLAG/ALLOW logic
│
├── data/                             # Training data (upload to Google Drive)
│   ├── train_v2.jsonl                # Training samples
│   └── eval_v2.jsonl                 # Evaluation samples
│
├── data_gen/                         # Data generation utilities
│   ├── augmentation.py               # Noise, typos, character confusion
│   ├── adversarial_templates.py      # Evasion, OCR, dangerous negatives
│   └── robust_generator.py           # Random data generator
│
├── training/                         # Training scripts
│   ├── pii_guardrail.ipynb           # Google Colab training notebook
│   ├── generate_with_portkey.py      # Gemini data generator (Portkey)
│   └── generate_robust_data_v2.py    # Random data generator (fallback)
│
├── requirements.txt
├── env.example
└── README.md
```

---

## Step-by-Step Guide

### Step 1: Setup Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/OSS-Guardrail.git
cd OSS-Guardrail

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install portkey-ai
```

---

### Step 2: Get Portkey API Key

1. Go to **[Portkey Dashboard](https://app.portkey.ai/)**
2. Log in with your hackathon credentials
3. Navigate to **Settings → API Keys**
4. Copy your API key

**Available Models (Portkey format: `@provider/model`):**
| Model | Description |
|-------|-------------|
| `@openai/gpt-4o-mini` | Fast, cheap, good quality (recommended) |
| `@openai/gpt-4o` | Best OpenAI quality |
| `@openai/o4-mini` | Reasoning model |
| `@google/gemini-1.5-flash` | Fast Gemini |
| `@google/gemini-1.5-pro` | Best Gemini |
| `@anthropic/claude-3-haiku` | Fast Claude |

---

### Step 3: Generate Training Data

#### Option A: Using Portkey + LLM (Recommended for quality)

```powershell
# Set your Portkey API key
$env:PORTKEY_API_KEY = "your_portkey_api_key_here"

# Generate 10,000 samples with parallel processing (5 workers by default)
python training/generate_with_portkey.py --samples 10000 --output data

# Use more workers for faster generation (careful with rate limits)
python training/generate_with_portkey.py --samples 10000 --workers 10

# Use fewer workers if hitting rate limits
python training/generate_with_portkey.py --samples 10000 --workers 3

# Or specify a different model
python training/generate_with_portkey.py --samples 10000 --model "@openai/gpt-4o"

# If interrupted, resume from checkpoint
python training/generate_with_portkey.py --samples 10000 --output data --resume

# Use sequential mode (slower but safer for rate limits)
python training/generate_with_portkey.py --samples 10000 --sequential
```

**Estimated time:** ~8-10 minutes with 5 workers (parallel), ~30 minutes sequential

#### Option B: Using Random Generation (Faster, no API needed)

```powershell
python training/generate_robust_data_v2.py --samples 10000 --output data
```

**Estimated time:** ~10 seconds

---

### Step 4: Upload Data to Google Drive

1. Open **Google Drive** in your browser
2. Create folder: `My Drive/pii-guardrail-model/`
3. Upload these files:
   - `data/train_v2.jsonl`
   - `data/eval_v2.jsonl`

Your folder should look like:
```
My Drive/
└── pii-guardrail-model/
    ├── train_v2.jsonl    ← Upload this
    ├── eval_v2.jsonl     ← Upload this
    └── output_v2/        ← Model saves here (created automatically)
```

---

### Step 5: Train the Model in Google Colab

1. Go to **[Google Colab](https://colab.research.google.com/)**
2. Upload `training/pii_guardrail.ipynb`
3. **Enable GPU runtime:**
   - Click `Runtime` → `Change runtime type`
   - Select `T4 GPU` (free tier) or `A100` (Colab Pro)
4. **Run all cells in order**

| Cell | What it does | Time |
|------|--------------|------|
| 0 | Markdown intro | - |
| 1 | Install Unsloth | 2-3 min |
| 2 | Mount Google Drive | 30 sec |
| 3 | Configuration | instant |
| 4 | Load risk-aware system prompt | instant |
| 5 | Load training data | 1 min |
| 6 | Format datasets | 1 min |
| 7 | Load Llama 3.2-1B with LoRA | 2-3 min |
| 8 | Training configuration | instant |
| 9 | **Train the model** | 30-60 min |
| 10 | Evaluation functions | instant |
| 11 | Evaluate on test set | 5-10 min |
| 12 | Test negative samples | 2 min |
| 13 | Test positive samples | 1 min |
| 14 | Test risk-based classification | 2 min |
| 15 | Production guardrail class | instant |
| 16 | Save model for deployment | 2-3 min |
| 17 | Summary | instant |

---

### Step 6: Check Training Results

After Cell 11, you should see metrics like:

```
Precision: > 0.90
Recall:    > 0.90
F1 Score:  > 0.90
False Positive Rate: < 10%
```

In Cell 12 (negative tests), look for:
- `[PASS]` - Model correctly said no PII ✅
- `[FAIL]` - False positive ❌ (should be minimal)

In Cell 14 (risk classification), check that:
- HIGH RISK inputs get `confidence: 9-10`
- MEDIUM RISK inputs get `confidence: 6-8`
- LOW RISK inputs are NOT flagged or have low confidence

---

### Step 7: Download Trained Model

After Cell 16, your model is saved to Google Drive:
- `My Drive/pii-guardrail-model/lora_adapters/` - LoRA weights
- `My Drive/pii-guardrail-model/merged_16bit/` - Full merged model
- `My Drive/pii-guardrail-model/model.gguf` - GGUF for llama.cpp (optional)

Download from Google Drive or use:
```python
from google.colab import files
import shutil
shutil.make_archive('/content/pii-guardrail-model', 'zip', '/content/drive/MyDrive/pii-guardrail-model')
files.download('/content/pii-guardrail-model.zip')
```

---

### Step 8: Run the API Server

```bash
# Set environment variables
cp env.example .env
# Edit .env with your configuration

# Start the server
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## Output Format

**When PII is detected (HIGH RISK):**
```json
{
  "flagged": true,
  "confidence": 10,
  "entities": [
    {
      "type": "IN_AADHAAR",
      "value": "2345 6789 0123",
      "start": 17,
      "end": 31
    }
  ],
  "reason": "HIGH RISK: Detected Aadhaar with explicit context",
  "risk_level": "HIGH"
}
```

**When no PII is found:**
```json
{
  "flagged": false,
  "confidence": 10,
  "entities": [],
  "reason": "No PII detected in text",
  "risk_level": "LOW"
}
```

### Risk Levels

| Risk Level | Confidence | Examples |
|------------|------------|----------|
| **HIGH** | 9-10 | Email, Phone, Aadhaar, PAN, SSN, Credit Card |
| **MEDIUM** | 6-8 | Full name + location, Employee IDs |
| **LOW** | 1-5 | First name only, public figures, fictional characters |

---

## Entity Types & Severity

| Entity | Type | Severity | Action |
|--------|------|----------|--------|
| Aadhaar | `IN_AADHAAR` | 10 | BLOCK |
| PAN | `IN_PAN` | 9 | BLOCK |
| SSN | `US_SSN` | 10 | BLOCK |
| Credit Card | `CREDIT_CARD` | 9 | BLOCK |
| Email | `EMAIL_ADDRESS` | 3 | FLAG |
| Phone | `PHONE_NUMBER` | 3 | FLAG |
| Name | `PERSON` | 2 | FLAG |

---

## API Endpoints

### `POST /guardrail/pii`

Portkey webhook endpoint for PII detection.

**Request** (from Portkey):
```json
{
  "request": {
    "messages": [
      {"role": "user", "content": "My Aadhaar is 2345 6789 0123"}
    ]
  }
}
```

**Response**:
```json
{
  "verdict": "block",
  "data": {
    "flagged": true,
    "entities": [
      {"type": "IN_AADHAAR", "value": "2345 6789 0123", "start": 14, "end": 28}
    ],
    "confidence": 9,
    "severity": 10,
    "reason": "BLOCKED: Critical PII detected - 1 Aadhaar"
  }
}
```

### `POST /detect`

Direct PII detection endpoint.

**Request**:
```json
{
  "text": "Contact me at user@example.com"
}
```

**Response**:
```json
{
  "result": {
    "flagged": true,
    "entities": [
      {"type": "EMAIL_ADDRESS", "value": "user@example.com", "start": 14, "end": 30}
    ],
    "confidence": 9,
    "severity": 3,
    "reason": "Detected 1 Email Address"
  },
  "processing_time_ms": 45.2,
  "model_version": "1.0.0"
}
```

---

## Portkey Integration

### Webhook Configuration

In Portkey UI, configure your guardrail:

```json
{
  "webhook_url": "https://your-api.com/guardrail/pii",
  "timeout": 3000,
  "headers": {
    "Authorization": "Bearer YOUR_API_KEY"
  }
}
```

### Fallback Strategy

```json
{
  "strategy": {
    "mode": "fallback",
    "on_status_codes": [246, 446]
  },
  "targets": [
    {"virtual_key": "gpt4o-key"}
  ]
}
```

---

## Troubleshooting

### "File not found" error in Colab Cell 5
- Make sure you uploaded `train_v2.jsonl` and `eval_v2.jsonl` to `My Drive/pii-guardrail-model/`

### Model hallucinating (false positives)
- The grounding validation in Cell 14 catches and rejects hallucinations
- If raw FP rate is high but validated rate is low, the safety net is working

### Out of memory in Colab
- Reduce batch size in Cell 7: change `per_device_train_batch_size` to 1
- Use gradient accumulation: `gradient_accumulation_steps=4`

### Portkey API errors
- Check your API key is set correctly
- Try a different model: `--model "@openai/gpt-4o-mini"`
- Try with `--resume` flag if generation was interrupted

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Inference Latency | < 100ms | With 4-bit quantization |
| Precision | > 95% | All entity types |
| Recall | > 95% | All entity types |
| False Positive Rate | < 5% | Critical for production |

---

## License

MIT License - See LICENSE file for details.

---

## Acknowledgments

- [Unsloth](https://github.com/unslothai/unsloth) - Optimized fine-tuning
- [Portkey](https://portkey.ai) - AI Gateway integration
