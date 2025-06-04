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

    # store ongoing dicts
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_in_progress = {}

    def parse(self, response):
        self.page_count += 1
        # find all document result links ---
        for link in response.css('a.title::attr(href)').getall():
            full_url = response.urljoin(link)
            yield scrapy.Request(full_url, callback=self.parse_document)

        # find and follow the "Next Page" button ---
        next_page = response.css('a[title="Next Page"]::attr(href)').get()
        if next_page and self.page_count < self.max_pages:
            yield response.follow(next_page, callback=self.parse)

    def parse_document(self, response):
        if self.doc_count >= self.max_docs:
            return
        self.doc_count += 1

        # save raw HTML for reference (optional)
        celex = self.extract_celex_from_url(response.url)
        soup = BeautifulSoup(response.text, "html.parser")

        if celex not in self.items_in_progress:
            self.items_in_progress[celex] = {}

        main_data = {
            "url": response.url,
            "celex": celex,
            "title": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        }
        self.items_in_progress[celex]['main'] = main_data

        expected_tabs = ["Document information", "Procedure"]
        tabs_found = 0
        for a in soup.select("ul.MenuList a"):
            tab_name = a.get_text(strip=True)
            if tab_name in expected_tabs:
                tab_url = response.urljoin(a["href"])
                tabs_found += 1
                yield scrapy.Request(
                    tab_url,
                    callback=self.parse_tab,
                    meta={"celex": celex, "tab_name": tab_name}
                )
        
        if tabs_found == 0:
            yield self.items_in_progress.pop(celex)

    def parse_tab(self, response):
        celex = response.meta.get('celex')
        tab_name = response.meta.get('tab_name')
        if not celex or not tab_name:
            return

        tab_data = extract_metadata_from_html(response.text, tab=tab_name)
        self.items_in_progress[celex][tab_name] = tab_data

        expected_tabs = set(["main", "Document information", "Procedure"])
        found_tabs = set(self.items_in_progress[celex].keys())
        if expected_tabs.issubset(found_tabs):
            combined = self.items_in_progress.pop(celex)

            merged = {}
            for section in combined.values():
                merged.update(section)
            yield merged

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
