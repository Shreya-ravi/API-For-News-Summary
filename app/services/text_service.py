import re
from urllib.parse import urlparse

from utils import translate_text

STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'have', 'will', 'into',
    'after', 'about', 'your', 'you', 'all', 'need', 'know', 'latest', 'newspaper',
    'news', 'live', 'updates', 'today', 'said', 'says'
}


def build_slug(url: str, title: str) -> str:
    title_text = (title or '').strip()
    title_text = re.sub(r'\s*\|\s*.*$', '', title_text)
    title_text = re.sub(r'\s*-\s*Latest.*$', '', title_text, flags=re.IGNORECASE)
    english_title = title_text
    if re.search(r'[^\x00-\x7F]', title_text):
        try:
            translated = translate_text(title_text, target='en', source='auto')
            if translated:
                english_title = translated
        except Exception:
            english_title = title_text

    title_words = re.findall(r'[A-Za-z0-9]+', english_title)
    filtered = [word.lower() for word in title_words if len(word) > 2]
    if filtered:
        return '-'.join(filtered[:12])

    parsed = urlparse(url)
    path = parsed.path.strip('/')
    last_part = path.split('/')[-1] if path else title_text
    last_part = re.sub(r'\.cms$', '', last_part)
    last_part = re.sub(r'-?\d+$', '', last_part)
    words = re.findall(r'[A-Za-z0-9]+', last_part)
    return '-'.join(words[:12]).lower() or 'article-summary'


def extract_keywords(text: str, limit: int = 8) -> str:
    source_text = (text or '').strip()
    if re.search(r'[^\x00-\x7F]', source_text):
        try:
            translated = translate_text(source_text[:1200], target='en', source='auto')
            if translated:
                source_text = translated
        except Exception:
            pass

    words = re.findall(r'[A-Za-z]{3,}', source_text.lower())
    clean_words = []
    seen = set()
    for word in words:
        if word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        clean_words.append(word)
    return ', '.join(clean_words[:limit])
