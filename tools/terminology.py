import os
from dotenv import load_dotenv
import omophub

load_dotenv()

API_KEY = os.getenv("OMOPHUB_API_KEY")

if not API_KEY:
    raise RuntimeError("OMOPHUB_API_KEY is missing from .env")

client = omophub.OMOPHub(api_key=API_KEY)


def search_concept(
    query: str,
    vocabulary: str | None = None,
    limit: int = 10,
):
    """
    Search OMOPHub for concepts.

    Examples:
        Metformin
        E11.9
        417181009
        Hemoglobin A1c
        Appendectomy
    """

    kwargs = {
        "page_size": limit
    }

    if vocabulary:
        kwargs["vocabulary_ids"] = [vocabulary]

    results = client.search.basic(
        query,
        **kwargs
    )

    return results


def get_mappings(
    concept_id: int,
    target_vocabulary: str | None = None,
):
    """
    Retrieve OMOP mappings for a concept.

    IMPORTANT:
    A source concept may map to zero, one,
    or multiple target concepts.
    """

    if target_vocabulary:
        result = client.mappings.get(
            concept_id,
            target_vocabulary=target_vocabulary,
        )
    else:
        result = client.mappings.get(concept_id)

    return result.get("mappings", [])


def is_valid_concept(concept: dict) -> bool:
    """
    Return True if the concept is not marked invalid.
    """

    return concept.get("invalid_reason") is None


def is_standard_concept(concept: dict) -> bool:
    """
    OMOP standard_concept = 'S'
    """

    return concept.get("standard_concept") == "S"