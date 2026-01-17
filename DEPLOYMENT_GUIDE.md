# Model Deployment Guide: Download → FastAPI → Portkey

Complete step-by-step guide to deploy your fine-tuned PII model.

---

## Step 1: Download Model from Google Drive

### Option A: Manual Download (Easiest)

1. Go to [Google Drive](https://drive.google.com)
2. Find folder: `pii-guardrail-model`
3. Right-click → **Download**
4. Extract ZIP to your local project:
   ```
   pii-guardrail-model/
   ├── adapter_config.json
   ├── adapter_model.bin
   ├── tokenizer.json
   ├── tokenizer_config.json
   └── special_tokens_map.json
   ```
5. Place in project root: `./pii-guardrail-model/output/`

### Option B: Programmatic Download (With Python)

Create `download_model.py`:

```python
import os
import subprocess
from pathlib import Path

# Install Google Drive CLI
subprocess.run(["pip", "install", "gdown"], check=True)

import gdown

# Get folder ID from your Google Drive link
# Link format: https://drive.google.com/drive/folders/FOLDER_ID
FOLDER_ID = "your_folder_id_here"  # Replace with actual ID

output_dir = Path("pii-guardrail-model/output")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading model to {output_dir}...")

# Download folder
gdown.download_folder(
    url=f"https://drive.google.com/drive/folders/{FOLDER_ID}",
    output=str(output_dir),
    quiet=False,
    use_cookies=False
)

print("✅ Model downloaded successfully!")

# Verify files
files = list(output_dir.glob("*"))
print(f"\nFiles in {output_dir}:")
for f in files:
    size_mb = f.stat().st_size / 1e6 if f.is_file() else 0
    print(f"  - {f.name} ({size_mb:.1f}MB)" if f.is_file() else f"  - {f.name}/")
```

Run it:
```bash
python download_model.py
```

### Option C: Using `gdrive` CLI

```bash
# Install gdrive
# Windows: Download from https://github.com/prasmussen/gdrive/releases

# Authenticate (first time)
gdrive auth

# Download folder
gdrive download --recursive FOLDER_ID

# Move to project
mv FOLDER_ID pii-guardrail-model/output
```

---

## Step 2: Deploy with FastAPI Server

### A. Verify Model Files

```bash
ls -r pii-guardrail-model/output/
```

Expected output:
```
adapter_config.json
adapter_model.bin
tokenizer.json
tokenizer_config.json
special_tokens_map.json
```

### B. Set Environment Variables

Create `.env` file in project root:

```bash
# Model Configuration
MODEL_PATH=./pii-guardrail-model/output
LOAD_IN_4BIT=true

# API Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_RELOAD=true

# Optional: Fallback LLM (for low confidence)
FALLBACK_LLM_PROVIDER=openai
FALLBACK_LLM_KEY=your_api_key_here
```

Or copy from template:
```bash
cp env.example .env
# Edit .env with your values
```

### C. Install Dependencies

```bash
# Python 3.10+ required
python --version

# Create virtual environment (optional but recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install PyTorch (required)
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Install unsloth for optimized inference
pip install unsloth

# Verify installation
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
```

### D. Start the FastAPI Server

```bash
# Method 1: Direct uvicorn
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Method 2: Using Python
python -c "import uvicorn; uvicorn.run('api.main:app', host='0.0.0.0', port=8000, reload=True)"
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### E. Test the API Server

Open new terminal (keep server running):

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","model_loaded":true,"version":"1.0.0"}
```

Test with Python:

```python
import requests
import json

# Test direct inference
response = requests.post(
    "http://localhost:8000/inference",
    json={
        "text": "My Aadhaar is 1234-5678-9012 and email is test@example.com",
        "threshold": 0.6
    }
)

print(json.dumps(response.json(), indent=2))

# Expected response:
# {
#   "flagged": true,
#   "entities": [
#     {
#       "type": "IN_AADHAAR",
#       "value": "1234-5678-9012",
#       "confidence": 0.95,
#       "start": 13,
#       "end": 28
#     },
#     {
#       "type": "EMAIL_ADDRESS",
#       "value": "test@example.com",
#       "confidence": 0.92,
#       "start": 37,
#       "end": 53
#     }
#   ],
#   "confidence": 0.94,
#   "action": "BLOCK",
#   "reason": "Contains sensitive PII"
# }
```

### F. API Endpoints

**Health Check:**
```bash
GET /health
```

**Direct Inference:**
```bash
POST /inference
Content-Type: application/json

{
  "text": "string",
  "threshold": 0.6
}
```

**Portkey Webhook (see Step 3):**
```bash
POST /guardrail/pii
Content-Type: application/json

{
  "data": {
    "messages": [
      {"role": "user", "content": "..."}
    ]
  }
}
```

**Docs:**
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## Step 3: Configure Portkey Webhook Integration

### A. What is Portkey?

Portkey is an LLM gateway that lets you add guardrails to your LLM calls. Your FastAPI server acts as a **webhook** that inspects text before it goes to your LLM.

```
User Request
    ↓
Portkey Gateway
    ↓
Your PII Guardrail Webhook (FastAPI)
    ├─ Detects PII → BLOCK/FLAG
    └─ No PII → Allow to LLM
    ↓
LLM (OpenAI, Claude, etc.)
```

### B. Portkey Setup

1. **Sign up:** https://portkey.ai
2. **Create API key**
3. **Go to Guardrails section**
4. **Add Custom Guardrail → Webhook**

### C. Configure Your Webhook

In Portkey Dashboard:

**Webhook Configuration:**
```
Name: PII Detection
URL: https://your-domain.com/guardrail/pii
Method: POST
Timeout: 30 seconds
Retry: 3 times
```

**Headers:**
```json
{
  "Authorization": "Bearer YOUR_API_TOKEN",
  "Content-Type": "application/json"
}
```

### D. Local Testing with Portkey

If testing locally (your machine not accessible from internet), use tunneling:

```bash
# Install ngrok
# https://ngrok.com/

# Create public tunnel
ngrok http 8000

# This gives you a URL like: https://abc123.ngrok.io

# Use in Portkey:
# URL: https://abc123.ngrok.io/guardrail/pii
```

### E. Test Portkey Integration

Using Portkey's test interface or curl:

```bash
# Get your Portkey API key
PORTKEY_API_KEY="your_portkey_api_key"

# Test call through Portkey
curl https://api.portkey.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "x-portkey-api-key: $PORTKEY_API_KEY" \
  -H "x-portkey-guardrail: pii-detection" \
  -d '{
    "messages": [
      {"role": "user", "content": "My SSN is 123-45-6789"}
    ]
  }'

# Response will show BLOCKED with reason
```

### F. Production Deployment

For production, deploy your FastAPI to a public server:

**Option 1: AWS EC2**
```bash
# Launch EC2 instance (Ubuntu)
# SSH into instance
# Install Docker
# Build and run container

docker build -t pii-guardrail .
docker run -p 8000:8000 --env-file .env pii-guardrail
```

**Option 2: Heroku**
```bash
# Install Heroku CLI
heroku login
heroku create pii-guardrail-api
git push heroku main
```

**Option 3: Railway/Render**
Connect GitHub repo and auto-deploy.

**Option 4: Docker + Your Server**
```bash
# Create Dockerfile (if not exists)
docker build -t pii-guardrail .
docker run -d -p 8000:8000 --env-file .env pii-guardrail
```

### G. Portkey Production URL

Once deployed, update Portkey with your production URL:

```
URL: https://your-api.example.com/guardrail/pii
```

---

## Complete Workflow Checklist

- [ ] Download model from Google Drive
- [ ] Verify model files exist in `pii-guardrail-model/output/`
- [ ] Create `.env` file with `MODEL_PATH` set
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
- [ ] Install unsloth: `pip install unsloth`
- [ ] Start FastAPI: `python -m uvicorn api.main:app --reload`
- [ ] Test health endpoint: `curl http://localhost:8000/health`
- [ ] Test inference: Send sample PII text
- [ ] Sign up for Portkey
- [ ] Configure webhook in Portkey dashboard
- [ ] Test through Portkey (local or deployed)
- [ ] Deploy to production server
- [ ] Update Portkey with production URL
- [ ] Monitor logs for errors

---

## Troubleshooting

**Model not loading:**
```
Error: "Model path does not exist"
→ Check MODEL_PATH in .env matches actual folder location
→ Verify adapter_model.bin exists
```

**Out of memory:**
```
Error: "CUDA out of memory"
→ Set LOAD_IN_4BIT=true in .env
→ Reduce max_seq_length in api/model.py
```

**unsloth not found:**
```
Error: "ModuleNotFoundError: No module named 'unsloth'"
→ pip install unsloth
→ Falls back to slower inference without it
```

**Portkey webhook timeout:**
```
Error: "Webhook timeout"
→ Increase timeout in Portkey to 30+ seconds
→ Check FastAPI is responding: curl http://localhost:8000/health
```

---

## Next: Monitor & Maintain

Once deployed:

1. **Monitor API logs** - Check for errors
2. **Track metrics** - PII detection accuracy
3. **Update model** - Retrain periodically
4. **Scale** - Add load balancer if needed

See `api/main.py` for logging configuration.
