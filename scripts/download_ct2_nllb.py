from pathlib import Path
import argparse

from ctranslate2.converters import TransformersConverter
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    parser.add_argument("--quantization", default="float16")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    name = args.model.split("/")[-1]
    hf_dir = root / "models" / "translate" / "hf" / name
    ct2_dir = root / "models" / "translate" / "ct2" / name

    hf_dir.mkdir(parents=True, exist_ok=True)
    ct2_dir.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    tokenizer.save_pretrained(hf_dir)
    model.save_pretrained(hf_dir)

    print(f"Converting to CTranslate2: {ct2_dir}")
    converter = TransformersConverter(str(hf_dir))
    converter.convert(str(ct2_dir), quantization=args.quantization, force=True)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
