from bs4 import BeautifulSoup
from collections import defaultdict

def parse_html(html, parser="html.parser"):
    return BeautifulSoup(html, parser)

def extract_eli(soup):
    eli_p = soup.find(lambda tag: tag.name == "p" and "ELI:" in tag.text and tag.find("a"))
    if eli_p:
        return eli_p.find("a")["href"]
    a = soup.find("a", href=lambda x: x and "data.europa.eu/eli/" in x)
    return a["href"] if a else None

def extract_dl_pairs(soup):
    for dl in soup.find_all("dl", class_="NMetadata"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            label = dt.get_text(strip=True).rstrip(":")
            yield label, dd

def extract_metadata_dl_authors(soup):
    metadata = {}
    for label, dd in extract_dl_pairs(soup):
        if label == "Author":
            metadata['author'] = [span.get_text(strip=True) for span in dd.find_all("span")]
        elif label == "Responsible body":
            metadata['responsible_body'] = dd.get_text(strip=True)
        elif label == "Form":
            metadata['document_type'] = dd.get_text(strip=True)
    return metadata

def extract_metadata_dl_dates(soup):
    result = defaultdict(list)
    for label, dd in extract_dl_pairs(soup):
        raw_value = dd.get_text(separator=" ", strip=True)
        parts = raw_value.split(";")
        date = parts[0].strip() if parts else ""
        note = ";".join(parts[1:]).strip() if len(parts) > 1 else ""
        note_spans = [s.get_text(strip=True) for s in dd.find_all("span")]
        note = " ".join(note_spans) if note_spans else note
        field = label.lower().replace(" ", "_")
        if field in ["date_of_effect", "deadline"]:
            result[field].append({"date": date, "note": note})
        else:
            if field in result:
                existing = result[field]
                if isinstance(existing, list):
                    existing.append({"date": date, "note": note})
                else:
                    result[field] = [
                        {"date": existing, "note": ""},
                        {"date": date, "note": note}
                    ]
            else:
                result[field] = date
    return dict(result)

def extract_relationships_tab_from_soup(soup):
    relationships = {}
    for label, dd in extract_dl_pairs(soup):
        if label == "Treaty":
            treaty = dd.find("span", lang="en")
            relationships['treaty'] = treaty.get_text(strip=True) if treaty else dd.get_text(strip=True)
        elif label == "Legal basis":
            legal_bases = []
            for li in dd.find_all("li"):
                a = li.find("a")
                celex = a['data-celex'] if a and 'data-celex' in a.attrs else (a.get_text(strip=True) if a else None)
                desc = li.get_text(" ", strip=True)
                legal_bases.append({"celex": celex, "description": desc})
            relationships['legal_basis'] = legal_bases
        elif label == "Proposal":
            proposals = []
            for li in dd.find_all("li"):
                a = li.find("a")
                celex = a['data-celex'] if a and 'data-celex' in a.attrs else (a.get_text(strip=True) if a else None)
                title = a['data-original-title'] if a and 'data-original-title' in a.attrs else ""
                rest = li.get_text(" ", strip=True)
                proposals.append({"celex": celex, "title": title, "description": rest})
            relationships['proposals'] = proposals
        elif label == "Instruments cited":
            instruments = []
            for li in dd.find_all("li"):
                a = li.find("a")
                celex = a['data-celex'] if a and 'data-celex' in a.attrs else (a.get_text(strip=True) if a else None)
                label = li.get_text(" ", strip=True)
                instruments.append({"celex": celex, "description": label})
            relationships['instruments_cited'] = instruments
    return relationships

def extract_classification_tab_from_soup(soup):
    results = {
        "eurovoc_descriptors": [],
        "subject_matters": [],
        "directory_codes": []
    }
    for label, dd in extract_dl_pairs(soup):
        if label == "EUROVOC descriptor":
            for li in dd.find_all("li"):
                a = li.find("a")
                if a:
                    url = a.get("href", "")
                    code = url.split("DC_CODED=")[1].split("&")[0] if "DC_CODED=" in url else None
                    label_txt = a.find("span", lang="en")
                    label_txt = label_txt.get_text(strip=True) if label_txt else a.get_text(strip=True)
                    results["eurovoc_descriptors"].append({
                        "code": code, "label": label_txt, "url": url
                    })
        elif label == "Subject matter":
            for li in dd.find_all("li"):
                a = li.find("a")
                if a:
                    url = a.get("href", "")
                    code = url.split("CT_1_CODED=")[1].split("&")[0] if "CT_1_CODED=" in url else None
                    label_txt = a.find("span", lang="en")
                    label_txt = label_txt.get_text(strip=True) if label_txt else a.get_text(strip=True)
                    results["subject_matters"].append({
                        "code": code, "label": label_txt, "url": url
                    })
        elif label == "Directory code":
            for li in dd.find_all("li"):
                code = li.contents[0].strip() if li.contents else ""
                path = []
                for a in li.find_all("a"):
                    url = a.get("href", "")
                    acode = url.split("_CODED=")[1].split("&")[0] if "CC_" in url and "_CODED=" in url else None
                    label_txt = a.find("span", lang="en")
                    label_txt = label_txt.get_text(strip=True) if label_txt else a.get_text(strip=True)
                    path.append({"code": acode, "label": label_txt, "url": url})
                results["directory_codes"].append({"code": code, "path": path})
    return results

def extract_document_text(html):
    soup = parse_html(html)
    results = {"text_blocks": [], "sections": []}
    doc_div = soup.find("div", id="document1")
    if not doc_div:
        return results
    for tag in doc_div.find_all(['table', 'img', 'hr', 'a', 'figure']):
        tag.decompose()
    for tag in doc_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            results["text_blocks"].append(text)
            if tag.name.startswith("h"):
                results["sections"].append({"level": tag.name, "title": text})
    return results

def extract_procedure_timeline(html):
    soup = parse_html(html)
    table = soup.find("table", class_="procedureTable")
    timeline = []
    if table:
        header = [th.get_text(strip=True) for th in table.find_all("th")]
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if not tds: continue
            entry = {}
            for idx, td in enumerate(tds):
                entry[header[idx].lower()] = td.get_text(strip=True)
            timeline.append(entry)
    return timeline

def extract_metadata_from_html(html, tab=None):
    """
    Main controller: extracts everything for 'Document information',
    only timeline for 'Procedure'.
    """
    soup = parse_html(html)
    if tab == "Document information":
        # All in one go!
        result = {}
        result['eli'] = extract_eli(soup)
        result.update(extract_metadata_dl_authors(soup))
        result.update(extract_metadata_dl_dates(soup))
        result.update(extract_relationships_tab_from_soup(soup))
        result.update(extract_classification_tab_from_soup(soup))
        result.update(extract_document_text(html))
        return result
    elif tab == "Procedure":
        return {"procedure_timeline": extract_procedure_timeline(html)}
    else:
        return {}
