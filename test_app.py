from utils import extract_article, summarize_text

url = "https://example.com/news"

data = extract_article(url)
print("TITLE:", data["title"])
print("TEXT:", data["text"][:500])

summary = summarize_text(data["text"])
print("ENGLISH SUMMARY:", summary["english"])
