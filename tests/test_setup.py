"""Tests for setup.py dependency probing, parser recommendation, and checks."""

from __future__ import annotations

import importlib

from scholaraio.config import Config
from scholaraio.setup import (
    ParserChoice,
    _check_docling,
    _check_huggingface,
    _prompt_text,
    _wizard_keys,
    _wizard_parser,
    check_dep_group,
    recommend_pdf_parser,
    run_check,
)


def test_check_dep_group_treats_runtime_import_failure_as_missing(monkeypatch):
    original = importlib.import_module

    def fake_import(name: str, package=None):
        if name == "bertopic":
            raise RuntimeError("numba cache failure")
        if package is None:
            return original(name)
        return original(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    status = check_dep_group("topics")

    assert not status.installed
    assert "bertopic" in status.missing


def test_check_docling_uses_cli_presence(monkeypatch):
    monkeypatch.setattr("scholaraio.setup.shutil.which", lambda name: "/usr/bin/docling" if name == "docling" else None)

    ok, detail = _check_docling("zh")

    assert ok is True
    assert detail == "/usr/bin/docling"


def test_check_docling_reports_actionable_install_guidance(monkeypatch):
    monkeypatch.setattr("scholaraio.setup.shutil.which", lambda name: None)

    ok, detail = _check_docling("zh")

    assert ok is False
    assert "pip install docling" in detail
    assert "安装文档" in detail


def test_check_huggingface_uses_reachability_probe(monkeypatch):
    monkeypatch.setattr("scholaraio.setup._probe_url", lambda url, timeout=2: url == "https://huggingface.co")

    ok, detail = _check_huggingface("zh")

    assert ok is True
    assert detail == "可达"


def test_check_huggingface_reports_actionable_failure(monkeypatch):
    monkeypatch.setattr("scholaraio.setup._probe_url", lambda url, timeout=2: False)

    ok, detail = _check_huggingface("zh")

    assert ok is False
    assert "Docling" in detail
    assert "MinerU" in detail


def test_recommend_pdf_parser_prefers_mineru_when_both_reachable():
    parser_name, reason = recommend_pdf_parser(True, True, "zh")

    assert parser_name == "MinerU"
    assert "MinerU 可用" in reason
    assert "Hugging Face 也可达" in reason


def test_recommend_pdf_parser_prefers_docling_when_only_huggingface_reachable():
    parser_name, reason = recommend_pdf_parser(False, True, "zh")

    assert parser_name == "Docling"
    assert "Hugging Face 可达而 MinerU 不可用" in reason


def test_run_check_includes_parser_recommendation(monkeypatch):
    cfg = Config()
    monkeypatch.setattr("scholaraio.setup._check_mineru", lambda *_: (True, "mineru ok"))
    monkeypatch.setattr("scholaraio.setup._check_docling", lambda *_: (True, "docling ok"))
    monkeypatch.setattr("scholaraio.setup._check_huggingface", lambda *_: (True, "hf ok"))
    monkeypatch.setattr("scholaraio.setup.recommend_pdf_parser", lambda *args: ("MinerU", "both reachable"))

    results = run_check(cfg, "zh")

    labels = [item.label for item in results]
    assert "Docling" in labels
    assert "Hugging Face" in labels
    assert "PDF 解析器推荐" in labels


def test_check_mineru_reports_actionable_failure(monkeypatch):
    cfg = Config()
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "")

    class DummyRequests:
        @staticmethod
        def get(*_args, **_kwargs):
            raise RuntimeError("offline")

    monkeypatch.setitem(__import__("sys").modules, "requests", DummyRequests)

    from scholaraio.setup import _check_mineru

    ok, detail = _check_mineru(cfg, "zh")

    assert ok is False
    assert "免费申请 key" in detail
    assert "Docker" in detail


def test_wizard_parser_mineru_choice_skips_auto_probe(monkeypatch, capsys):
    cfg = Config()
    answers = iter(["1", "y"])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))
    monkeypatch.setattr(
        "scholaraio.setup._probe_url", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError())
    )

    choice = _wizard_parser(cfg, "zh")

    assert choice.parser == "mineru"
    assert choice.needs_mineru_key is False
    out = capsys.readouterr().out
    assert "已选择 MinerU" in out


def test_wizard_parser_auto_choice_shows_advisory_not_override(monkeypatch, capsys):
    cfg = Config()
    answers = iter(["3", "n"])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))
    monkeypatch.setattr("scholaraio.setup._probe_url", lambda url, timeout=2: "mineru.net" in url)

    choice = _wizard_parser(cfg, "zh")

    assert choice.parser == "mineru"
    assert choice.needs_mineru_key is True
    out = capsys.readouterr().out
    assert "建议优先使用 MinerU" in out
    assert "如果你已经确定要用另一个" in out


def test_wizard_parser_auto_prefers_configured_mineru_before_probe(monkeypatch, capsys):
    cfg = Config()
    monkeypatch.setattr(cfg, "resolved_mineru_api_key", lambda: "mineru-key")
    answers = iter(["3", "n"])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))
    monkeypatch.setattr("scholaraio.setup._probe_url", lambda *_args, **_kwargs: False)

    choice = _wizard_parser(cfg, "zh")

    assert choice.parser == "mineru"
    assert choice.needs_mineru_key is True
    out = capsys.readouterr().out
    assert "建议优先使用 MinerU" in out


def test_prompt_text_returns_empty_string_on_eof(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: (_ for _ in ()).throw(EOFError()))

    value = _prompt_text("  > ")

    assert value == ""


def test_wizard_parser_auto_choice_defaults_to_cloud_key_on_eof(monkeypatch):
    cfg = Config()
    answers = iter(["3", ""])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))
    monkeypatch.setattr("scholaraio.setup._probe_url", lambda url, timeout=2: "mineru.net" in url)

    choice = _wizard_parser(cfg, "zh")

    assert choice.parser == "mineru"
    assert choice.needs_mineru_key is True


def test_wizard_keys_persists_docling_parser_preference(tmp_path, monkeypatch):
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))

    _wizard_keys(tmp_path, "zh", ParserChoice(parser="docling", needs_mineru_key=False))

    local_cfg = (tmp_path / "config.local.yaml").read_text(encoding="utf-8")
    assert "pdf_preferred_parser: docling" in local_cfg


def test_wizard_keys_handles_null_ingest_section(tmp_path, monkeypatch):
    (tmp_path / "config.local.yaml").write_text("ingest: null\n", encoding="utf-8")
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))

    _wizard_keys(tmp_path, "zh", ParserChoice(parser="docling", needs_mineru_key=False))

    local_cfg = (tmp_path / "config.local.yaml").read_text(encoding="utf-8")
    assert "pdf_preferred_parser: docling" in local_cfg


def test_wizard_keys_handles_non_mapping_local_config(tmp_path, monkeypatch):
    (tmp_path / "config.local.yaml").write_text("- unexpected\n", encoding="utf-8")
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))

    _wizard_keys(tmp_path, "zh", ParserChoice(parser="docling", needs_mineru_key=False))

    local_cfg = (tmp_path / "config.local.yaml").read_text(encoding="utf-8")
    assert "pdf_preferred_parser: docling" in local_cfg


def test_wizard_keys_handles_null_llm_section(tmp_path, monkeypatch):
    (tmp_path / "config.local.yaml").write_text("llm: null\n", encoding="utf-8")
    answers = iter(["test-key", ""])
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(answers))

    _wizard_keys(tmp_path, "zh", ParserChoice(parser="docling", needs_mineru_key=False))

    local_cfg = (tmp_path / "config.local.yaml").read_text(encoding="utf-8")
    assert "api_key: test-key" in local_cfg
