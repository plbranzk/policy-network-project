# src/scraping/eurolex_spider.py

import scrapy
from bs4 import BeautifulSoup
from src.parsing.meta_extractor import extract_metadata_from_html

class EurolexSpider(scrapy.Spider):
    name = 'eurolex'
    start_urls = [
        'https://eur-lex.europa.eu/search.html?scope=EURLEX&lang=en&type=quick&qid=1748872546646'
    ]
    page_count = 0
    max_pages = 2
    doc_count = 0
    max_docs = 5

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def parse(self, response):
        self.page_count += 1

        # --- 1. Find all document result links ---
        for link in response.css('a.title::attr(href)').getall():
            full_url = response.urljoin(link)
            yield scrapy.Request(full_url, callback=self.parse_document)

        # --- 2. Find and follow the "Next Page" button ---
        next_page = response.css('a[title="Next Page"]::attr(href)').get()
        if next_page and self.page_count < self.max_pages:
            yield response.follow(next_page, callback=self.parse)

    def parse_document(self, response):
        if self.doc_count >= self.max_docs:
            return
        self.doc_count += 1

        # Save raw HTML for reference (optional)
        celex = self.extract_celex_from_url(response.url)
        raw_path = f"data/raw/{celex}.html" if celex else "data/raw/unknown_celex.html"
        with open(raw_path, "wb") as f:
            f.write(response.body)

        # Use BeautifulSoup for metadata extraction
        soup = BeautifulSoup(response.text, "html.parser")
        metadata = {
            "url": response.url,
            "celex": celex,
            "title": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
            # ...add more fields (later from meta_extractor)
        }
        yield metadata

    @staticmethod
    def extract_celex_from_url(url):
        # Try to find the CELEX number in the URL
        import re
        m = re.search(r'CELEX:([0-9A-Z]+)', url)
        if m:
            return m.group(1)
        # Fallback: sometimes in query param
        m = re.search(r'uri=CELEX:([0-9A-Z]+)', url)
        return m.group(1) if m else None
