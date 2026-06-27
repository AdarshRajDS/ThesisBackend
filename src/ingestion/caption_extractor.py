import re

CAPTION_PATTERN = r"(Figure\s+\d+(?:\.\d+)?[:.]?\s.*)"

def extract_caption(text: str):

    if not text:
        return None

    match = re.search(CAPTION_PATTERN, text, re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None