import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .translator import ENVITranslator


def cmd_en2vi(args: argparse.Namespace) -> int:
    tr = ENVITranslator(source="en", target="vi")
    return _run_translate(tr, args)


def cmd_vi2en(args: argparse.Namespace) -> int:
    tr = ENVITranslator(source="vi", target="en")
    return _run_translate(tr, args)


def cmd_translate(args: argparse.Namespace) -> int:
    tr = ENVITranslator(source=args.source, target=args.target)
    return _run_translate(tr, args)


def cmd_languages(args: argparse.Namespace) -> int:
    try:
        data = ENVITranslator.get_supported_languages(as_dict=True)
        items = list(data.items())
        if args.search:
            q = args.search.lower()
            items = [(name, code) for name, code in items if q in name.lower() or q in code.lower()]
        items.sort(key=lambda x: x[0].lower())
        if args.codes:
            for _, code in items:
                print(code)
        else:
            for name, code in items:
                print(f"{name}: {code}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _run_translate(tr: ENVITranslator, args: argparse.Namespace) -> int:
    try:
        if args.text is not None:
            print(
                tr.translate_text(
                    args.text,
                    preserve_format=args.preserve_format,
                    max_chars=args.max_chars,
                    retries=args.retries,
                    retry_backoff_sec=args.retry_backoff,
                )
            )
            return 0
        if args.input is not None and args.output is not None:
            tr.translate_file(
                args.input,
                args.output,
                preserve_format=args.preserve_format,
                max_chars=args.max_chars,
                retries=args.retries,
                retry_backoff_sec=args.retry_backoff,
            )
            print(f"Translated file written to: {args.output}")
            return 0
        print("Provide --text or both --input and --output.", file=sys.stderr)
        return 2
    except Exception as e:  # Surface helpful errors in CLI
        print(f"Error: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="envi_translator",
        description="English ↔ Vietnamese translation using deep-translator (Google)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser, with_source_target: bool = False) -> None:
        sp.add_argument("-t", "--text", help="Text to translate")
        sp.add_argument("-i", "--input", help="Input text file path")
        sp.add_argument("-o", "--output", help="Output text file path")
        sp.add_argument(
            "--preserve-format",
            action="store_true",
            help="Preserve line breaks and spacing (default on if flag present)",
        )
        sp.add_argument(
            "--no-preserve-format",
            action="store_true",
            help="Disable format preservation (overrides --preserve-format)",
        )
        sp.add_argument(
            "--max-chars",
            type=int,
            default=4500,
            help="Max characters per chunk (default: 4500)",
        )
        sp.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Retry times per chunk on errors (default: 3)",
        )
        sp.add_argument(
            "--retry-backoff",
            type=float,
            default=1.0,
            help="Base seconds for exponential backoff (default: 1.0)",
        )
        if with_source_target:
            sp.add_argument("--source", default="auto", help="Source language (default: auto)")
            sp.add_argument("--target", default="vi", help="Target language (default: vi)")

    sp_en2vi = sub.add_parser("en2vi", help="Translate English → Vietnamese")
    add_common(sp_en2vi)
    sp_en2vi.set_defaults(func=cmd_en2vi)

    sp_vi2en = sub.add_parser("vi2en", help="Translate Vietnamese → English")
    add_common(sp_vi2en)
    sp_vi2en.set_defaults(func=cmd_vi2en)

    sp_translate = sub.add_parser("translate", help="Custom translate with --source/--target")
    add_common(sp_translate, with_source_target=True)
    sp_translate.set_defaults(func=cmd_translate)

    # Post-process to derive boolean preserve_format respecting both flags
    def _set_defaults(args: argparse.Namespace) -> None:
        # Default is True unless explicitly disabled by --no-preserve-format
        preserve = True
        if getattr(args, "no_preserve_format", False):
            preserve = False
        if getattr(args, "preserve_format", False):
            preserve = True
        args.preserve_format = preserve

    p.set_defaults(post_parse=_set_defaults)

    # Languages subcommand
    sp_lang = sub.add_parser("languages", help="List supported languages")
    sp_lang.add_argument("--codes", action="store_true", help="Only print language codes")
    sp_lang.add_argument("--search", help="Filter by substring in name or code")
    sp_lang.set_defaults(func=cmd_languages)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    post = getattr(args, "post_parse", None)
    if callable(post):
        post(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
