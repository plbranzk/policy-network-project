from bs4 import BeautifulSoup
import re

def extract_title(soup):
    # Try different patterns if needed!
    node = soup.find("h1", class_="title")
    if node:
        return node.get_text(strip=True)
    node = soup.find("meta", {"name": "DC.title"})
    return node["content"] if node and "content" in node.attrs else None

def extract_celex(soup, html_path=None):
    # Try to extract from the page; if not, fallback to filename
    node = soup.find("meta", {"name": "DC.identifier"})
    if node and "content" in node.attrs:
        return node["content"]
    # Fallback: try to extract from file name if passed
    if html_path:
        m = re.search(r"(\d{8,})", html_path)
        return m.group(1) if m else None
    return None

def extract_document_date(soup):
    # Common date field
    node = soup.find("meta", {"name": "DC.date"})
    return node["content"] if node and "content" in node.attrs else None

def extract_doc_type(soup):
    node = soup.find("meta", {"name": "DC.type"})
    return node["content"] if node and "content" in node.attrs else None

def extract_author(soup):
    node = soup.find("meta", {"name": "DC.creator"})
    return node["content"] if node and "content" in node.attrs else None

def extract_official_journal_reference(soup):
    # These sometimes have dedicated classes, e.g. "oj-ref"
    node = soup.find(class_="oj-ref")
    return node.get_text(strip=True) if node else None