#!/usr/bin/env python3
"""
PII Training Data Generator using Portkey

Features:
- Uses Portkey API gateway with any supported model
- PARALLEL processing for 4-5x faster generation
- Batch processing with checkpoint/resume capability
- Hybrid approach: LLM generates contexts, we inject random valid PII
- Observability through Portkey dashboard

Usage:
    # Set environment variables (Windows PowerShell)
    $env:PORTKEY_API_KEY = "your_api_key"
    
    # Optional: Set model (default: @openai/gpt-4o-mini)
    $env:PORTKEY_MODEL = "@openai/gpt-4o-mini"
    
    # Generate dataset (parallel by default - 5 workers)
    python training/generate_with_portkey.py --samples 10000 --output data
    
    # Use more workers for faster generation (careful with rate limits)
    python training/generate_with_portkey.py --samples 10000 --workers 10
    
    # Use fewer workers if hitting rate limits
    python training/generate_with_portkey.py --samples 10000 --workers 3
    
    # Use sequential mode (slower but safer for rate limits)
    python training/generate_with_portkey.py --samples 10000 --sequential
    
    # Use specific model
    python training/generate_with_portkey.py --samples 10000 --model "@openai/gpt-4o"
    
    # Resume if interrupted
    python training/generate_with_portkey.py --samples 10000 --output data --resume

Available Models (Portkey format @provider/model):
    @openai/gpt-4o-mini     - Fast, cheap, good quality (recommended)
    @openai/gpt-4o          - Best OpenAI quality
    @openai/o4-mini         - Reasoning model
    @google/gemini-1.5-flash - Fast Gemini
    @google/gemini-1.5-pro  - Best Gemini
    @anthropic/claude-3-haiku - Fast Claude
"""

import os
import json
import time
import random
import string
import threading
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from portkey_ai import Portkey
except ImportError:
    print("ERROR: portkey-ai package not installed")
    print("Run: pip install portkey-ai")
    exit(1)

# ============================================================================
# Configuration
# ============================================================================
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")

# Model to use - Portkey format: @provider/model-name
# Options: @openai/gpt-4o-mini, @openai/gpt-4o, @google/gemini-1.5-flash, etc.
MODEL_NAME = os.getenv("PORTKEY_MODEL", "@openai/gpt-4o-mini")  # Default to GPT-4o-mini

BATCH_SIZE = 30  # Samples per API call (conservative for rate limits)
MAX_WORKERS = 5  # Number of parallel API calls
CHECKPOINT_FILE = "data/portkey_checkpoint.json"
OUTPUT_DIR = "data"

# ============================================================================
# PII Generators (Random but valid formats)
# ============================================================================
def gen_aadhaar() -> str:
    """Generate valid Aadhaar: 12 digits starting with 2-9."""
    first = str(random.randint(2, 9))
    rest = ''.join(random.choices(string.digits, k=11))
    num = first + rest
    return f"{num[:4]} {num[4:8]} {num[8:12]}"


def gen_pan() -> str:
    """Generate valid PAN: ABCDE1234F format."""
    first3 = ''.join(random.choices(string.ascii_uppercase, k=3))
    fourth = random.choice(['P', 'C', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G'])
    fifth = random.choice(string.ascii_uppercase)
    digits = ''.join(random.choices(string.digits, k=4))
    last = random.choice(string.ascii_uppercase)
    return f"{first3}{fourth}{fifth}{digits}{last}"


def gen_email() -> str:
    """Generate realistic email."""
    names = ['rahul', 'priya', 'amit', 'neha', 'vijay', 'sunita', 'raj', 'anita',
             'deepak', 'kavita', 'suresh', 'meera', 'arun', 'pooja', 'kiran', 'sanjay']
    surnames = ['sharma', 'patel', 'singh', 'kumar', 'gupta', 'verma', 'joshi', 'reddy']
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'company.in']
    
    name = random.choice(names)
    surname = random.choice(surnames)
    num = random.randint(1, 999)
    domain = random.choice(domains)
    
    formats = [
        f"{name}.{surname}{num}@{domain}",
        f"{name}{num}@{domain}",
        f"{name}_{surname}@{domain}",
    ]
    return random.choice(formats)


def gen_phone() -> str:
    """Generate valid Indian phone number."""
    first = str(random.randint(6, 9))
    rest = ''.join(random.choices(string.digits, k=9))
    num = first + rest
    formats = [
        f"+91 {num[:5]} {num[5:]}",
        f"+91-{num[:5]}-{num[5:]}",
        f"{num[:5]} {num[5:]}",
    ]
    return random.choice(formats)


def gen_ssn() -> str:
    """Generate valid US SSN format."""
    area = random.randint(1, 899)
    while area in [0, 666] or area >= 900:
        area = random.randint(1, 899)
    group = random.randint(1, 99)
    serial = random.randint(1, 9999)
    return f"{area:03d}-{group:02d}-{serial:04d}"


def gen_credit_card() -> str:
    """Generate credit card number format."""
    prefix = random.choice(['4', '5', '37', '6011'])
    length = 16 if prefix != '37' else 15
    rest = ''.join(random.choices(string.digits, k=length - len(prefix)))
    num = prefix + rest
    if len(num) == 16:
        return f"{num[:4]} {num[4:8]} {num[8:12]} {num[12:]}"
    return f"{num[:4]} {num[4:10]} {num[10:]}"


def gen_person() -> str:
    """Generate Indian person name."""
    first_names = ['Rahul', 'Priya', 'Amit', 'Neha', 'Vijay', 'Sunita', 'Raj', 
                   'Anita', 'Deepak', 'Kavita', 'Suresh', 'Meera', 'Arun', 'Pooja',
                   'Kiran', 'Sanjay', 'Ravi', 'Lakshmi', 'Venkat', 'Divya']
    last_names = ['Sharma', 'Patel', 'Singh', 'Kumar', 'Gupta', 'Verma', 'Joshi',
                  'Rao', 'Reddy', 'Nair', 'Menon', 'Das', 'Bose', 'Sen', 'Iyer']
    return f"{random.choice(first_names)} {random.choice(last_names)}"


# Mapping of PII types to their placeholders and generators
PII_CONFIG = {
    "IN_AADHAAR": {"placeholder": "{{AADHAAR}}", "generator": gen_aadhaar},
    "IN_PAN": {"placeholder": "{{PAN}}", "generator": gen_pan},
    "EMAIL_ADDRESS": {"placeholder": "{{EMAIL}}", "generator": gen_email},
    "PHONE_NUMBER": {"placeholder": "{{PHONE}}", "generator": gen_phone},
    "US_SSN": {"placeholder": "{{SSN}}", "generator": gen_ssn},
    "CREDIT_CARD": {"placeholder": "{{CARD}}", "generator": gen_credit_card},
    "PERSON": {"placeholder": "{{NAME}}", "generator": gen_person},
}

# Context words for confidence scoring
CONTEXT_WORDS = {
    "IN_AADHAAR": ["aadhaar", "uid", "uidai", "unique id", "आधार", "aadhar"],
    "IN_PAN": ["pan", "income tax", "tax", "permanent account", "pan card"],
    "EMAIL_ADDRESS": ["email", "mail", "contact", "@", "e-mail"],
    "PHONE_NUMBER": ["phone", "mobile", "call", "whatsapp", "+91", "number", "contact"],
    "US_SSN": ["ssn", "social security", "tax id", "social"],
    "CREDIT_CARD": ["card", "credit", "debit", "payment", "visa", "mastercard"],
    "PERSON": ["name", "mr", "ms", "mrs", "dr", "person", "user", "customer"],
}


# ============================================================================
# Gemini Prompts (for context generation)
# ============================================================================
def get_prompt_for_type(pii_type: str, count: int) -> str:
    """Get the Gemini prompt for generating contexts."""
    
    prompts = {
        "IN_AADHAAR": f"""Generate exactly {count} unique, realistic sentences where someone mentions their Aadhaar number.
Use {{{{AADHAAR}}}} as the placeholder for the 12-digit number.

Requirements:
- Mix of formal and informal styles
- Include some Hinglish (Hindi-English mix) sentences
- Vary contexts: KYC verification, bank linking, government services, casual mention
- Some sentences should have context words like "Aadhaar", "UID", some should not
- Make them sound like real user inputs, not templated

Return ONLY a JSON array of strings, nothing else. Example format:
["My Aadhaar is {{{{AADHAAR}}}}.", "bhai mera aadhaar {{{{AADHAAR}}}} hai verify karo"]""",

        "IN_PAN": f"""Generate exactly {count} unique, realistic sentences where someone mentions their PAN card number.
Use {{{{PAN}}}} as the placeholder.

Requirements:
- Mix formal and informal styles
- Include some Hinglish
- Contexts: tax filing, bank account opening, investment, ID verification
- Vary whether "PAN" keyword is present or not
- Sound like real user inputs

Return ONLY a JSON array of strings.""",

        "EMAIL_ADDRESS": f"""Generate exactly {count} unique, realistic sentences where someone shares their email address.
Use {{{{EMAIL}}}} as the placeholder.

Requirements:
- Mix formal and informal
- Contexts: contact sharing, registration, work communication, personal
- Realistic phrasing

Return ONLY a JSON array of strings.""",

        "PHONE_NUMBER": f"""Generate exactly {count} unique, realistic sentences with Indian phone numbers.
Use {{{{PHONE}}}} as the placeholder.

Requirements:
- Mix formal and informal, include Hinglish
- Contexts: contact sharing, WhatsApp, business, emergency
- Realistic Indian communication style

Return ONLY a JSON array of strings.""",

        "US_SSN": f"""Generate exactly {count} unique, realistic sentences mentioning US Social Security Numbers.
Use {{{{SSN}}}} as the placeholder.

Requirements:
- Mix formal and informal
- Contexts: tax filing, employment, benefits, identity verification
- Realistic US contexts

Return ONLY a JSON array of strings.""",

        "CREDIT_CARD": f"""Generate exactly {count} unique, realistic sentences mentioning credit/debit card numbers.
Use {{{{CARD}}}} as the placeholder.

Requirements:
- Mix formal and informal
- Contexts: online payment, verification, shopping, booking
- Realistic

Return ONLY a JSON array of strings.""",

        "PERSON": f"""Generate exactly {count} unique, realistic sentences mentioning a person by name.
Use {{{{NAME}}}} as the placeholder for Indian names.

Requirements:
- Contexts: introductions, references, appointments, records, mentions
- Mix formal and informal
- Realistic

Return ONLY a JSON array of strings.""",

        "NEGATIVE": f"""Generate exactly {count} unique sentences that contain NO personal identifiable information.
These should be normal business, technical, or casual sentences.

Requirements:
- Some should look like they MIGHT contain PII but don't (tricky negatives):
  - Order IDs that look like phone numbers (e.g., "Order #9876543210")
  - Product codes that look like PAN (e.g., "SKU: ABCDE12345")
  - Reference numbers that look like Aadhaar (e.g., "Ticket: 1234 5678 9012")
- Include: technical documentation, business updates, news, casual chat
- NO actual PII - no real names, no valid Aadhaar/PAN/phone formats
- Mix of contexts: IT, business, daily life, news

Return ONLY a JSON array of strings.""",
    }
    
    return prompts.get(pii_type, "")


# ============================================================================
# System Prompt for Training Data
# ============================================================================
SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection system.

TASK: Analyze the input text and detect any PII entities.

OUTPUT FORMAT (strict JSON):
{
  "flagged": true or false,
  "confidence": 1-10,
  "entities": [
    {
      "type": "ENTITY_TYPE",
      "value": "exact text from input",
      "start": start_index,
      "end": end_index
    }
  ],
  "reason": "explanation"
}

ENTITY TYPES:
- IN_AADHAAR: Indian Aadhaar (12 digits, starts with 2-9)
- IN_PAN: Indian PAN (format: ABCDE1234F)
- EMAIL_ADDRESS: Email addresses
- PHONE_NUMBER: Phone numbers (Indian mobile starts with 6-9)
- PERSON: Person names
- US_SSN: US Social Security (XXX-XX-XXXX)
- CREDIT_CARD: Credit card numbers (13-16 digits)

CRITICAL RULES:
1. ONLY flag text that ACTUALLY appears in the input
2. The "value" field MUST be an exact substring of the input
3. start/end positions MUST be accurate
4. If NO PII exists, return flagged=false with empty entities array
5. Do NOT hallucinate or invent PII that isn't there
6. Order IDs, product codes, dates, IP addresses are NOT PII

CONFIDENCE SCORING:
- 10: Perfect pattern match with strong context words
- 8-9: Strong match with some context
- 6-7: Pattern match without strong context
- 4-5: Weak pattern, ambiguous
- 1-3: Very uncertain, likely false positive"""


# ============================================================================
# Portkey Data Generator
# ============================================================================
class PortkeyDataGenerator:
    def __init__(self, api_key: str, model: str = None):
        """Initialize Portkey client."""
        self.client = Portkey(api_key=api_key)
        self.model = model or MODEL_NAME
        self.checkpoint = self._load_checkpoint()
        
        print(f"Using model: {self.model}")
        
    def _load_checkpoint(self) -> Dict:
        """Load progress from checkpoint file."""
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"completed_batches": [], "samples": []}
    
    def _save_checkpoint(self):
        """Save progress to checkpoint file."""
        os.makedirs(os.path.dirname(CHECKPOINT_FILE) if os.path.dirname(CHECKPOINT_FILE) else '.', exist_ok=True)
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)
        print(f"  [Checkpoint] Saved: {len(self.checkpoint['samples'])} total samples")
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM via Portkey."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=4096,
                temperature=0.8,  # Some creativity for variety
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  [API Error] {e}")
            return None
    
    def _parse_json_array(self, text: str) -> List[str]:
        """Extract JSON array from response text."""
        try:
            # Find JSON array in response
            start = text.find('[')
            end = text.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            print(f"  [JSON Error] {e}")
        return []
    
    def _calculate_confidence(self, text: str, pii_type: str) -> int:
        """Calculate confidence based on context words."""
        text_lower = text.lower()
        context_words = CONTEXT_WORDS.get(pii_type, [])
        
        has_strong_context = any(word in text_lower for word in context_words)
        
        if has_strong_context:
            return random.randint(9, 10)
        else:
            return random.randint(6, 8)
    
    def _create_positive_sample(self, context: str, pii_type: str) -> Optional[Dict]:
        """Create a training sample with PII."""
        config = PII_CONFIG[pii_type]
        placeholder = config["placeholder"]
        generator = config["generator"]
        
        # Check if placeholder exists
        if placeholder not in context:
            return None
        
        # Generate PII value and replace placeholder
        value = generator()
        text = context.replace(placeholder, value)
        
        # Find position
        start = text.find(value)
        if start == -1:
            return None
        end = start + len(value)
        
        confidence = self._calculate_confidence(text, pii_type)
        
        return {
            "text": text,
            "flagged": True,
            "pii_type": pii_type,
            "value": value,
            "start": start,
            "end": end,
            "confidence": confidence
        }
    
    def _create_negative_sample(self, text: str) -> Dict:
        """Create a training sample without PII."""
        return {
            "text": text,
            "flagged": False,
            "pii_type": None,
            "value": None,
            "start": None,
            "end": None,
            "confidence": 10
        }
    
    def generate_batch(self, pii_type: str, count: int, batch_num: int) -> List[Dict]:
        """Generate a batch of samples for one PII type."""
        batch_id = f"{pii_type}_batch{batch_num}"
        
        # Skip if already completed
        if batch_id in self.checkpoint["completed_batches"]:
            print(f"  [Skip] Already completed: {batch_id}")
            return []
        
        print(f"\n{'='*60}")
        print(f"Generating: {batch_id} ({count} samples)")
        print(f"{'='*60}")
        
        # Get prompt and call API
        prompt = get_prompt_for_type(pii_type, count)
        response = self._call_llm(prompt)
        
        if not response:
            print(f"  [Failed] No response for {batch_id}")
            return []
        
        # Parse contexts
        contexts = self._parse_json_array(response)
        print(f"  [OK] Received {len(contexts)} contexts from API")
        
        # Create samples
        samples = []
        for context in contexts:
            if pii_type == "NEGATIVE":
                sample = self._create_negative_sample(context)
            else:
                sample = self._create_positive_sample(context, pii_type)
            
            if sample:
                samples.append(sample)
        
        print(f"  [OK] Created {len(samples)} valid samples")
        
        # Update checkpoint
        self.checkpoint["completed_batches"].append(batch_id)
        self.checkpoint["samples"].extend(samples)
        self._save_checkpoint()
        
        # Rate limit delay
        print(f"  [Wait] {DELAY_BETWEEN_BATCHES}s rate limit delay...")
        time.sleep(DELAY_BETWEEN_BATCHES)
        
        return samples
    
    def generate_dataset(self, total_samples: int = 10000) -> List[Dict]:
        """Generate the full dataset (sequential mode)."""
        # Calculate samples per type (8 types including NEGATIVE)
        pii_types = list(PII_CONFIG.keys()) + ["NEGATIVE"]
        samples_per_type = total_samples // len(pii_types)
        
        print(f"\n{'#'*60}")
        print(f"PII Training Data Generator (Portkey) - SEQUENTIAL MODE")
        print(f"{'#'*60}")
        print(f"Total target: {total_samples} samples")
        print(f"Per type: {samples_per_type} samples")
        print(f"Types: {', '.join(pii_types)}")
        print(f"Batch size: {BATCH_SIZE}")
        print(f"{'#'*60}\n")
        
        for pii_type in pii_types:
            remaining = samples_per_type
            batch_num = 0
            
            while remaining > 0:
                batch_size = min(BATCH_SIZE, remaining)
                self.generate_batch(pii_type, batch_size, batch_num)
                remaining -= batch_size
                batch_num += 1
        
        print(f"\n{'#'*60}")
        print(f"Generation Complete!")
        print(f"Total samples: {len(self.checkpoint['samples'])}")
        print(f"{'#'*60}")
        
        return self.checkpoint["samples"]
    
    def _process_batch_parallel(self, batch_info: Tuple[str, int, int]) -> Tuple[List[Dict], str, bool]:
        """Process a single batch - used for parallel execution."""
        pii_type, count, batch_num = batch_info
        batch_id = f"{pii_type}_batch{batch_num}"
        
        # Skip if already completed
        if batch_id in self.checkpoint["completed_batches"]:
            return [], batch_id, True  # skipped=True
        
        # Get prompt and call API
        prompt = get_prompt_for_type(pii_type, count)
        response = self._call_llm(prompt)
        
        if not response:
            return [], batch_id, False
        
        # Parse contexts
        contexts = self._parse_json_array(response)
        
        # Create samples
        samples = []
        for context in contexts:
            if pii_type == "NEGATIVE":
                sample = self._create_negative_sample(context)
            else:
                sample = self._create_positive_sample(context, pii_type)
            
            if sample:
                samples.append(sample)
        
        return samples, batch_id, False  # skipped=False
    
    def generate_dataset_parallel(self, total_samples: int = 10000, max_workers: int = 5) -> List[Dict]:
        """Generate the full dataset using parallel processing."""
        # Calculate samples per type (8 types including NEGATIVE)
        pii_types = list(PII_CONFIG.keys()) + ["NEGATIVE"]
        samples_per_type = total_samples // len(pii_types)
        
        print(f"\n{'#'*60}")
        print(f"PII Training Data Generator (Portkey) - PARALLEL MODE")
        print(f"{'#'*60}")
        print(f"Total target: {total_samples} samples")
        print(f"Per type: {samples_per_type} samples")
        print(f"Types: {', '.join(pii_types)}")
        print(f"Batch size: {BATCH_SIZE}")
        print(f"Parallel workers: {max_workers}")
        print(f"{'#'*60}\n")
        
        # Build list of all batches to process
        all_batches = []
        for pii_type in pii_types:
            remaining = samples_per_type
            batch_num = 0
            while remaining > 0:
                batch_size = min(BATCH_SIZE, remaining)
                all_batches.append((pii_type, batch_size, batch_num))
                remaining -= batch_size
                batch_num += 1
        
        print(f"Total batches to process: {len(all_batches)}")
        
        # Process batches in parallel
        completed = 0
        failed = 0
        skipped = 0
        lock = threading.Lock()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_batch_parallel, batch): batch 
                for batch in all_batches
            }
            
            # Process results as they complete
            for future in as_completed(future_to_batch):
                batch_info = future_to_batch[future]
                pii_type, count, batch_num = batch_info
                
                try:
                    samples, batch_id, was_skipped = future.result()
                    
                    with lock:
                        if was_skipped:
                            skipped += 1
                        elif samples:
                            self.checkpoint["completed_batches"].append(batch_id)
                            self.checkpoint["samples"].extend(samples)
                            completed += 1
                            print(f"  [OK] {batch_id}: {len(samples)} samples (Total: {len(self.checkpoint['samples'])})")
                        else:
                            failed += 1
                            print(f"  [FAIL] {batch_id}: No samples generated")
                        
                        # Save checkpoint periodically
                        if completed % 10 == 0 and completed > 0:
                            self._save_checkpoint()
                            
                except Exception as e:
                    failed += 1
                    print(f"  [ERROR] {pii_type}_batch{batch_num}: {e}")
        
        # Final save
        self._save_checkpoint()
        
        print(f"\n{'#'*60}")
        print(f"Generation Complete!")
        print(f"  Completed: {completed}")
        print(f"  Skipped: {skipped}")
        print(f"  Failed: {failed}")
        print(f"  Total samples: {len(self.checkpoint['samples'])}")
        print(f"{'#'*60}")
        
        return self.checkpoint["samples"]


def format_for_training(samples: List[Dict]) -> List[Dict]:
    """Convert samples to the training conversation format."""
    formatted = []
    
    for sample in samples:
        if sample["flagged"]:
            output = {
                "flagged": True,
                "confidence": sample["confidence"],
                "entities": [{
                    "type": sample["pii_type"],
                    "value": sample["value"],
                    "start": sample["start"],
                    "end": sample["end"]
                }],
                "reason": f"Detected {sample['pii_type'].replace('_', ' ').replace('IN ', '').title()}"
            }
        else:
            output = {
                "flagged": False,
                "confidence": 10,
                "entities": [],
                "reason": "No PII detected in text"
            }
        
        formatted.append({
            "conversations": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f'Analyze for PII: "{sample["text"]}"'},
                {"role": "assistant", "content": json.dumps(output, indent=2)}
            ]
        })
    
    return formatted


def save_dataset(samples: List[Dict], output_dir: str):
    """Save formatted dataset to JSONL files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Format samples
    formatted = format_for_training(samples)
    
    # Shuffle
    random.shuffle(formatted)
    
    # Split 80/20
    split_idx = int(len(formatted) * 0.8)
    train_data = formatted[:split_idx]
    eval_data = formatted[split_idx:]
    
    # Save
    train_path = os.path.join(output_dir, "train_v2.jsonl")
    eval_path = os.path.join(output_dir, "eval_v2.jsonl")
    
    with open(train_path, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    with open(eval_path, 'w', encoding='utf-8') as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n[Saved] {len(train_data)} training samples -> {train_path}")
    print(f"[Saved] {len(eval_data)} evaluation samples -> {eval_path}")
    
    # Verify uniqueness
    user_texts = [item['conversations'][1]['content'] for item in formatted]
    unique_count = len(set(user_texts))
    dup_count = len(user_texts) - unique_count
    print(f"\n[Quality] Unique samples: {unique_count}/{len(formatted)} ({100*unique_count/len(formatted):.1f}%)")
    if dup_count > 0:
        print(f"[Warning] Duplicates: {dup_count}")


# ============================================================================
# Main
# ============================================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PII training data using Portkey")
    parser.add_argument("--samples", type=int, default=10000, help="Total samples to generate")
    parser.add_argument("--output", type=str, default="data", help="Output directory")
    parser.add_argument("--model", type=str, default=None, help="Model to use (e.g., @openai/gpt-4o-mini)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help=f"Number of parallel workers (default: {MAX_WORKERS})")
    parser.add_argument("--sequential", action="store_true", help="Use sequential mode instead of parallel")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--save-only", action="store_true", help="Only format and save existing checkpoint")
    args = parser.parse_args()
    
    # Check API key
    if not PORTKEY_API_KEY:
        print("=" * 60)
        print("ERROR: PORTKEY_API_KEY environment variable not set")
        print("=" * 60)
        print("\nSet your Portkey API key:")
        print("  Windows PowerShell: $env:PORTKEY_API_KEY = 'your_key'")
        print("  Windows CMD:        set PORTKEY_API_KEY=your_key")
        print("  Linux/Mac:          export PORTKEY_API_KEY=your_key")
        print("\nOptionally set the model (default: @openai/gpt-4o-mini):")
        print("  $env:PORTKEY_MODEL = '@openai/gpt-4o'")
        print("\nAvailable models (Portkey format):")
        print("  @openai/gpt-4o-mini   - Fast, cheap, good quality")
        print("  @openai/gpt-4o        - Best quality, slower")
        print("  @openai/o4-mini       - Reasoning model")
        print("  @google/gemini-1.5-flash - Fast Gemini")
        print("  @google/gemini-1.5-pro   - Best Gemini")
        print("  @anthropic/claude-3-haiku - Fast Claude")
        exit(1)
    
    # Get model from args or env
    model = args.model or MODEL_NAME
    
    # Initialize generator
    generator = PortkeyDataGenerator(PORTKEY_API_KEY, model=model)
    
    if args.save_only:
        # Just format and save existing checkpoint
        if generator.checkpoint["samples"]:
            save_dataset(generator.checkpoint["samples"], args.output)
        else:
            print("No samples in checkpoint to save")
        exit(0)
    
    if not args.resume:
        # Clear checkpoint for fresh start
        if os.path.exists(CHECKPOINT_FILE):
            print(f"\nExisting checkpoint found with {len(generator.checkpoint['samples'])} samples.")
            confirm = input("Delete and start fresh? (y/n): ").strip().lower()
            if confirm == 'y':
                os.remove(CHECKPOINT_FILE)
                generator.checkpoint = {"completed_batches": [], "samples": []}
                print("Checkpoint cleared.")
            else:
                print("Use --resume to continue from checkpoint.")
                exit(0)
    
    # Generate (parallel by default, sequential if --sequential flag)
    if args.sequential:
        print("\nUsing SEQUENTIAL mode...")
        samples = generator.generate_dataset(args.samples)
    else:
        print(f"\nUsing PARALLEL mode with {args.workers} workers...")
        samples = generator.generate_dataset_parallel(args.samples, max_workers=args.workers)
    
    # Save
    if samples:
        save_dataset(samples, args.output)
        print("\n" + "=" * 60)
        print("Done! Upload train_v2.jsonl and eval_v2.jsonl to Google Drive.")
        print("=" * 60)
    else:
        print("\nNo samples generated. Check your API key and try again.")

