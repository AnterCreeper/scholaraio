from __future__ import annotations

import os
from types import SimpleNamespace

from scholaraio import vectors
from scholaraio.config import _build_config


def test_load_model_sets_hf_endpoint_before_sentence_transformers_import(tmp_path, monkeypatch):
    cfg = _build_config(
        {
            "embed": {
                "source": "huggingface",
                "hf_endpoint": "https://hf-mirror.example",
                "device": "cpu",
                "model": "test-model",
            }
        },
        tmp_path,
    )

    seen: dict[str, str | None] = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name: str, device: str):
            self.model_name = model_name
            self.device = device

    def fake_import_module(name: str):
        assert name == "sentence_transformers"
        seen["hf_endpoint_at_import"] = os.environ.get("HF_ENDPOINT")
        return SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)

    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    monkeypatch.setattr(vectors.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(vectors, "_resolve_model_path", lambda *args: None)
    vectors._model_cache.clear()

    model = vectors._load_model(cfg)

    assert seen["hf_endpoint_at_import"] == "https://hf-mirror.example"
    assert model.model_name == "test-model"
    assert model.device == "cpu"
