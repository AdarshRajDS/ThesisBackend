import os
from unittest.mock import patch

import pytest

from src.llm.llm_factory import _assert_local_api_base, get_llm


def test_get_llm_uses_local_lm_studio_by_default():
    with patch("src.llm.llm_factory.get_lmstudio_llm") as mock_local:
        mock_local.return_value = object()
        get_llm(0.2)
        mock_local.assert_called_once_with(0.2)


def test_reject_groq_provider():
    with patch("src.config.settings.settings.llm_provider", "groq"):
        with pytest.raises(RuntimeError, match="disabled"):
            get_llm()


def test_reject_non_local_api_base_when_online_not_allowed():
    with patch("src.config.settings.settings.llm_allow_online", False):
        with pytest.raises(RuntimeError, match="local inference server"):
            _assert_local_api_base("https://api.groq.com/openai/v1")


def test_allow_localhost_api_base():
    with patch("src.config.settings.settings.llm_allow_online", False):
        _assert_local_api_base("http://127.0.0.1:1234/v1")


def test_warn_when_groq_env_present(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="src.llm.llm_factory"):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test"}, clear=False):
            with patch("src.llm.llm_factory.get_lmstudio_llm") as mock_local:
                mock_local.return_value = object()
                get_llm()
    assert any("GROQ_API_KEY is set but ignored" in r.message for r in caplog.records)
