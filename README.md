# PII Guardrail System

A production-ready PII (Personally Identifiable Information) detection guardrail using fine-tuned Llama 3.2-1B, designed for Portkey webhook integration.

## Features

- **Indian PII Support**: Aadhaar (12-digit UID), PAN (Tax ID)
- **General PII Detection**: Email, Phone, Names, SSN, Credit Cards
- **Sub-100ms Inference**: Optimized with 4-bit quantization
- **Portkey Integration**: Webhook-compatible with fallback support
- **Hybrid Actions**: BLOCK/FLAG/ALLOW based on severity thresholds

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Portkey        │────▶│  FastAPI         │────▶│  Llama 3.2-1B   │
│  Gateway        │     │  Webhook         │     │  (QLoRA)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        │                       ▼                        │
        │               ┌──────────────────┐            │
        │               │  Action Logic    │            │
        │               │  BLOCK/FLAG/ALLOW│            │
        │               └──────────────────┘            │
        │                       │                        │
        ▼                       ▼                        │
┌─────────────────┐     ┌──────────────────┐            │
│  GPT-4o         │◀────│  Fallback        │◀───────────┘
│  (Fallback)     │     │  (conf < 0.6)    │
└─────────────────┘     └──────────────────┘
```

## Project Structure

```
OSS-Guardrail/
├── data_gen/                 # Synthetic data generation
│   ├── config.py            # Entity patterns & context words
│   ├── generator.py         # Gemini-based data generator
│   ├── templates.py         # Context-rich sentence templates
│   ├── validators.py        # PII format validators
│   └── dataset_builder.py   # JSONL dataset builder
├── training/
│   └── pii_guardrail.ipynb  # Google Colab training notebook
├── api/
│   ├── main.py              # FastAPI webhook server
│   ├── model.py             # Model loading & inference
│   ├── schemas.py           # Pydantic request/response models
│   └── actions.py           # BLOCK/FLAG/ALLOW logic
├── requirements.txt
├── env.example
└── README.md
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/OSS-Guardrail.git
cd OSS-Guardrail

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install PyTorch (select appropriate CUDA version)
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Install Unsloth for optimized inference
pip install unsloth
```

### 2. Generate Training Data

```python
from data_gen import DatasetBuilder

builder = DatasetBuilder(output_dir="data", seed=42)
stats, train_path, eval_path = builder.build_dataset(
    total_samples=10000,
    eval_ratio=0.2
)
```

### 3. Train the Model (Google Colab)

1. Open `training/pii_guardrail.ipynb` in Google Colab
2. Enable GPU runtime (T4 recommended)
3. Run all cells to train and save LoRA adapters
4. Download the trained adapters

### 4. Run the API Server

```bash
# Set environment variables
cp env.example .env
# Edit .env with your configuration

# Start the server
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Direct detection
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "My Aadhaar is 2345 6789 0123"}'
```

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
    "confidence": 0.94,
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
    "confidence": 0.95,
    "severity": 3,
    "reason": "Detected 1 Email Address"
  },
  "processing_time_ms": 45.2,
  "model_version": "1.0.0"
}
```

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

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Inference Latency | < 100ms | With 4-bit quantization |
| Precision | > 95% | All entity types |
| Recall | > 95% | All entity types |
| IN_AADHAAR F1 | > 98% | Critical entity |
| IN_PAN F1 | > 98% | Critical entity |

## Development

### Running Tests

```bash
# Generate test data
python -m data_gen.dataset_builder --samples 1000 --output-dir test_data

# Run the API in debug mode
DEBUG=true uvicorn api.main:app --reload
```

### Adding New Entity Types

1. Add pattern and context words to `data_gen/config.py`
2. Add templates to `data_gen/templates.py`
3. Add validator to `data_gen/validators.py`
4. Update severity in `api/actions.py`
5. Retrain the model

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [Microsoft Presidio](https://github.com/microsoft/presidio) - Entity naming conventions
- [Guardrails AI](https://github.com/guardrails-ai/guardrails) - Action strategies
- [Unsloth](https://github.com/unslothai/unsloth) - Optimized fine-tuning
- [Portkey](https://portkey.ai) - AI Gateway integration

