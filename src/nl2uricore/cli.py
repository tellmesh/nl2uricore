from __future__ import annotations

import argparse
from pathlib import Path

from .generator import GenerationRequest, MarkpactGenerationError, generate_markpact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nl2uricore", description="Generate UriPack Markpact files from NL prompts.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a *.markpact.md file.")
    gen.add_argument("--prompt", required=True)
    gen.add_argument("--prefix", required=True, help="URI scheme prefix, e.g. printer, usb, browser, cache")
    gen.add_argument("--pack-id", default=None)
    gen.add_argument("--out", required=True, help="Output Markpact path")
    gen.add_argument("--model", default=None, help="Optional LiteLLM model, e.g. openai/gpt-4.1-mini")
    gen.add_argument("--no-llm", action="store_true", help="Use deterministic fallback generator")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "generate":
        return 1

    try:
        content = generate_markpact(
            GenerationRequest(prompt=args.prompt, prefix=args.prefix, pack_id=args.pack_id),
            use_llm=not args.no_llm,
            model=args.model,
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(out)
        return 0
    except MarkpactGenerationError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
