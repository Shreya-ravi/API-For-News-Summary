from newspaper import Article
from transformers import pipeline
import json
import random
import string
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8,kn;q=0.8,ta;q=0.8,te;q=0.8,ml;q=0.8,bn;q=0.8",
}

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

SCRIPT_LANGUAGE_PATTERNS = [
    ("kn", r"[\u0C80-\u0CFF]"),
    ("hi", r"[\u0900-\u097F]"),
    ("mr", r"[\u0900-\u097F]"),
    ("ne", r"[\u0900-\u097F]"),
    ("ta", r"[\u0B80-\u0BFF]"),
    ("te", r"[\u0C00-\u0C7F]"),
    ("ml", r"[\u0D00-\u0D7F]"),
    ("bn", r"[\u0980-\u09FF]"),
    ("gu", r"[\u0A80-\u0AFF]"),
    ("pa", r"[\u0A00-\u0A7F]"),
]

NON_LATIN_PATTERN = r"[\u0C80-\u0CFF\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F\u0980-\u09FF\u0A80-\u0AFF\u0A00-\u0A7F]"
SUMMARY_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "will", "into",
    "after", "about", "your", "you", "all", "need", "know", "said", "says", "was",
    "were", "are", "has", "had", "its", "their", "they", "them", "than", "then",
    "also", "more", "most", "very", "just", "here", "there", "what", "when", "where",
    "which", "while", "over", "under", "between", "through", "because", "been"
}
NOISE_PATTERNS = [
    r"^also read[:\s-]",
    r"^read more[:\s-]",
    r"^follow us[:\s-]",
    r"^for latest",
    r"^subscribe",
    r"^advertisement$",
    r"^photo[:\s-]",
    r"^video[:\s-]",
    r"senior political correspondent",
    r"working in kannada journalism",
    r"recent work on",
]


def normalize_text(text):
    text = text or ""
    text = text.replace("\r", "\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def strip_html(value):
    if not value:
        return ""
    if "<" in value and ">" in value:
        value = BeautifulSoup(value, "html.parser").get_text("\n", strip=True)
    return normalize_text(value)


def clean_article_text(text, title=""):
    clean = normalize_text(text)
    if not clean:
        return ""

    paragraphs = [part.strip() for part in re.split(r"\n\n+|\n", clean) if part.strip()]
    cleaned_paragraphs = []
    seen = set()
    title_norm = normalize_text(title).lower()

    for paragraph in paragraphs:
        paragraph_norm = normalize_text(paragraph)
        paragraph_key = paragraph_norm.lower()
        if paragraph_key in seen:
            continue
        if title_norm and paragraph_key == title_norm:
            continue
        if len(paragraph_norm.split()) < 6:
            continue
        if any(re.search(pattern, paragraph_key, flags=re.IGNORECASE) for pattern in NOISE_PATTERNS):
            continue
        seen.add(paragraph_key)
        cleaned_paragraphs.append(paragraph_norm)

    return normalize_text("\n\n".join(cleaned_paragraphs))


def validate_url(url):
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Please enter a valid article URL.")
    return url.strip()


def fetch_html(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def pick_image(soup):
    for selector, attr in [
        ('meta[property="og:image"]', 'content'),
        ('meta[name="twitter:image"]', 'content'),
        ('article img', 'src'),
        ('.article-content img', 'src'),
        ('img', 'src'),
    ]:
        node = soup.select_one(selector)
        if node:
            value = node.get(attr, "")
            if value:
                return value
    return ""


def build_absolute_url(url):
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("/"):
        return f"https://udayavani.com{url}"
    return url


def extract_json_ld_text(soup):
    texts = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            for key in ["articleBody", "description", "headline", "name"]:
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    texts.append(value.strip())
    return normalize_text("\n\n".join(texts))


def walk_json_strings(node, bucket):
    if isinstance(node, dict):
        preferred_keys = {
            "articleBody", "content", "body", "description", "summary",
            "text", "story", "storyContent", "contentRendered"
        }
        for key, value in node.items():
            if key in preferred_keys and isinstance(value, str):
                cleaned = strip_html(value)
                if len(cleaned) > 80:
                    bucket.append(cleaned)
            walk_json_strings(value, bucket)
    elif isinstance(node, list):
        for item in node:
            walk_json_strings(item, bucket)


def extract_embedded_json_text(soup):
    texts = []
    for script in soup.find_all("script"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        raw = raw.strip()
        if not raw:
            continue
        candidates = [raw]
        if "self.__next_f.push" in raw or "\\\"" in raw:
            candidates.append(raw.replace('\\"', '"'))
        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except Exception:
                continue
            walk_json_strings(data, texts)
    unique = []
    seen = set()
    for text in texts:
        if text not in seen:
            seen.add(text)
            unique.append(text)
    return normalize_text("\n\n".join(unique))


def extract_news_details(html):
    obj = None
    for marker in ['newsDetails\\":{', '"newsDetails":{', "newsDetails\":{\""]:
        start = html.find(marker)
        if start == -1:
            continue

        decoder = json.JSONDecoder()
        raw = html[start + len(marker) - 1:]
        try:
            obj, _ = decoder.raw_decode(raw)
            break
        except Exception:
            continue

    if not isinstance(obj, dict):
        obj = {}

    news_section = obj.get("news_section") or ""
    if not news_section:
        match = re.search(r'news_section\\?":\\?"(?P<path>/test-news/news-json/[^"\\]+\.json)', html)
        if match:
            news_section = match.group("path")

    image = ""
    rep = obj.get("representativeImage")
    if isinstance(rep, dict):
        image = rep.get("full") or rep.get("medium") or rep.get("mobile_large") or ""
        if image and image.startswith("/"):
            image = f"https://d3jde0c4xcko0v.cloudfront.net/production{image}"

    if not image:
        image_match = re.search(r'https://d3jde0c4xcko0v\.cloudfront\.net/production/[^"\']+\.(?:webp|jpg|jpeg|png)', html)
        if image_match:
            image = image_match.group(0)

    return {
        "title": normalize_text(obj.get("title") or "No Title"),
        "second_title": normalize_text(obj.get("secondTitle") or ""),
        "description": normalize_text(obj.get("description") or obj.get("summary") or ""),
        "image": image,
        "news_section": news_section,
    }


def extract_candidate_news_sections(html):
    matches = re.findall(r'(/(?:test-news|news)/news-json/[A-Za-z0-9_-]+\.json)', html)
    ordered = []
    seen = set()
    for item in matches:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def fetch_udayavani_news_section(news_section):
    if not news_section:
        return ""

    endpoint = f"https://udayavani.com/api/newsSectioncfr?src={requests.utils.quote(news_section, safe='')}"
    response = requests.get(endpoint, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    blocks = []
    for node in soup.find_all(["p", "div", "li"]):
        text = node.get_text(" ", strip=True)
        if len(text.split()) > 5:
            blocks.append(text)

    if not blocks:
        return normalize_text(soup.get_text("\n", strip=True))

    return normalize_text("\n\n".join(blocks))


def fetch_best_udayavani_article(html):
    details = extract_news_details(html)
    candidates = []

    if details and details.get("news_section"):
        candidates.append(details["news_section"])

    for item in extract_candidate_news_sections(html):
        if item not in candidates:
            candidates.append(item)

    best_text = ""
    for news_section in candidates:
        try:
            article_body = fetch_udayavani_news_section(news_section)
        except Exception:
            continue
        if len(article_body) > len(best_text):
            best_text = article_body

    return best_text, details


def extract_with_bs4(html):
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    for selector, attr in [
        ('meta[property="og:title"]', 'content'),
        ('meta[name="twitter:title"]', 'content'),
        ('h1', None),
        ('title', None),
    ]:
        node = soup.select_one(selector)
        if node:
            title = node.get(attr, "") if attr else node.get_text(" ", strip=True)
            if title:
                break

    description = ""
    for selector in [
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[name="twitter:description"]',
    ]:
        node = soup.select_one(selector)
        if node and node.get("content"):
            description = node.get("content", "")
            break

    paragraphs = []
    selectors = [
        'article p',
        'main p',
        '[itemprop="articleBody"] p',
        '[data-testid="article-body"] p',
        '[data-component="text-block"] p',
        '[class*="article"] p',
        '[class*="story"] p',
        '[class*="content"] p',
        '.article-content p',
        '.post-content p',
        '.entry-content p',
        '.story-content p',
        '.content p',
    ]
    for selector in selectors:
        items = [p.get_text(" ", strip=True) for p in soup.select(selector)]
        items = [item for item in items if len(item.split()) > 5]
        if len(items) >= 2:
            paragraphs = items
            break

    if not paragraphs:
        all_items = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paragraphs = [item for item in all_items if len(item.split()) > 5]

    text = normalize_text("\n\n".join(paragraphs))
    article_body, news_details = fetch_best_udayavani_article(html)

    if len(article_body) > len(text):
        text = article_body
    if news_details:
        if not title or (
            news_details["title"]
            and title
            and news_details["title"] in title
            and len(news_details["title"]) < len(title)
        ):
            title = news_details["title"]

    if len(text) < 120:
        fallback_text = normalize_text(
            "\n\n".join(
                value for value in [
                    news_details["title"] if news_details else "",
                    news_details["second_title"] if news_details else "",
                    news_details["description"] if news_details else "",
                ]
                if value
            )
        )
        if len(fallback_text) > len(text):
            text = fallback_text
            if not title:
                title = news_details["title"]

    if len(text) < 120:
        json_ld_text = extract_json_ld_text(soup)
        text = json_ld_text if len(json_ld_text) > len(text) else text

    if len(text) < 120:
        embedded_text = extract_embedded_json_text(soup)
        text = embedded_text if len(embedded_text) > len(text) else text

    if len(text) < 120 and description:
        text = normalize_text(f"{description}\n\n{text}" if text else description)

    image = pick_image(soup)
    if not image:
        if news_details:
            image = news_details["image"]
    image = build_absolute_url(image)

    return {
        "title": normalize_text(title),
        "text": text,
        "image": image,
    }


def extract_article(url):
    clean_url = validate_url(url)

    try:
        html = fetch_html(clean_url)
    except Exception:
        html = ""

    if html:
        try:
            article = Article(clean_url)
            article.set_html(html)
            article.parse()

            fallback = extract_with_bs4(html)
            text = clean_article_text(article.text, article.title)
            if len(text) < len(fallback["text"]):
                text = fallback["text"]
            title = normalize_text(article.title) or fallback["title"] or "No Title"
            image = article.top_image or fallback["image"]

            return {
                "title": title,
                "text": text,
                "image": image,
                "url": clean_url,
            }
        except Exception:
            fallback = extract_with_bs4(html)
            return {
                "title": fallback["title"] or "No Title",
                "text": clean_article_text(fallback["text"], fallback["title"]),
                "image": fallback["image"],
                "url": clean_url,
            }

    return {
        "title": "Error",
        "text": "",
        "image": "",
        "url": clean_url,
    }


def split_text(text, limit=1200):
    text = normalize_text(text)
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    parts = re.split(r"(?<=[.!?\u0964\u0C64])\s+|\n\n+", text)
    chunks = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        candidate = f"{current} {part}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = part
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text[i:i + limit] for i in range(0, len(text), limit)]


def simple_fallback_summary(text, max_sentences=4):
    clean = normalize_text(text)
    if not clean:
        return "No content found."
    parts = re.split(r"(?<=[.!?\u0964\u0C64])\s+", clean)
    summary = " ".join(parts[:max_sentences]).strip()
    return summary or clean[:400]


def split_sentences(text):
    clean = normalize_text(text)
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?\u0964\u0C64])\s+|\n+", clean)
    return [part.strip() for part in parts if part and len(part.strip().split()) >= 5]


def extractive_summary(text, max_sentences=4):
    sentences = split_sentences(text)
    if not sentences:
        return simple_fallback_summary(text, max_sentences=max_sentences)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    freq = {}
    for word in words:
        if word in SUMMARY_STOPWORDS:
            continue
        freq[word] = freq.get(word, 0) + 1

    scored = []
    for index, sentence in enumerate(sentences):
        sentence_words = re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())
        if not sentence_words:
            score = 0
        else:
            score = sum(freq.get(word, 0) for word in sentence_words) / max(len(sentence_words), 1)
        position_bonus = max(0, 1.5 - (index * 0.1))
        scored.append((score + position_bonus, index, sentence))

    selected = sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences]
    selected = sorted(selected, key=lambda item: item[1])
    summary = " ".join(sentence for _, _, sentence in selected).strip()
    return summary or simple_fallback_summary(text, max_sentences=max_sentences)


def translate_text(text, target='en', source='auto'):
    chunks = split_text(text, 2500)
    translated = []
    for chunk in chunks:
        last_error = None
        for source_code in [source, "auto"]:
            try:
                response = requests.get(
                    "https://translate.googleapis.com/translate_a/single",
                    params={
                        "client": "gtx",
                        "sl": source_code,
                        "tl": target,
                        "dt": "t",
                        "q": chunk,
                    },
                    headers=HEADERS,
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()
                translated_chunk = "".join(item[0] for item in data[0] if item and item[0])
                if translated_chunk:
                    translated.append(translated_chunk)
                    last_error = None
                    break
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
    return normalize_text("\n\n".join(translated))


def detect_language(text):
    sample = normalize_text(text)[:800]
    if not sample:
        return "en"

    for code, pattern in SCRIPT_LANGUAGE_PATTERNS:
        if re.search(pattern, sample):
            return code

    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "en",
                "dt": "t",
                "q": sample,
            },
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data[2] if len(data) > 2 and data[2] else "en"
    except Exception:
        return "en"


def contains_non_latin(text):
    return bool(re.search(NON_LATIN_PATTERN, text or ""))


def summarize_english_text(text):
    clean = normalize_text(text)
    if not clean:
        raise ValueError("No content found for summarization.")

    word_count = len(clean.split())
    if word_count < 45:
        return simple_fallback_summary(clean)
    extractive = extractive_summary(clean, max_sentences=4)

    chunks = split_text(clean, 1000)
    if len(chunks) == 1 and word_count < 220:
        return extractive

    try:
        partial = []
        for chunk in chunks[:3]:
            chunk_words = len(chunk.split())
            if chunk_words < 35:
                partial.append(extractive_summary(chunk, max_sentences=2))
                continue
            max_length = min(90, max(25, int(chunk_words * 0.35)))
            min_length = min(max_length - 5, max(10, int(chunk_words * 0.16)))
            if max_length >= chunk_words:
                max_length = max(20, chunk_words - 5)
            if min_length >= max_length:
                min_length = max(8, max_length - 8)
            if max_length <= min_length:
                partial.append(extractive_summary(chunk, max_sentences=2))
                continue
            result = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            partial.append(result[0]["summary_text"].strip())

        combined = " ".join(partial).strip()
        if not combined:
            return extractive
        if len(combined.split()) > len(extractive.split()) * 2:
            return extractive
        return combined
    except Exception:
        return extractive


def summarize_text(text):
    clean = clean_article_text(text)
    if not clean:
        return {
            "english": "No content found.",
            "original": "No content found.",
            "language": "en",
        }

    language = detect_language(clean)
    original_summary = extractive_summary(clean, max_sentences=5)

    if language == "en":
        english_summary = summarize_english_text(clean)
        original_summary = english_summary
    else:
        try:
            english_summary = translate_text(original_summary, target="en", source=language)
        except Exception:
            try:
                english_source = translate_text(clean, target="en", source="auto")
                english_summary = summarize_english_text(english_source)
            except Exception:
                english_summary = "English summary is unavailable for this article."

    if contains_non_latin(english_summary):
        try:
            english_summary = translate_text(english_summary, target="en", source="auto")
        except Exception:
            english_summary = "English summary is unavailable for this article."

    return {
        "english": english_summary,
        "original": original_summary,
        "language": language,
    }


def generate_short_code(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=length))
