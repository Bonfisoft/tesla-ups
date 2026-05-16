"""Internationalization module for Tesla UPS Bridge."""

import os
from typing import Any

from .en import TRANSLATIONS as EN_TRANSLATIONS
from .haw import TRANSLATIONS as HAW_TRANSLATIONS
from .it import TRANSLATIONS as IT_TRANSLATIONS
from .nv import TRANSLATIONS as NV_TRANSLATIONS

LOCALES = {
    "en": EN_TRANSLATIONS,
    "haw": HAW_TRANSLATIONS,
    "it": IT_TRANSLATIONS,
    "nv": NV_TRANSLATIONS,
}


def get_locale(lang: str | None = None) -> dict[str, str]:
    """Get translation dictionary for the specified language.
    
    Args:
        lang: Language code (en, haw, it, nv). If None, uses environment variable 
        or defaults to 'en'.
        
    Returns:
        Dictionary of translation keys to translated strings.
    """
    if lang is None:
        lang = os.getenv("DEFAULT_LANGUAGE", "en")

    return LOCALES.get(lang.lower(), EN_TRANSLATIONS)


def _(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """Translate a key to the specified language.
    
    Args:
        key: Translation key
        lang: Language code (en, haw, it, nv). If None, uses environment variable 
        or defaults to 'en'.
        **kwargs: Format arguments for the translation string
        
    Returns:
        Translated string
    """
    translations = get_locale(lang)
    text = translations.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    return text


def detect_language_from_header(accept_language: str | None) -> str:
    """Detect language from Accept-Language HTTP header.
    
    Args:
        accept_language: Accept-Language header value (e.g., "it-IT,it;q=0.9,en-US;q=0.8")
        
    Returns:
        Language code (en or it)
    """
    if not accept_language:
        return "en"

    # Parse header and look for supported languages
    # Header format: "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
    for lang in accept_language.split(","):
        # Remove quality value if present
        lang_code = lang.split(";")[0].strip().lower()

        # Check for exact match
        if lang_code in LOCALES:
            return lang_code

        # Check for language prefix (e.g., "it-it" -> "it")
        base_code = lang_code.split("-")[0]
        if base_code in LOCALES:
            return base_code

    return "en"
