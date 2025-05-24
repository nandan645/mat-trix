import re
from pathlib import Path

import fitz


def extract_metadata_from_pdf(pdf_path: Path) -> dict:
    """
    Extracts DOI and title from a PDF.
    Tries to get DOI and title from PDF metadata first, then from text.
    Does NOT extract full text here, as PyPDFLoader will handle that.
    """
    metadata = {
        "source_file": pdf_path.name,
        "title": "Unknown Title",
        "doi": "Unknown DOI",
    }
    try:
        doc = fitz.open(pdf_path)
        pdf_meta = doc.metadata
        if pdf_meta:
            if pdf_meta.get("title"):
                metadata["title"] = pdf_meta["title"]
            if pdf_meta.get("doi"):
                metadata["doi"] = pdf_meta["doi"]

        if metadata["doi"] == "Unknown DOI" or metadata["title"] == "Unknown Title":
            for page_num in range(min(3, doc.page_count)):
                page = doc.load_page(page_num)
                text = page.get_text("text")  # Direct call is cleaner

                if metadata["doi"] == "Unknown DOI":
                    doi_match = re.search(
                        r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.IGNORECASE
                    )
                    if doi_match:
                        metadata["doi"] = doi_match.group(0)

                if metadata["title"] == "Unknown Title" and page_num == 0:
                    lines = text.split("\n")
                    if lines:
                        for line in lines:
                            cleaned_line = line.strip()
                            if len(cleaned_line) > 10 and cleaned_line.lower() not in [
                                "article",
                                "research article",
                                "review",
                                "abstract",
                                "introduction",
                            ]:
                                if not re.match(
                                    r"^(https?://|www\.)", cleaned_line
                                ) and not re.match(r"^\d+$", cleaned_line):
                                    potential_title = cleaned_line
                                    if not re.search(
                                        r"(\w+\s+\w+(\s*,\s*|\s+and\s+))",
                                        potential_title,
                                        re.IGNORECASE,
                                    ):
                                        metadata["title"] = potential_title
                                        break
    except Exception as e:
        print(f"Error extracting metadata for {pdf_path}: {e}")
    return metadata


def construct_nature_url_from_doi(doi: str) -> str:
    if doi and doi != "Unknown DOI" and doi.startswith("10."):
        return f"https://doi.org/{doi}"
    return "URL N/A"


if __name__ == "__main__":
    test_pdf_path = Path("pdf_documents/test_article.pdf")
    if test_pdf_path.exists():
        meta = extract_metadata_from_pdf(test_pdf_path)
        print(meta)
    else:
        print(f"{test_pdf_path} not found. Create a dummy PDF for testing.")
