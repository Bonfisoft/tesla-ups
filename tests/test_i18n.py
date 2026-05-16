"""Tests for internationalization module."""

import pytest

from i18n import _, detect_language_from_header, get_locale


class TestGetLocale:
    """Test get_locale function."""

    def test_get_locale_english(self):
        """Test getting English locale."""
        locale = get_locale("en")
        assert locale["dashboard.title"] == "UPS Bridge Status"
        assert locale["status.online"] == "Online"

    def test_get_locale_italian(self):
        """Test getting Italian locale."""
        locale = get_locale("it")
        assert locale["dashboard.title"] == "Stato UPS Bridge"
        assert locale["status.online"] == "Online"

    def test_get_locale_default(self):
        """Test default locale is English."""
        locale = get_locale(None)
        assert locale["dashboard.title"] == "UPS Bridge Status"

    def test_get_locale_invalid(self):
        """Test invalid locale falls back to English."""
        locale = get_locale("fr")  # French not supported
        assert locale["dashboard.title"] == "UPS Bridge Status"

    def test_get_locale_case_insensitive(self):
        """Test locale codes are case insensitive."""
        assert get_locale("EN")["dashboard.title"] == "UPS Bridge Status"
        assert get_locale("IT")["dashboard.title"] == "Stato UPS Bridge"
        assert get_locale("En")["dashboard.title"] == "UPS Bridge Status"


class TestTranslateFunction:
    """Test the _() translation function."""

    def test_translate_english(self):
        """Test English translation."""
        assert _("dashboard.title", "en") == "UPS Bridge Status"
        assert _("status.online", "en") == "Online"

    def test_translate_italian(self):
        """Test Italian translation."""
        assert _("dashboard.title", "it") == "Stato UPS Bridge"
        assert _("status.on_battery", "it") == "Su Batteria"

    def test_translate_with_formatting(self):
        """Test translation with string formatting."""
        result = _("alert.grid_outage", "en", soe=75)
        assert result == "Grid outage detected! Battery at 75%"

    def test_translate_italian_with_formatting(self):
        """Test Italian translation with string formatting."""
        result = _("alert.grid_outage", "it", soe=75)
        assert result == "Rilevata interruzione di rete! Batteria al 75%"

    def test_translate_missing_key(self):
        """Test missing key returns key itself."""
        assert _("nonexistent.key", "en") == "nonexistent.key"

    def test_translate_default_language(self):
        """Test default language when lang is None."""
        assert _("dashboard.title") == "UPS Bridge Status"


class TestDetectLanguageFromHeader:
    """Test language detection from Accept-Language header."""

    def test_detect_italian_exact(self):
        """Test detecting Italian language code."""
        assert detect_language_from_header("it") == "it"

    def test_detect_italian_with_region(self):
        """Test detecting Italian with region code."""
        assert detect_language_from_header("it-IT") == "it"
        assert detect_language_from_header("it-CH") == "it"

    def test_detect_english(self):
        """Test detecting English."""
        assert detect_language_from_header("en") == "en"
        assert detect_language_from_header("en-US") == "en"
        assert detect_language_from_header("en-GB") == "en"

    def test_detect_with_quality_values(self):
        """Test parsing header with quality values."""
        header = "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
        assert detect_language_from_header(header) == "it"

    def test_detect_english_first(self):
        """Test when English is first in header."""
        header = "en-US,en;q=0.9,it-IT;q=0.8"
        assert detect_language_from_header(header) == "en"

    def test_detect_empty_header(self):
        """Test empty header returns default."""
        assert detect_language_from_header("") == "en"
        assert detect_language_from_header(None) == "en"

    def test_detect_unsupported_language(self):
        """Test unsupported language falls back to English."""
        assert detect_language_from_header("fr-FR,fr;q=0.9") == "en"
        assert detect_language_from_header("de-DE") == "en"

    def test_detect_mixed_supported_and_unsupported(self):
        """Test mixing supported and unsupported languages."""
        header = "fr-FR,fr;q=0.9,it-IT;q=0.8,en;q=0.7"
        assert detect_language_from_header(header) == "it"


class TestTranslationCompleteness:
    """Test that all translations have the same keys."""

    def test_all_keys_present_in_italian(self):
        """Test Italian has all the same keys as English."""
        from i18n.en import TRANSLATIONS as EN
        from i18n.it import TRANSLATIONS as IT

        en_keys = set(EN.keys())
        it_keys = set(IT.keys())

        assert en_keys == it_keys, f"Missing keys: {en_keys - it_keys}"

    def test_no_empty_translations(self):
        """Test no translations are empty strings."""
        from i18n.en import TRANSLATIONS as EN
        from i18n.it import TRANSLATIONS as IT

        for key, value in EN.items():
            assert value.strip(), f"Empty English translation for {key}"

        for key, value in IT.items():
            assert value.strip(), f"Empty Italian translation for {key}"
