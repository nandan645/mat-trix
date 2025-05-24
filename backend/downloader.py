import os
import json
import subprocess
from urllib.parse import urlparse

DOWNLOAD_DIR = "pdf_documents"  # Change this to your preferred folder
JSON_FILE = "materials/nature_articles.json"  # Change this if your JSON file has a different name

# Create the download directory if it doesn't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Load the JSON data
with open(JSON_FILE, "r") as file:
    articles = json.load(file)

# Process each article
for article in articles:
    original_url = article.get("URL")
    if not original_url:
        continue

    pdf_url = original_url + ".pdf"
    file_name = os.path.basename(urlparse(pdf_url).path)
    file_path = os.path.join(DOWNLOAD_DIR, file_name)

    if os.path.exists(file_path):
        print(f"Skipping (already exists): {file_path}")
        continue

    print(f"Downloading: {file_name}")
    subprocess.run(["aria2c", "-d", DOWNLOAD_DIR, pdf_url])
