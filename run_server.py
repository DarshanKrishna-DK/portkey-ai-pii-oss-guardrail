#!/usr/bin/env python3
"""
Quick startup script for PII Guardrail API

Usage:
    python run_server.py

Or with custom port:
    python run_server.py --port 8080
"""

import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Start PII Guardrail API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--model-path", type=str, default=None, help="Path to model (default: from .env or pii-guardrail-model/lora_adapters)")
    args = parser.parse_args()
    
    # Set model path if provided
    if args.model_path:
        os.environ["MODEL_PATH"] = args.model_path
    elif "MODEL_PATH" not in os.environ:
        os.environ["MODEL_PATH"] = "pii-guardrail-model/lora_adapters"
    
    print("="*60)
    print("PII Guardrail API Server")
    print("="*60)
    print(f"Model path: {os.environ.get('MODEL_PATH')}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print("="*60)
    print()
    print("Endpoints:")
    print(f"  Health:    http://{args.host}:{args.port}/health")
    print(f"  Detect:    http://{args.host}:{args.port}/detect")
    print(f"  Analyze:   http://{args.host}:{args.port}/analyze")
    print(f"  Portkey:   http://{args.host}:{args.port}/guardrail/pii")
    print(f"  Docs:      http://{args.host}:{args.port}/docs")
    print("="*60)
    print()
    
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()

