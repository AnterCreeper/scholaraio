"""Fault-injection tests for metadata API retry logic."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from scholaraio.ingest.metadata._api import (
    _request_with_retry,
    query_crossref,
    query_openalex,
    query_semantic_scholar,
)


class TestRequestWithRetry:
    @patch("scholaraio.ingest.metadata._api.SESSION")
    def test_success_on_first_attempt(self, mock_session):
        mock_session.get.return_value = SimpleNamespace(status_code=200)
        resp = _request_with_retry("http://example.com/test")
        assert resp.status_code == 200
        assert mock_session.get.call_count == 1

    @patch("scholaraio.ingest.metadata._api.SESSION")
    @patch("scholaraio.ingest.metadata._api.time.sleep")
    def test_retries_429_with_retry_after(self, mock_sleep, mock_session):
        mock_session.get.side_effect = [
            SimpleNamespace(status_code=429, headers={"Retry-After": "3"}),
            SimpleNamespace(status_code=200),
        ]
        resp = _request_with_retry("http://example.com/test")
        assert resp.status_code == 200
        assert mock_session.get.call_count == 2
        mock_sleep.assert_called_once_with(3)

    @patch("scholaraio.ingest.metadata._api.SESSION")
    @patch("scholaraio.ingest.metadata._api.time.sleep")
    def test_retries_429_with_exponential_backoff(self, mock_sleep, mock_session):
        mock_session.get.side_effect = [
            SimpleNamespace(status_code=429, headers={}),
            SimpleNamespace(status_code=429, headers={}),
            SimpleNamespace(status_code=200),
        ]
        resp = _request_with_retry("http://example.com/test")
        assert resp.status_code == 200
        assert mock_session.get.call_count == 3
        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch("scholaraio.ingest.metadata._api.SESSION")
    @patch("scholaraio.ingest.metadata._api.time.sleep")
    def test_retries_503_with_exponential_backoff(self, mock_sleep, mock_session):
        mock_session.get.side_effect = [
            SimpleNamespace(status_code=503, headers={}),
            SimpleNamespace(status_code=503, headers={}),
            SimpleNamespace(status_code=200),
        ]
        resp = _request_with_retry("http://example.com/test")
        assert resp.status_code == 200
        assert mock_session.get.call_count == 3
        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch("scholaraio.ingest.metadata._api.SESSION")
    @patch("scholaraio.ingest.metadata._api.time.sleep")
    def test_returns_last_response_after_max_retries(self, mock_sleep, mock_session):
        mock_session.get.return_value = SimpleNamespace(status_code=429, headers={})
        resp = _request_with_retry("http://example.com/test", max_retries=2)
        assert resp.status_code == 429
        assert mock_session.get.call_count == 3  # initial + 2 retries
        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch("scholaraio.ingest.metadata._api.SESSION")
    @patch("scholaraio.ingest.metadata._api.time.sleep")
    def test_retry_after_capped_at_30(self, mock_sleep, mock_session):
        mock_session.get.side_effect = [
            SimpleNamespace(status_code=429, headers={"Retry-After": "100"}),
            SimpleNamespace(status_code=200),
        ]
        resp = _request_with_retry("http://example.com/test")
        assert resp.status_code == 200
        mock_sleep.assert_called_once_with(30)


class TestQuerySemanticScholarRetry:
    @patch("scholaraio.ingest.metadata._api._request_with_retry")
    def test_uses_retry_helper(self, mock_retry):
        mock_retry.return_value = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"title": "Test"},
        )
        result = query_semantic_scholar(doi="10.1234/x")
        assert result["title"] == "Test"
        mock_retry.assert_called_once()


class TestQueryOpenAlexRetry:
    @patch("scholaraio.ingest.metadata._api._request_with_retry")
    def test_uses_retry_helper(self, mock_retry):
        mock_retry.return_value = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"results": [{"title": "Test"}]},
        )
        result = query_openalex(title="Test")
        assert result["title"] == "Test"
        mock_retry.assert_called_once()


class TestQueryCrossrefRetry:
    @patch("scholaraio.ingest.metadata._api._request_with_retry")
    def test_uses_retry_helper(self, mock_retry):
        mock_retry.return_value = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"message": {"DOI": "10.1234/x"}},
        )
        result = query_crossref(doi="10.1234/x")
        assert result["DOI"] == "10.1234/x"
        mock_retry.assert_called_once()
