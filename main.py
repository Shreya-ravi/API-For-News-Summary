from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import re
import sqlite3

from fastapi import FastAPI, Request, Form, Cookie, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import Article
from schemas import (
    ArticleDetailResponse,
    HealthResponse,
    HistoryItemResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from utils import extract_article, summarize_text, generate_short_code, translate_text

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from",
    "have", "will", "into", "after", "about", "your",
    "you", "all", "need", "know", "latest", "newspaper",
    "news", "live", "updates", "today", "said", "says"
}


def extract_slug_from_url(url, title=""):
    title_text = (title or "").strip()
    title_text = re.sub(r"\s*\|\s*.*$", "", title_text)
    title_text = re.sub(r"\s*-\s*Latest.*$", "", title_text, flags=re.IGNORECASE)
    english_title = title_text
    if re.search(r"[^\x00-\x7F]", title_text):
        try:
            translated = translate_text(title_text, target="en", source="auto")
            if translated:
                english_title = translated
        except Exception:
            english_title = title_text

    title_words = re.findall(r"[A-Za-z0-9]+", english_title)
    filtered = [word.lower() for word in title_words if len(word) > 2]
    if filtered:
        return "-".join(filtered[:12])

    parsed = urlparse(url)
    path = parsed.path.strip("/")
    last_part = path.split("/")[-1] if path else title_text
    last_part = re.sub(r"\.cms$", "", last_part)
    last_part = re.sub(r"-?\d+$", "", last_part)
    words = re.findall(r"[A-Za-z0-9]+", last_part)
    return "-".join(words[:12]).lower() or "article-summary"


def extract_keywords_from_slug(text):
    source_text = (text or "").strip()
    if re.search(r"[^\x00-\x7F]", source_text):
        try:
            translated = translate_text(source_text[:1200], target="en", source="auto")
            if translated:
                source_text = translated
        except Exception:
            pass

    words = re.findall(r"[A-Za-z]{3,}", source_text.lower())
    clean_words = []
    seen = set()
    for word in words:
        if word in STOPWORDS or word in seen:
            continue
        seen.add(word)
        clean_words.append(word)
    return ", ".join(clean_words[:8])


def normalize_article_url(url: str) -> str:
    clean = (url or "").strip()
    parsed = urlparse(clean)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query = parsed.query
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, query=query, fragment="").geturl()


def shorten_text(text: str, length: int = 180) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    if len(clean) <= length:
        return clean
    return clean[:length].rstrip() + "..."


app = FastAPI(
    title="News Summarizer API",
    description="API for extracting news articles, generating multilingual summaries, and resolving short URLs.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="Templates" if Path("Templates").exists() else "templates")


ARTICLE_COLUMNS = {
    "title": "ALTER TABLE articles ADD COLUMN title VARCHAR",
    "article_text": "ALTER TABLE articles ADD COLUMN article_text TEXT",
    "image": "ALTER TABLE articles ADD COLUMN image VARCHAR",
    "slug": "ALTER TABLE articles ADD COLUMN slug VARCHAR",
    "keywords": "ALTER TABLE articles ADD COLUMN keywords TEXT",
    "english_summary": "ALTER TABLE articles ADD COLUMN english_summary TEXT",
    "original_summary": "ALTER TABLE articles ADD COLUMN original_summary TEXT",
    "source_language": "ALTER TABLE articles ADD COLUMN source_language VARCHAR",
    "created_at": "ALTER TABLE articles ADD COLUMN created_at VARCHAR",
    "updated_at": "ALTER TABLE articles ADD COLUMN updated_at VARCHAR",
}


def ensure_article_schema():
    connection = sqlite3.connect("news.db")
    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(articles)")
        existing = {row[1] for row in cursor.fetchall()}
        for column, statement in ARTICLE_COLUMNS.items():
            if column not in existing:
                cursor.execute(statement)

        now = datetime.utcnow().isoformat()
        if "created_at" not in existing:
            cursor.execute("UPDATE articles SET created_at = ? WHERE created_at IS NULL", (now,))
        if "updated_at" not in existing:
            cursor.execute("UPDATE articles SET updated_at = ? WHERE updated_at IS NULL", (now,))

        connection.commit()
    finally:
        connection.close()


ensure_article_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_unique_code(db: Session):
    while True:
        code = generate_short_code()
        if not db.query(Article).filter(Article.short_code == code).first():
            return code


def build_short_url(request: Request, article: Article):
    return request.url_for("redirect_short_url", code=article.short_code)


def get_recent_articles(db: Session, limit: int = 10):
    articles = db.query(Article).order_by(Article.id.desc()).all()
    unique_articles = []
    seen_urls = set()
    for article in articles:
        normalized = normalize_article_url(article.original_url or "")
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)
        article.preview_summary = shorten_text(article.english_summary, 160)
        article.preview_keywords = shorten_text(article.keywords, 80)
        unique_articles.append(article)
        if len(unique_articles) >= limit:
            break
    return unique_articles


def create_article_record(url: str, db: Session):
    normalized_url = normalize_article_url(url)
    existing_articles = db.query(Article).order_by(Article.id.desc()).all()
    for article in existing_articles:
        if normalize_article_url(article.original_url or "") == normalized_url:
            return article

    data = extract_article(url)
    if not data["text"]:
        raise ValueError("Could not extract full article content from this URL.")

    summaries = summarize_text(data["text"])
    title = data["title"]
    article_text = data["text"]
    image = data["image"]
    slug = extract_slug_from_url(url, title)
    keywords = extract_keywords_from_slug(f"{title} {article_text}")
    short_code = create_unique_code(db)

    article = Article(
        original_url=url,
        short_code=short_code,
        title=title,
        article_text=article_text,
        image=image,
        slug=slug,
        keywords=keywords,
        english_summary=summaries["english"],
        original_summary=summaries["original"],
        source_language=summaries.get("language"),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def render_result(request: Request, article: Article):
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "title": article.title,
            "article_text": article.article_text,
            "summary_english": article.english_summary,
            "summary_original": article.original_summary,
            "image": article.image,
            "slug": article.slug,
            "keywords": article.keywords,
            "short_url": build_short_url(request, article),
        },
    )


def serialize_article(request: Request, article: Article):
    return ArticleDetailResponse(
        original_url=article.original_url or "",
        title=article.title or "",
        image=article.image or "",
        article_text=article.article_text or "",
        summary_english=article.english_summary or "",
        summary_original=article.original_summary or "",
        slug=article.slug or "",
        keywords=article.keywords or "",
        short_url=build_short_url(request, article),
        short_code=article.short_code or "",
    )


def serialize_history_item(request: Request, article: Article):
    return HistoryItemResponse(
        title=article.title or "",
        slug=article.slug or "",
        short_code=article.short_code or "",
        short_url=build_short_url(request, article),
        summary_english=article.english_summary or "",
    )


@app.get("/api/health", response_model=HealthResponse, tags=["API"])
def health_check():
    return HealthResponse(status="ok", service="news-summarizer")


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "admin":
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(key="user", value=username)
        return response
    return templates.TemplateResponse("index.html", {"request": request, "error": "Invalid credentials"})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: str = Cookie(None), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "recent_articles": get_recent_articles(db),
            "current_user": user,
        },
    )


@app.get("/summarize")
def summarize_page_redirect(user: str = Cookie(None)):
    if not user:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/summarize")
def summarize(request: Request, url: str = Form(...), db: Session = Depends(get_db), user: str = Cookie(None)):
    if not user:
        return RedirectResponse("/", status_code=302)

    try:
        article = create_article_record(url, db)
        return render_result(request, article)
    except Exception as exc:
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": str(exc),
                "recent_articles": get_recent_articles(db),
                "current_user": user,
            },
            status_code=400,
        )


@app.post("/api/summarize", response_model=SummarizeResponse, tags=["API"])
def summarize_api(payload: SummarizeRequest, request: Request, db: Session = Depends(get_db)):
    try:
        article = create_article_record(str(payload.url), db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    data = serialize_article(request, article).model_dump(exclude={"original_url"})
    return SummarizeResponse(**data)


@app.get("/api/article/{code}", response_model=ArticleDetailResponse, tags=["API"])
def get_article_api(code: str, request: Request, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.short_code == code).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return serialize_article(request, article)


@app.get("/api/history", response_model=list[HistoryItemResponse], tags=["API"])
def get_history_api(request: Request, limit: int = 10, db: Session = Depends(get_db)):
    articles = get_recent_articles(db, limit=limit)
    return [serialize_history_item(request, article) for article in articles]


@app.get("/s/{code}", response_class=HTMLResponse, name="redirect_short_url")
def redirect_short_url(request: Request, code: str, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.short_code == code).first()
    if not article:
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Invalid URL",
                "recent_articles": get_recent_articles(db),
            },
            status_code=404,
        )
    return render_result(request, article)


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("user")
    return response
