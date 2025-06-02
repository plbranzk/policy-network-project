import requests
import os

def download_eurlex_html(url, output_dir):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download: {url}")
    celex = url.split("CELEX:")[1] if "CELEX:" in url else "unknown"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{celex}.html")
    with open(file_path, "wb") as f:
        f.write(response.content)
    return file_path  # Path to the saved HTML file