from deep_translator import GoogleTranslator


def translate_en_to_zh_tw(text: str) -> str:
    return GoogleTranslator(source="en", target="zh-TW").translate(text)
