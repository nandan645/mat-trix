import os
import re
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from utils import construct_nature_url_from_doi

load_dotenv()


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

CHROMA_PERSIST_DIRECTORY = Path("chroma_db")
CHROMA_COLLECTION_NAME = "scientific_articles"

EMBEDDING_MODEL_NAME = "models/text-embedding-004"
embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL_NAME, google_api_key=SecretStr(GOOGLE_API_KEY)
)

LLM_MODEL_NAME = "gemini-2.5-flash-preview-05-20"

embeddings = GoogleGenerativeAIEmbeddings(
    model=EMBEDDING_MODEL_NAME, google_api_key=SecretStr(GOOGLE_API_KEY)
)
llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL_NAME, google_api_key=SecretStr(GOOGLE_API_KEY), temperature=0.3
)


client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIRECTORY))
vectorstore = Chroma(
    client=client, collection_name=CHROMA_COLLECTION_NAME, embedding_function=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

new_template = """
You are a helpful AI assistant specializing in scientific literature and Material Science.
Your task is to answer the user's question based ONLY on the following numbered context from Material Science research papers.
If the user asks a general question or gives a statement, then reply user with a statement that you are a Material Science assistant and you can only answer questions related to Material Science.
Provide a detailed, comprehensive, and user-friendly explanation using proper Markdown syntax, including support for mathematical expressions if present in the context (e.g., $\sigma_{{VM}}$ or E = mc^2).
if the user asked a general question related to Material Science, provide a detailed answer based on the context.
When you use information from a specific source in the context, cite it using its corresponding number in square brackets, like [1], [2], etc.
If multiple sources support a statement, you can cite them together, like [1][3].
If the context does not contain information to answer the question, clearly state that there is not enough information found from the Material Science Research papers to answer this question and do not cite any sources, ask user to ask questions only Related to Material Science.
Do not make up information or use external knowledge.

IMPORTANT: At the very end of your response, on a new line, include the following flag:
- If your answer contains citation numbers (like [1], [2], etc.): `has_references: true`
- If your answer does NOT contain any citation numbers: `has_references: false`

CONTEXT:
{context_with_numbers}

USER QUESTION:
{question}

DETAILED ANSWER WITH INLINE CITATION NUMBERS (e.g., [1], [2]):
"""
new_prompt = PromptTemplate(
    template=new_template, input_variables=["context_with_numbers", "question"]
)


def process_retrieved_docs(docs):
    unique_sources_map = {}
    numbered_context_parts = []
    source_objects_for_references = []
    current_source_number = 1

    for doc in docs:
        doi = doc.metadata.get("doi", "N/A")
        title = doc.metadata.get("title", "N/A")
        source_file = doc.metadata.get("source_file", "N/A")
        page = doc.metadata.get("page", "N/A")
        url = construct_nature_url_from_doi(doi)

        source_key = doi if doi != "N/A" else f"{title}_{source_file}"

        if source_key not in unique_sources_map:
            unique_sources_map[source_key] = current_source_number
            source_objects_for_references.append(
                {
                    "number": current_source_number,
                    "doi": doi,
                    "title": title,
                    "url": url,
                    "page_info": f"Page: {page} (from {source_file})",
                }
            )
            current_source_number += 1

        citation_number_for_this_chunk = unique_sources_map[source_key]
        context_header = f"Source [{citation_number_for_this_chunk}] (Page: {page}):"
        numbered_context_parts.append(f"{context_header}\n{doc.page_content}")

    context_with_numbers_str = "\n---\n".join(numbered_context_parts)

    return {
        "context_with_numbers": context_with_numbers_str,
        "sources_for_references": source_objects_for_references,
    }


def extract_reference_flag_and_clean_answer(raw_answer):
    has_references_match = re.search(
        r"has_references:\s*(true|false)\s*$", raw_answer, re.IGNORECASE
    )

    if has_references_match:
        has_references = has_references_match.group(1).lower() == "true"
        cleaned_answer = re.sub(
            r"has_references:\s*(true|false)\s*$", "", raw_answer, flags=re.IGNORECASE
        ).strip()
        return cleaned_answer, has_references

    citation_pattern = r"\[\d+\]"
    contains_citations = bool(re.search(citation_pattern, raw_answer))

    if contains_citations:
        return raw_answer, True

    answer_lower = raw_answer.lower()
    has_references = not (
        "not enough information found" in answer_lower
        or "i am a material science assistant" in answer_lower
    )

    return raw_answer, has_references


def combine_llm_output_with_references(llm_output_and_sources_dict):
    llm_answer = llm_output_and_sources_dict["llm_answer"]
    sources = llm_output_and_sources_dict["sources_for_references"]

    if not sources:
        return llm_answer

    cleaned_answer, has_references = extract_reference_flag_and_clean_answer(llm_answer)

    if not has_references:
        return cleaned_answer

    references_section = "\n\n---\n**References:**\n"
    for src in sorted(sources, key=lambda x: x["number"]):
        ref_line = f"{src['number']}. **Title:** {src['title']}\n   **DOI:** {src['doi']}\n   **URL:** {src['url']}\n   **Source Info:** {src['page_info']}\n"
        references_section += ref_line

    return cleaned_answer + references_section


def get_initial_query_dict(query_string: str) -> dict:
    return {"original_query": query_string}


def retrieve_documents(input_dict: dict) -> dict:
    docs = retriever.invoke(input_dict["original_query"])
    return {"retrieved_docs": docs}


def generate_answer_from_context(input_dict: dict) -> dict:
    llm_input = {
        "question": input_dict["original_query"],
        "context_with_numbers": input_dict["processed_data_for_llm"][
            "context_with_numbers"
        ],
    }
    llm_answer_str = (new_prompt | llm | StrOutputParser()).invoke(llm_input)
    return {"llm_answer_raw": llm_answer_str}


def format_final_response(input_dict: dict) -> str:
    return combine_llm_output_with_references(
        {
            "llm_answer": input_dict["llm_answer_raw"],
            "sources_for_references": input_dict["processed_data_for_llm"][
                "sources_for_references"
            ],
        }
    )


final_rag_chain = RunnableLambda(get_initial_query_dict) | RunnablePassthrough.assign(
    retrieved_docs_output=RunnableLambda(retrieve_documents)
)


def process_documents_in_chain(input_dict: dict) -> dict:
    processed_data = process_retrieved_docs(input_dict["retrieved_docs"])
    return {"processed_data_for_llm": processed_data}


def create_rag_chain():
    _retrieval_chain = RunnablePassthrough.assign(
        retrieved_docs=RunnableLambda(lambda x: retriever.invoke(x["original_query"]))
    )

    _processing_chain = RunnablePassthrough.assign(
        processed_data_for_llm=RunnableLambda(
            lambda x: process_retrieved_docs(x["retrieved_docs"])
        )
    )

    _llm_input_mapper = RunnableLambda(
        lambda x: {
            "question": x["original_query"],
            "context_with_numbers": x["processed_data_for_llm"]["context_with_numbers"],
        }
    )
    _llm_generation_chain = _llm_input_mapper | new_prompt | llm | StrOutputParser()

    _answer_generation_chain = RunnablePassthrough.assign(
        llm_answer_raw=_llm_generation_chain
    )

    _final_formatting_chain = RunnableLambda(
        lambda x: combine_llm_output_with_references(
            {
                "llm_answer": x["llm_answer_raw"],
                "sources_for_references": x["processed_data_for_llm"][
                    "sources_for_references"
                ],
            }
        )
    )

    chain = (
        RunnableLambda(lambda query_string: {"original_query": query_string})
        | _retrieval_chain
        | _processing_chain
        | _answer_generation_chain
        | _final_formatting_chain
    )
    return chain


final_rag_chain = create_rag_chain()


async def afinal_rag_chain_invoke(query: str):
    initial_dict = {"original_query": query}

    retrieved_docs = await retriever.aget_relevant_documents(
        initial_dict["original_query"]
    )
    dict_after_retrieval = {**initial_dict, "retrieved_docs": retrieved_docs}

    processed_data = process_retrieved_docs(dict_after_retrieval["retrieved_docs"])
    dict_after_processing = {
        **dict_after_retrieval,
        "processed_data_for_llm": processed_data,
    }

    llm_input = {
        "question": dict_after_processing["original_query"],
        "context_with_numbers": dict_after_processing["processed_data_for_llm"][
            "context_with_numbers"
        ],
    }
    formatted_prompt_str = new_prompt.format(**llm_input)
    llm_response_obj = await llm.ainvoke(formatted_prompt_str)
    llm_answer_str = (
        llm_response_obj.content
        if hasattr(llm_response_obj, "content")
        else str(llm_response_obj)
    )
    dict_after_llm = {**dict_after_processing, "llm_answer_raw": llm_answer_str}

    return combine_llm_output_with_references(
        {
            "llm_answer": dict_after_llm["llm_answer_raw"],
            "sources_for_references": dict_after_llm["processed_data_for_llm"][
                "sources_for_references"
            ],
        }
    )


if __name__ == "__main__":
    try:
        doc_count = vectorstore._collection.count()
        if doc_count == 0:
            print("ChromaDB collection is empty. Run ingestion.py first.")
        else:
            print(
                f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' has {doc_count} documents."
            )
            test_query_1 = "What are the effects of VED on residual stress in additively manufactured nitinol?"
            print(f"\nQuerying with: {test_query_1}")
            response_1 = final_rag_chain.invoke(test_query_1)
            print("\nResponse 1:")
            print(response_1)

            test_query_2 = (
                "Explain the Abnormal Spin Seebeck effect in Tb3Fe5O12 garnet films."
            )
            print(f"\nQuerying with: {test_query_2}")
            response_2 = final_rag_chain.invoke(test_query_2)
            print("\nResponse 2:")
            print(response_2)

    except Exception as e:
        print(f"An error occurred during testing: {e}")
        print(
            "This might be due to an empty or uninitialized vector store. Please run ingestion.py."
        )
