"""Shared CLI argument helpers."""

from __future__ import annotations

import argparse


class _ResultLimitAction(argparse.Action):
    """Accept --limit as the canonical flag while keeping --top as a safe alias."""

    def __call__(self, parser, namespace, values, option_string=None):
        current = getattr(namespace, self.dest, None)
        if current is not None and current != values:
            parser.error("--limit 和 --top 不能同时指定不同的值")
        setattr(namespace, self.dest, values)


def _add_result_limit_arg(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument(
        "--limit",
        "--top",
        dest="result_limit",
        metavar="N",
        type=int,
        default=None,
        action=_ResultLimitAction,
        help=f"{help_text}（兼容旧写法 --top）",
    )


def _resolve_result_limit(args: argparse.Namespace, default: int) -> int:
    result_limit = getattr(args, "result_limit", None)
    if result_limit is not None:
        return result_limit
    legacy_top = getattr(args, "top", None)
    if legacy_top is not None:
        return legacy_top
    return default


def _resolve_top(args: argparse.Namespace, default: int) -> int:
    return _resolve_result_limit(args, default)


def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=str, default=None, help="年份过滤：2023 / 2020-2024 / 2020-")
    parser.add_argument("--journal", type=str, default=None, help="期刊名过滤（模糊匹配）")
    parser.add_argument(
        "--type",
        type=str,
        default=None,
        dest="paper_type",
        help="论文类型过滤：review / journal-article 等（模糊匹配）",
    )
