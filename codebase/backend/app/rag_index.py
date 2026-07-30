from argparse import ArgumentParser
import json

import httpx


def main() -> None:
    parser = ArgumentParser(description="Index processed Discord data with RAG-Anything.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--scope-key", default="cohort:K4")
    parser.add_argument("--processed-dir", default="/data/processed")
    args = parser.parse_args()
    response = httpx.post(
        f"{args.url.rstrip('/')}/index",
        json={
            "scope_key": args.scope_key,
            "processed_dir": args.processed_dir,
        },
        timeout=1800,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False))


if __name__ == "__main__":
    main()
