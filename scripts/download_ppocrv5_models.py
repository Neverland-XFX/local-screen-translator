from pathlib import Path
import sys

import requests


BASE_URL = "https://huggingface.co/PaddlePaddle/{repo}/resolve/main/{file}"
FILES = ["inference.json", "inference.pdiparams", "inference.yml", "config.json"]
MODELS = {
    "ppocrv5_server_det": "PP-OCRv5_server_det",
    "ppocrv5_server_rec": "PP-OCRv5_server_rec",
}


def download_file(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    models_dir = root / "models" / "ocr"

    for key, repo in MODELS.items():
        target = models_dir / key
        print(f"Downloading {repo} -> {target}")
        for filename in FILES:
            url = BASE_URL.format(repo=repo, file=filename)
            dest = target / filename
            print(f"  {filename}")
            download_file(url, dest)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
