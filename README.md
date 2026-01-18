# PII Guardrail

Fine-tuned Llama 3.2-1B model for PII detection with FastAPI server and Portkey webhook integration.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PII GUARDRAIL SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐    │
│   │   Portkey    │────▶│   FastAPI Server │────▶│  Llama 3.2-1B       │    │
│   │   Gateway    │     │   /guardrail/pii │     │  (Fine-tuned)       │    │
│   └──────────────┘     └──────────────────┘     └─────────────────────┘    │
│         │                      │                         │                  │
│         │                      ▼                         ▼                  │
│         │              ┌──────────────────┐     ┌─────────────────────┐    │
│         │              │  Pre-filter      │     │  Grounding          │    │
│         │              │  (Regex Scan)    │     │  Validation         │    │
│         │              └──────────────────┘     └─────────────────────┘    │
│         │                                                │                  │
│         ▼                                                ▼                  │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │                        JSON Response                              │     │
│   │  { flagged, confidence, entities, reason, risk_level }           │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp env.example .env
# Edit .env with your MODEL_PATH
```

### 3. Run Server

```bash
python run_server.py
```

Server starts at `http://localhost:8000`

### 4. Test API

Open `http://localhost:8000/docs` for Swagger UI:

![API Documentation](docs-api-swagger.png)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/guardrail/pii` | POST | Portkey webhook endpoint |
| `/detect` | POST | Direct PII detection |
| `/analyze` | POST | Flat response format |

## Request/Response

**Request:**
```json
{
  "text": "My email is john@example.com"
}
```

**Response:**
```json
{
  "flagged": true,
  "confidence": 9,
  "entities": [
    {
      "type": "EMAIL",
      "value": "john@example.com",
      "start": 12,
      "end": 28
    }
  ],
  "reason": "Detected email address",
  "risk_level": "HIGH"
}
```

## Supported PII Types

The model detects the following Personally Identifiable Information:

### Indian PII
| PII Type | Format | Example | Severity |
|----------|--------|---------|----------|
| **Aadhaar** | 12 digits (XXXX XXXX XXXX) | 1234 5678 9012 | 🔴 CRITICAL |
| **PAN** | 10 characters (ABCDE1234F) | ABCDE1234F | 🔴 CRITICAL |

### International PII
| PII Type | Format | Example | Severity |
|----------|--------|---------|----------|
| **Email Address** | user@domain.com | john.doe@example.com | 🟠 HIGH |
| **Phone Number** | +CC XXX-XXXX-XXXX | +91 98765 43210 | 🟠 HIGH |
| **US Social Security Number (SSN)** | XXX-XX-XXXX | 123-45-6789 | 🔴 CRITICAL |
| **Credit Card** | XXXX-XXXX-XXXX-XXXX | 4532-1234-5678-9012 | 🔴 CRITICAL |
| **Person Name** | Full/Partial names | John Smith, Priya Sharma | 🟡 MEDIUM |

### Detection Accuracy

| Entity Type | Detection Rate | False Positive Rate |
|-------------|----------------|-------------------|
| Aadhaar (valid format) | ~95% | Low |
| PAN (valid format) | ~92% | Low-Medium |
| Email Address | ~98% | Very Low |
| Phone Number | ~94% | Low |
| SSN | ~96% | Very Low |
| Credit Card | ~97% | Very Low |
| Person Names | ~85% | Medium |

**Note:** Detection accuracy depends on context. Standalone numbers may have higher false positives.

## Risk Levels

| Level | Confidence | PII Types | Action |
|-------|------------|-----------|--------|
| 🔴 **CRITICAL** | 9-10 | Aadhaar, PAN, SSN, Credit Card | Auto-BLOCK |
| 🟠 **HIGH** | 7-8 | Email, Phone (with context) | FLAG/REVIEW |
| 🟡 **MEDIUM** | 5-6 | Names with location, Employee IDs | FLAG |
| 🟢 **LOW** | 1-4 | Partial data, Public figures | ALLOW/LOG |

## Training (Google Colab)

1. Upload `data/train_v2.jsonl` and `data/eval_v2.jsonl` to Google Drive
2. Open `training/pii_guardrail.ipynb` in Colab
3. Run cells in order (1 → 9 for training, 18 for testing)
4. Download model from Drive

## Project Structure

```
├── api/
│   ├── main.py          # FastAPI application
│   ├── model.py         # Model loading & inference
│   └── schemas.py       # Pydantic models
├── data/
│   ├── train_v2.jsonl   # Training data
│   └── eval_v2.jsonl    # Evaluation data
├── training/
│   ├── pii_guardrail.ipynb      # Colab training notebook
│   └── generate_with_portkey.py # Data generation script
├── pii-guardrail-model/         # Fine-tuned model
├── run_server.py        # Server entry point
└── requirements.txt
```

## Portkey Integration

Set webhook URL in Portkey:
```
https://your-server.com/guardrail/pii
```

Use ngrok for local testing:
```bash
ngrok http 8000
```
