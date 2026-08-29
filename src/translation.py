import re
from difflib import SequenceMatcher

import requests
from deep_translator import GoogleTranslator


DATAMUSE_URL = "https://api.datamuse.com/sug"
DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
DATAMUSE_TIMEOUT = 2
DICTIONARY_TIMEOUT = 25


def translate_en_to_zh_tw(text: str) -> str:
    return GoogleTranslator(source="en", target="zh-TW").translate(text)


def single_english_word(text: str) -> str | None:
    match = re.fullmatch(r"\s*[^A-Za-z]*([A-Za-z]+(?:[-'’][A-Za-z]+)*)[^A-Za-z]*\s*", text)
    return match.group(1).replace("’", "'").lower() if match else None


def suggest_word(word: str) -> str | None:
    response = requests.get(
        DATAMUSE_URL, params={"s": word, "max": 5}, timeout=DATAMUSE_TIMEOUT
    )
    response.raise_for_status()
    candidates = [item.get("word", "").lower() for item in response.json()]
    if word.lower() in candidates:
        return None
    for candidate in candidates:
        if (
            re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", candidate)
            and SequenceMatcher(None, word.lower(), candidate).ratio() >= 0.72
        ):
            return candidate
    return None


def lookup_dictionary(word: str) -> dict | None:
    response = requests.get(
        DICTIONARY_URL.format(word=word), timeout=DICTIONARY_TIMEOUT
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    entries = response.json()
    if not isinstance(entries, list) or not entries:
        return None
    entry = entries[0]
    meanings = []
    for meaning in entry.get("meanings", [])[:4]:
        definitions = []
        synonyms = list(meaning.get("synonyms", []))
        for definition in meaning.get("definitions", [])[:2]:
            text = definition.get("definition")
            if text:
                definitions.append({"definition": text, "example": definition.get("example")})
            synonyms.extend(definition.get("synonyms", []))
        unique_synonyms = list(dict.fromkeys(item for item in synonyms if item))[:6]
        if definitions:
            meanings.append({
                "part_of_speech": meaning.get("partOfSpeech", ""),
                "definitions": definitions,
                "synonyms": unique_synonyms,
            })
    if not meanings:
        return None
    return {
        "word": entry.get("word", word),
        "phonetic": entry.get("phonetic", ""),
        "meanings": meanings,
    }


def lookup_inline(text: str, progress=None) -> dict:
    result = {
        "translation": None, "suggestion": None, "dictionary": None,
        "dictionary_status": None, "word": None,
    }
    word = single_english_word(text)
    result["word"] = word

    def emit():
        if progress:
            progress(result.copy())

    try:
        result["translation"] = translate_en_to_zh_tw(text)
    except Exception:
        pass
    if result["translation"]:
        emit()
    if not word:
        if not result["translation"]:
            emit()
        return result

    try:
        result["suggestion"] = suggest_word(word)
    except Exception:
        pass
    if result["suggestion"]:
        try:
            result["translation"] = translate_en_to_zh_tw(result["suggestion"])
        except Exception:
            pass
        emit()
    try:
        result["dictionary"] = lookup_dictionary(result["suggestion"] or word)
        result["dictionary_status"] = (
            "found" if result["dictionary"] else "not_found"
        )
    except requests.Timeout:
        result["dictionary_status"] = "timeout"
    except Exception:
        result["dictionary_status"] = "unavailable"
    emit()
    return result
