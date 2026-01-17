"""
Dataset Builder for PII Guardrail Training

Builds JSONL datasets with train/eval splits in the format
required for instruction-tuning with Unsloth.
"""

import os
import json
import random
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

from .generator import PIIDataGenerator, TrainingSample, TeacherVerifierLoop
from .config import SEVERITY_SCORES


@dataclass
class DatasetStats:
    """Statistics about the generated dataset."""
    total_samples: int
    train_samples: int
    eval_samples: int
    positive_samples: int
    negative_samples: int
    entity_distribution: Dict[str, int]
    avg_entities_per_sample: float


class DatasetBuilder:
    """
    Builds and exports training datasets for the PII guardrail model.
    """
    
    SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection model. 
Analyze the given text and identify all PII entities with their exact locations.

Output a JSON object with:
- flagged: boolean indicating if PII was detected
- entities: array of detected entities with type, value, start, and end positions
- confidence: your confidence score (0.0-1.0)
- reason: brief explanation of what was detected

Entity types to detect:
- IN_AADHAAR: Indian Aadhaar number (12 digits)
- IN_PAN: Indian PAN card (AAAAA0000A format)
- EMAIL_ADDRESS: Email addresses
- PHONE_NUMBER: Phone numbers
- PERSON: Person names
- US_SSN: US Social Security Numbers
- CREDIT_CARD: Credit/debit card numbers"""

    def __init__(
        self,
        output_dir: str = "data",
        gemini_api_key: Optional[str] = None,
        use_gemini: bool = False,
        seed: int = 42
    ):
        """
        Initialize the dataset builder.
        
        Args:
            output_dir: Directory to save datasets
            gemini_api_key: Optional Gemini API key for enhanced generation
            use_gemini: Whether to use Gemini for generation
            seed: Random seed for reproducibility
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.generator = PIIDataGenerator(
            gemini_api_key=gemini_api_key,
            use_gemini=use_gemini,
            seed=seed
        )
        
        self.verifier = TeacherVerifierLoop(gemini_api_key) if use_gemini else None
        self.seed = seed
        random.seed(seed)
    
    def _format_for_training(self, sample: TrainingSample) -> Dict[str, Any]:
        """
        Format a sample for instruction-tuning.
        
        Uses the Llama 3 chat format with system, user, and assistant roles.
        """
        # Create the expected output JSON
        output = {
            "flagged": sample.flagged,
            "entities": [
                {
                    "type": e.type,
                    "value": e.value,
                    "start": e.start,
                    "end": e.end
                }
                for e in sample.entities
            ],
            "confidence": sample.confidence,
            "reason": sample.reason
        }
        
        # Format as conversation
        return {
            "conversations": [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                },
                {
                    "role": "user", 
                    "content": f'Detect PII in: "{sample.text}"'
                },
                {
                    "role": "assistant",
                    "content": json.dumps(output, indent=2)
                }
            ]
        }
    
    def _format_alpaca_style(self, sample: TrainingSample) -> Dict[str, Any]:
        """
        Format a sample in Alpaca instruction format.
        """
        output = {
            "flagged": sample.flagged,
            "entities": [e.to_dict() for e in sample.entities],
            "confidence": sample.confidence,
            "reason": sample.reason
        }
        
        return {
            "instruction": "Detect all PII (Personally Identifiable Information) in the following text. Return a JSON object with flagged status, detected entities with their types and positions, confidence score, and reason.",
            "input": sample.text,
            "output": json.dumps(output, indent=2)
        }
    
    def _calculate_stats(self, samples: List[TrainingSample]) -> DatasetStats:
        """Calculate statistics for a dataset."""
        entity_counts = {}
        total_entities = 0
        positive = 0
        negative = 0
        
        for sample in samples:
            if sample.flagged:
                positive += 1
            else:
                negative += 1
            
            for entity in sample.entities:
                entity_counts[entity.type] = entity_counts.get(entity.type, 0) + 1
                total_entities += 1
        
        return DatasetStats(
            total_samples=len(samples),
            train_samples=0,  # Will be set after split
            eval_samples=0,
            positive_samples=positive,
            negative_samples=negative,
            entity_distribution=entity_counts,
            avg_entities_per_sample=total_entities / len(samples) if samples else 0
        )
    
    def split_dataset(
        self,
        samples: List[TrainingSample],
        eval_ratio: float = 0.2,
        stratify: bool = True
    ) -> Tuple[List[TrainingSample], List[TrainingSample]]:
        """
        Split dataset into train and eval sets.
        
        Args:
            samples: All samples
            eval_ratio: Ratio for evaluation set (default 0.2 = 20%)
            stratify: Whether to stratify by flagged status
            
        Returns:
            Tuple of (train_samples, eval_samples)
        """
        if stratify:
            # Separate positive and negative samples
            positive = [s for s in samples if s.flagged]
            negative = [s for s in samples if not s.flagged]
            
            # Shuffle each group
            random.shuffle(positive)
            random.shuffle(negative)
            
            # Split each group
            pos_split = int(len(positive) * (1 - eval_ratio))
            neg_split = int(len(negative) * (1 - eval_ratio))
            
            train = positive[:pos_split] + negative[:neg_split]
            eval_set = positive[pos_split:] + negative[neg_split:]
            
            # Shuffle the final sets
            random.shuffle(train)
            random.shuffle(eval_set)
        else:
            # Simple random split
            shuffled = samples.copy()
            random.shuffle(shuffled)
            split_idx = int(len(shuffled) * (1 - eval_ratio))
            train = shuffled[:split_idx]
            eval_set = shuffled[split_idx:]
        
        return train, eval_set
    
    def build_dataset(
        self,
        total_samples: int = 10000,
        eval_ratio: float = 0.2,
        format_type: str = "conversation",  # "conversation" or "alpaca"
        verify_with_gemini: bool = False,
        single_entity_ratio: float = 0.5,
        multi_entity_ratio: float = 0.2,
        negative_ratio: float = 0.2,
        edge_case_ratio: float = 0.1
    ) -> Tuple[DatasetStats, str, str]:
        """
        Build and save a complete dataset.
        
        Args:
            total_samples: Total number of samples to generate
            eval_ratio: Ratio for evaluation set
            format_type: Output format ("conversation" or "alpaca")
            verify_with_gemini: Whether to run teacher-verifier loop
            single_entity_ratio: Ratio of single-entity samples
            multi_entity_ratio: Ratio of multi-entity samples
            negative_ratio: Ratio of negative samples
            edge_case_ratio: Ratio of edge case samples
            
        Returns:
            Tuple of (stats, train_path, eval_path)
        """
        print(f"Generating {total_samples} samples...")
        
        # Generate samples
        samples = self.generator.generate_dataset(
            total_samples=total_samples,
            single_entity_ratio=single_entity_ratio,
            multi_entity_ratio=multi_entity_ratio,
            negative_ratio=negative_ratio,
            edge_case_ratio=edge_case_ratio,
            verify=True
        )
        
        # Optional Gemini verification
        if verify_with_gemini and self.verifier:
            print("Running teacher-verifier loop...")
            samples = self.verifier.run_verification_loop(samples)
        
        # Split dataset
        print(f"Splitting dataset (eval_ratio={eval_ratio})...")
        train_samples, eval_samples = self.split_dataset(samples, eval_ratio)
        
        # Calculate stats
        stats = self._calculate_stats(samples)
        stats.train_samples = len(train_samples)
        stats.eval_samples = len(eval_samples)
        
        # Format samples
        format_func = (
            self._format_for_training if format_type == "conversation" 
            else self._format_alpaca_style
        )
        
        train_formatted = [format_func(s) for s in train_samples]
        eval_formatted = [format_func(s) for s in eval_samples]
        
        # Save datasets
        train_path = self.output_dir / "train.jsonl"
        eval_path = self.output_dir / "eval.jsonl"
        
        print(f"Saving train set to {train_path}...")
        with open(train_path, 'w', encoding='utf-8') as f:
            for item in train_formatted:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Saving eval set to {eval_path}...")
        with open(eval_path, 'w', encoding='utf-8') as f:
            for item in eval_formatted:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        # Save stats
        stats_path = self.output_dir / "dataset_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total_samples": stats.total_samples,
                "train_samples": stats.train_samples,
                "eval_samples": stats.eval_samples,
                "positive_samples": stats.positive_samples,
                "negative_samples": stats.negative_samples,
                "entity_distribution": stats.entity_distribution,
                "avg_entities_per_sample": stats.avg_entities_per_sample,
                "config": {
                    "eval_ratio": eval_ratio,
                    "format_type": format_type,
                    "single_entity_ratio": single_entity_ratio,
                    "multi_entity_ratio": multi_entity_ratio,
                    "negative_ratio": negative_ratio,
                    "edge_case_ratio": edge_case_ratio,
                    "seed": self.seed
                }
            }, f, indent=2)
        
        print(f"\nDataset Statistics:")
        print(f"  Total samples: {stats.total_samples}")
        print(f"  Train samples: {stats.train_samples}")
        print(f"  Eval samples: {stats.eval_samples}")
        print(f"  Positive (with PII): {stats.positive_samples}")
        print(f"  Negative (no PII): {stats.negative_samples}")
        print(f"  Avg entities per sample: {stats.avg_entities_per_sample:.2f}")
        print(f"  Entity distribution: {stats.entity_distribution}")
        
        return stats, str(train_path), str(eval_path)
    
    def build_evaluation_set(
        self,
        num_samples: int = 500,
        output_file: str = "eval_benchmark.jsonl"
    ) -> str:
        """
        Build a dedicated evaluation benchmark set.
        
        This creates a balanced set specifically for measuring
        precision, recall, and F1 per entity type.
        """
        samples = []
        
        # Generate equal samples for each entity type
        entity_types = ["IN_AADHAAR", "IN_PAN", "EMAIL_ADDRESS", 
                       "PHONE_NUMBER", "PERSON", "US_SSN", "CREDIT_CARD"]
        
        samples_per_type = num_samples // (len(entity_types) + 1)  # +1 for negatives
        
        for entity_type in entity_types:
            from .templates import TEMPLATES
            templates = TEMPLATES.get(entity_type, [])
            
            for _ in range(samples_per_type):
                if templates:
                    template = random.choice(templates)
                    sample = self.generator._generate_from_template(template)
                    samples.append(sample)
        
        # Add negative samples
        negative_samples = self.generator.generate_negative_samples(samples_per_type)
        samples.extend(negative_samples)
        
        # Shuffle
        random.shuffle(samples)
        
        # Save
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                item = {
                    "text": sample.text,
                    "ground_truth": {
                        "flagged": sample.flagged,
                        "entities": [e.to_dict() for e in sample.entities]
                    }
                }
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Saved evaluation benchmark to {output_path}")
        return str(output_path)


def main():
    """Main function to generate dataset from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PII training dataset")
    parser.add_argument("--samples", type=int, default=10000, help="Total samples")
    parser.add_argument("--eval-ratio", type=float, default=0.2, help="Eval split ratio")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory")
    parser.add_argument("--format", type=str, default="conversation", 
                       choices=["conversation", "alpaca"], help="Output format")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--use-gemini", action="store_true", help="Use Gemini for generation")
    
    args = parser.parse_args()
    
    builder = DatasetBuilder(
        output_dir=args.output_dir,
        use_gemini=args.use_gemini,
        seed=args.seed
    )
    
    builder.build_dataset(
        total_samples=args.samples,
        eval_ratio=args.eval_ratio,
        format_type=args.format
    )


if __name__ == "__main__":
    main()

