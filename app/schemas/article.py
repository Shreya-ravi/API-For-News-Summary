from pydantic import BaseModel, Field, HttpUrl, field_validator


class SummarizeRequest(BaseModel):
    url: HttpUrl


class SummarizeResponse(BaseModel):
    title: str
    image: str
    article_text: str
    summary_english: str
    summary_original: str
    slug: str
    keywords: str
    short_url: str
    short_code: str


class ArticleDetailResponse(BaseModel):
    original_url: str
    title: str
    image: str
    article_text: str
    summary_english: str
    summary_original: str
    slug: str
    keywords: str
    short_url: str
    short_code: str


class HistoryItemResponse(BaseModel):
    title: str
    slug: str
    short_code: str
    short_url: str
    summary_english: str


class HealthResponse(BaseModel):
    status: str
    service: str
