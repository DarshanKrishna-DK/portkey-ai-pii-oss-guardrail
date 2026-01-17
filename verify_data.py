"""
Verification script to check generated PII Guardrail dataset.
"""

import json
from pathlib import Path
from collections import Counter


def verify_dataset():
    data_dir = Path("data")
    
    print("=" * 70)
    print("PII GUARDRAIL DATASET VERIFICATION")
    print("=" * 70)
    
    # 1. Check dataset stats
    print("\n1. DATASET STATISTICS")
    print("-" * 70)
    stats_file = data_dir / "dataset_stats.json"
    if stats_file.exists():
        with open(stats_file) as f:
            stats = json.load(f)
        print(f"✓ Total samples: {stats['total_samples']:,}")
        print(f"  - Train: {stats['train_samples']:,} ({stats['train_samples']/stats['total_samples']*100:.1f}%)")
        print(f"  - Eval: {stats['eval_samples']:,} ({stats['eval_samples']/stats['total_samples']*100:.1f}%)")
        print(f"  - Positive (with PII): {stats['positive_samples']:,}")
        print(f"  - Negative (without PII): {stats['negative_samples']:,}")
        print(f"✓ Average entities per sample: {stats['avg_entities_per_sample']:.2f}")
        print(f"\n✓ Entity type distribution:")
        for entity_type, count in sorted(stats['entity_distribution'].items(), key=lambda x: -x[1]):
            pct = count / stats['total_samples'] * 100
            print(f"  - {entity_type}: {count:,} ({pct:.1f}%)")
    else:
        print("✗ dataset_stats.json not found")
        return
    
    # 2. Check train.jsonl
    print("\n2. TRAIN DATASET (train.jsonl)")
    print("-" * 70)
    train_file = data_dir / "train.jsonl"
    if train_file.exists():
        train_count = sum(1 for _ in open(train_file))
        print(f"✓ Total lines: {train_count:,}")
        
        # Sample first few records
        print(f"\n✓ Sample records (first 2):")
        with open(train_file) as f:
            for i, line in enumerate(f):
                if i >= 2:
                    break
                record = json.loads(line)
                print(f"\n  Record {i+1}:")
                print(f"    - Keys: {list(record.keys())}")
                if 'text' in record:
                    print(f"    - Text preview: {record['text'][:80]}...")
                if 'output' in record:
                    output = json.loads(record['output']) if isinstance(record['output'], str) else record['output']
                    print(f"    - Flagged: {output.get('flagged')}")
                    print(f"    - Entities: {len(output.get('entities', []))} found")
    else:
        print("✗ train.jsonl not found")
    
    # 3. Check eval.jsonl
    print("\n3. EVAL DATASET (eval.jsonl)")
    print("-" * 70)
    eval_file = data_dir / "eval.jsonl"
    if eval_file.exists():
        eval_count = sum(1 for _ in open(eval_file))
        print(f"✓ Total lines: {eval_count:,}")
        
        # Sample first few records
        print(f"\n✓ Sample records (first 2):")
        with open(eval_file) as f:
            for i, line in enumerate(f):
                if i >= 2:
                    break
                record = json.loads(line)
                print(f"\n  Record {i+1}:")
                print(f"    - Keys: {list(record.keys())}")
                if 'text' in record:
                    print(f"    - Text preview: {record['text'][:80]}...")
                if 'output' in record:
                    output = json.loads(record['output']) if isinstance(record['output'], str) else record['output']
                    print(f"    - Flagged: {output.get('flagged')}")
                    print(f"    - Entities: {len(output.get('entities', []))} found")
    else:
        print("✗ eval.jsonl not found")
    
    # 4. Validation checks
    print("\n4. VALIDATION CHECKS")
    print("-" * 70)
    
    checks_passed = 0
    total_checks = 0
    
    # Check 4.1: File sizes
    total_checks += 1
    try:
        train_size = train_file.stat().st_size
        eval_size = eval_file.stat().st_size
        total_size = (train_size + eval_size) / (1024 * 1024)  # MB
        print(f"✓ File sizes:")
        print(f"  - train.jsonl: {train_size / (1024*1024):.2f} MB")
        print(f"  - eval.jsonl: {eval_size / (1024*1024):.2f} MB")
        print(f"  - Total: {total_size:.2f} MB")
        checks_passed += 1
    except Exception as e:
        print(f"✗ File size check failed: {e}")
    
    # Check 4.2: Line counts match stats
    total_checks += 1
    if train_count == stats['train_samples'] and eval_count == stats['eval_samples']:
        print(f"✓ Line counts match statistics")
        checks_passed += 1
    else:
        print(f"✗ Line count mismatch:")
        print(f"  - Train: {train_count} (expected {stats['train_samples']})")
        print(f"  - Eval: {eval_count} (expected {stats['eval_samples']})")
    
    # Check 4.3: Sample records are valid JSON
    total_checks += 1
    try:
        invalid_count = 0
        with open(train_file) as f:
            for i, line in enumerate(f):
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    invalid_count += 1
        
        if invalid_count == 0:
            print(f"✓ All training records are valid JSON")
            checks_passed += 1
        else:
            print(f"✗ Found {invalid_count} invalid JSON records in train.jsonl")
    except Exception as e:
        print(f"✗ JSON validation failed: {e}")
    
    print("\n" + "=" * 70)
    print(f"VERIFICATION COMPLETE: {checks_passed}/{total_checks} checks passed")
    print("=" * 70)


if __name__ == "__main__":
    verify_dataset()
