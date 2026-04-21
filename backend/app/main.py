from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import os
import re
import csv
import io
import requests
import xml.etree.ElementTree as ET

app = FastAPI(title="Research Tool Health API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY")
PUBMED_EMAIL = os.getenv("PUBMED_EMAIL")
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")

VALID_SOURCES = {"pubmed", "scopus"}

class SearchRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    max_results: int = Field(10, ge=1, le=100)
    include_full_text: bool = False
    sources: List[str] = Field(default=list(VALID_SOURCES))

    @validator("sources")
    def validate_sources(cls, v: List[str]) -> List[str]:
        lowered = [s.lower() for s in v]
        invalid = set(lowered) - VALID_SOURCES
        if invalid:
            raise ValueError(f"Invalid source(s): {invalid}. Must be one of {VALID_SOURCES}.")
        return lowered

class Article(BaseModel):
    source: str
    title: str
    year: Optional[int]
    authors: List[str] = []
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    abstract: Optional[str] = None

class SearchResponse(BaseModel):
    topic: str
    keywords: List[str]
    articles: List[Article]
    summary: str
    critical_appraisal: str
    research_gaps: str
    evidence_quality: str
    citations_csv: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest):
    active_sources = req.sources  # already validated and lowercased

    if "pubmed" in active_sources and not PUBMED_EMAIL:
        raise HTTPException(status_code=500, detail="PUBMED_EMAIL env var is required when searching PubMed.")

    keywords = extract_keywords(req.topic)
    pubmed_articles = fetch_pubmed(keywords, req.max_results) if "pubmed" in active_sources else []
    scopus_articles = fetch_scopus(keywords, req.max_results) if "scopus" in active_sources else []
    all_articles = pubmed_articles + scopus_articles

    filtered = [a for a in all_articles if (a.language is None or a.language.lower() == "eng" or a.language.lower() == "english") and (a.year is None or a.year >= 2000)]

    summary_block = generate_appraisal(req.topic, filtered)
    csv_text = export_csv(filtered)

    return SearchResponse(
        topic=req.topic,
        keywords=keywords,
        articles=filtered,
        summary=summary_block.get("summary", "").strip(),
        critical_appraisal=summary_block.get("critical_appraisal", "").strip(),
        research_gaps=summary_block.get("research_gaps", "").strip(),
        evidence_quality=summary_block.get("evidence_quality", "").strip(),
        citations_csv=csv_text.strip(),
    )


# ----------------- Keyword Extraction -----------------

STOP_WORDS = set([
    "the", "and", "or", "of", "in", "on", "for", "a", "an", "to", "with", "by", "from",
    "is", "are", "was", "were", "be", "this", "that", "these", "those"
])


def extract_keywords(topic: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]+", topic.lower())
    keywords = [t for t in tokens if t not in STOP_WORDS]
    seen = set()
    result = []
    for k in keywords:
        if k not in seen:
            result.append(k)
            seen.add(k)
    return result[:12] if result else [topic]


# ----------------- PubMed -----------------

def fetch_pubmed(keywords: List[str], max_results: int) -> List[Article]:
    term = " AND ".join(keywords)
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    params = {
        "db": "pubmed",
        "term": term + " AND (2000:3000[pdat])",
        "retmax": max_results,
        "retmode": "json",
        "email": PUBMED_EMAIL,
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    search = requests.get(base + "esearch.fcgi", params=params, timeout=30)
    search.raise_for_status()
    ids = search.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
        "email": PUBMED_EMAIL,
    }
    if PUBMED_API_KEY:
        fetch_params["api_key"] = PUBMED_API_KEY
    fetch = requests.get(base + "efetch.fcgi", params=fetch_params, timeout=30)
    fetch.raise_for_status()

    root = ET.fromstring(fetch.text)
    articles: List[Article] = []
    for article in root.findall(".//PubmedArticle"):
        title = text_or_none(article.find(".//ArticleTitle"))
        abstract = " ".join([t.text or "" for t in article.findall(".//AbstractText")]).strip() or None
        journal = text_or_none(article.find(".//Journal/Title"))
        year = extract_year(article)
        authors = []
        for author in article.findall(".//Author"):
            last = text_or_none(author.find("LastName"))
            fore = text_or_none(author.find("ForeName"))
            if last and fore:
                authors.append(f"{fore} {last}")
        language = text_or_none(article.find(".//Language"))
        doi = text_or_none(article.find(".//ArticleId[@IdType='doi']"))
        url = f"https://pubmed.ncbi.nlm.nih.gov/{text_or_none(article.find('.//PMID'))}/"

        articles.append(Article(
            source="PubMed",
            title=title or "",
            year=year,
            authors=authors,
            journal=journal,
            doi=doi,
            url=url,
            language=language,
            abstract=abstract,
        ))
    return articles


# ----------------- Scopus -----------------

def fetch_scopus(keywords: List[str], max_results: int) -> List[Article]:
    if not SCOPUS_API_KEY:
        return []
    query = " AND ".join([f"TITLE-ABS-KEY({k})" for k in keywords])
    url = "https://api.elsevier.com/content/search/scopus"
    headers = {"X-ELS-APIKey": SCOPUS_API_KEY}
    params = {"query": query, "count": max_results}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    entries = data.get("search-results", {}).get("entry", [])
    results = []
    for e in entries:
        title = e.get("dc:title")
        year = None
        if e.get("prism:coverDate"):
            try:
                year = int(e.get("prism:coverDate").split("-")[0])
            except ValueError:
                year = None
        results.append(Article(
            source="Scopus",
            title=title or "",
            year=year,
            authors=[],
            journal=e.get("prism:publicationName"),
            doi=e.get("prism:doi"),
            url=e.get("prism:url"),
            language=None,
            abstract=e.get("dc:description"),
        ))
    return results


# ----------------- LLM Appraisal -----------------

def generate_appraisal(topic: str, articles: List[Article]) -> Dict[str, str]:
    if not OPENAI_API_KEY or not articles:
        return {
            "summary": "",
            "critical_appraisal": "",
            "research_gaps": "",
            "evidence_quality": "",
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        abstracts = []
        for a in articles[:10]:
            abstracts.append(f"Title: {a.title}\nAbstract: {a.abstract or 'N/A'}")

        prompt = (
            f"You are a health sciences literature analyst. Topic: {topic}.\n"
            "Using the provided abstracts, produce:\n"
            "1) A concise synthesis summary.\n"
            "2) A critical appraisal (strengths/limitations).\n"
            "3) Research gaps.\n"
            "4) Evidence quality assessment.\n"
            "Return JSON with keys: summary, critical_appraisal, research_gaps, evidence_quality.\n"
            "Abstracts:\n" + "\n\n".join(abstracts)
        )

        response = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
            temperature=0.2,
        )
        text = response.output_text
        return parse_json_like(text)
    except Exception:
        return {
            "summary": "",
            "critical_appraisal": "",
            "research_gaps": "",
            "evidence_quality": "",
        }


# ----------------- CSV Export -----------------

def export_csv(articles: List[Article]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Title", "Year", "Authors", "Journal", "DOI", "URL", "Language", "Abstract"])
    for a in articles:
        writer.writerow([
            a.source,
            a.title,
            a.year or "",
            "; ".join(a.authors) if a.authors else "",
            a.journal or "",
            a.doi or "",
            a.url or "",
            a.language or "",
            a.abstract or "",
        ])
    return output.getvalue()


# ----------------- Helpers -----------------

def text_or_none(elem: Optional[ET.Element]) -> Optional[str]:
    if elem is None:
        return None
    return elem.text

def extract_year(article: ET.Element) -> Optional[int]:
    year_text = text_or_none(article.find(".//JournalIssue/PubDate/Year"))
    if not year_text:
        medline = text_or_none(article.find(".//JournalIssue/PubDate/MedlineDate"))
        if medline:
            m = re.search(r"(19|20)\d{2}", medline)
            if m:
                year_text = m.group(0)
    if year_text and year_text.isdigit():
        return int(year_text)
    return None

def parse_json_like(text: str) -> Dict[str, str]:
    try:
        import json
        return json.loads(text)
    except Exception:
        sections = {
            "summary": "",
            "critical_appraisal": "",
            "research_gaps": "",
            "evidence_quality": "",
        }
        current = None
        for line in text.splitlines():
            lower = line.lower().strip()
            if "summary" in lower and current != "summary":
                current = "summary"
                continue
            if "critical" in lower:
                current = "critical_appraisal"
                continue
            if "gap" in lower:
                current = "research_gaps"
                continue
            if "evidence" in lower:
                current = "evidence_quality"
                continue
            if current:
                sections[current] += line + "\n"
        return sections
