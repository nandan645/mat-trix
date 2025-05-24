import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from utils import extract_metadata_from_pdf

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

PDF_DIRECTORY = Path("pdf_documents")
CHROMA_PERSIST_DIRECTORY = Path("chroma_db")
CHROMA_COLLECTION_NAME = "scientific_articles"
PROCESSED_FILES_LOG = CHROMA_PERSIST_DIRECTORY / "processed_files.json"

EMBEDDING_MODEL_NAME = "models/text-embedding-004"
embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL_NAME, google_api_key=SecretStr(GOOGLE_API_KEY)
)

client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIRECTORY))

collection = client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME,
    embedding_function=None,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)


def load_processed_files_log():
    if PROCESSED_FILES_LOG.exists():
        with open(PROCESSED_FILES_LOG, "r") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_processed_files_log(processed_files_set):
    with open(PROCESSED_FILES_LOG, "w") as f:
        json.dump(list(processed_files_set), f)


def has_embeddings_in_collection(pdf_stem, collection):
    """Check if embeddings for a PDF file already exist in the collection."""
    try:
        result = collection.get(
            where={"source_file": {"$eq": f"{pdf_stem}.pdf"}},
            limit=1,
        )
        return len(result["ids"]) > 0
    except Exception as e:
        print(f"Error checking for existing embeddings: {e}")
        return False


def ingest_pdfs():
    if not PDF_DIRECTORY.exists():
        print(
            f"PDF directory {PDF_DIRECTORY} not found. Please create it and add PDFs."
        )
        return

    processed_files_set = load_processed_files_log()
    new_files_processed_count = 0
    skipped_with_embeddings_count = 0
    total_chunks_added_this_run = 0

    for pdf_file in PDF_DIRECTORY.glob("*.pdf"):
        if pdf_file.name in processed_files_set:
            print(f"Skipping already processed file: {pdf_file.name}")
            continue

        if has_embeddings_in_collection(pdf_file.stem, collection):
            print(f"Skipping {pdf_file.name}: Embeddings already exist in ChromaDB")
            processed_files_set.add(pdf_file.name)
            skipped_with_embeddings_count += 1
            continue

        print(f"Processing {pdf_file.name}...")
        try:
            core_metadata = extract_metadata_from_pdf(pdf_file)

            loader = PyPDFLoader(str(pdf_file))
            pages = loader.load()

            if not pages:
                print(f"Could not load pages from {pdf_file.name}. Skipping.")
                continue

            for page_doc in pages:
                page_doc.metadata["source_file"] = core_metadata["source_file"]
                page_doc.metadata["title"] = core_metadata["title"]
                page_doc.metadata["doi"] = core_metadata["doi"]
            chunks = text_splitter.split_documents(pages)

            if not chunks:
                print(f"No text chunks generated for {pdf_file.name}. Skipping.")
                continue

            chunk_texts_for_db = [doc.page_content for doc in chunks]
            chunk_metadatas_for_db = [doc.metadata for doc in chunks]
            chunk_ids = [
                f"{pdf_file.stem}_page{doc.metadata.get('page', 'N')}_chunk{j}"
                for j, doc in enumerate(chunks)
            ]

            chunk_embeddings_list = embeddings.embed_documents(chunk_texts_for_db)

            collection.add(
                ids=chunk_ids,
                embeddings=chunk_embeddings_list,
                documents=chunk_texts_for_db,
                metadatas=chunk_metadatas_for_db,
            )

            processed_files_set.add(pdf_file.name)
            new_files_processed_count += 1
            total_chunks_added_this_run += len(chunks)
            print(
                f"Successfully processed and added {pdf_file.name} to ChromaDB ({len(chunks)} chunks)."
            )

        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")

    save_processed_files_log(processed_files_set)
    print(
        f"\nIngestion complete. Newly processed files: {new_files_processed_count}. "
        f"Files skipped (embeddings exist): {skipped_with_embeddings_count}. "
        f"Total new chunks added: {total_chunks_added_this_run}."
    )
    print(
        f"Total documents in collection '{CHROMA_COLLECTION_NAME}': {collection.count()}"
    )


if __name__ == "__main__":
    PDF_DIRECTORY.mkdir(exist_ok=True)
    CHROMA_PERSIST_DIRECTORY.mkdir(exist_ok=True)
    ingest_pdfs()
