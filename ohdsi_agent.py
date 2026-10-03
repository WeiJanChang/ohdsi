import json

from ollama import chat

from tools.terminology import (
    search_concept,
    get_mappings,
    is_valid_concept,
    is_standard_concept,
)


# ============================================================
# 1. GEMMA: understand the mapping request
# ============================================================

def parse_request(user_input: str) -> dict:

    system_prompt = """
You are a Clinical Terminology Mapping Router.

Your job is ONLY to understand the user's terminology mapping request.

You do NOT generate terminology codes.
You do NOT generate OMOP concept IDs.
You do NOT guess mappings.
You do NOT provide medical advice.

Extract:

- source_term
- source_vocabulary
- target_vocabulary

Examples:

User:
Map E11.9 from ICD10CM to OMOP

Output:
{
  "source_term": "E11.9",
  "source_vocabulary": "ICD10CM",
  "target_vocabulary": "OMOP"
}

User:
Find the OMOP concept for SNOMED 417181009

Output:
{
  "source_term": "417181009",
  "source_vocabulary": "SNOMED",
  "target_vocabulary": "OMOP"
}

User:
Map metformin 500 mg tablet to OMOP

Output:
{
  "source_term": "metformin 500 mg tablet",
  "source_vocabulary": null,
  "target_vocabulary": "OMOP"
}

Return ONLY valid JSON.
Do not include markdown.
"""

    response = chat(
        model="gemma4:e2b",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_input,
            },
        ],
        options={
            "temperature": 0
        },
    )

    text = response.message.content.strip()

    return json.loads(text)


# ============================================================
# 2. OMOPHub: terminology search
# ============================================================

def find_source_concepts(request: dict):

    source_term = request.get("source_term")
    source_vocabulary = request.get("source_vocabulary")

    results = search_concept(
        query=source_term,
        vocabulary=source_vocabulary,
        limit=10,
    )

    return [
        concept
        for concept in results
        if is_valid_concept(concept)
    ]


# ============================================================
# 3. Display concept
# ============================================================

def print_concept(concept, number=None):

    prefix = f"[{number}] " if number else ""

    print(
        f"""
{prefix}{concept.get("concept_name")}
    Code:            {concept.get("concept_code")}
    OMOP concept_id: {concept.get("concept_id")}
    Vocabulary:      {concept.get("vocabulary_id")}
    Domain:          {concept.get("domain_id")}
    Concept class:   {concept.get("concept_class_id")}
    Standard:        {concept.get("standard_concept")}
    Match type:      {concept.get("match_type")}
    Match score:     {concept.get("match_score")}
"""
    )


# ============================================================
# 4. User selects concept if ambiguous
# ============================================================

def select_concept(concepts):

    if len(concepts) == 1:
        return concepts[0]

    print("\nMultiple candidate concepts found:\n")

    for i, concept in enumerate(concepts, start=1):
        print_concept(concept, i)

    while True:

        choice = input(
            f"Select concept [1-{len(concepts)}]: "
        ).strip()

        try:
            index = int(choice) - 1

            if 0 <= index < len(concepts):
                return concepts[index]

        except ValueError:
            pass

        print("Invalid selection.")


# ============================================================
# 5. OMOP Standardization
# ============================================================

def standardize_concept(concept):

    # Already Standard
    if is_standard_concept(concept):

        return {
            "status": "ALREADY_STANDARD",
            "source": concept,
            "targets": [concept],
        }

    mappings = get_mappings(
        concept_id=concept["concept_id"]
    )

    valid_targets = [
        mapping
        for mapping in mappings
        if mapping.get("target_standard_concept") == "S"
        and mapping.get("invalid_reason") is None
    ]

    if not valid_targets:

        return {
            "status": "NO_MAPPING_FOUND",
            "source": concept,
            "targets": [],
        }

    return {
        "status": "MAPPED",
        "source": concept,
        "targets": valid_targets,
    }


# ============================================================
# 6. Display final verified result
# ============================================================

def print_result(result):

    source = result["source"]

    print("\n")
    print("=" * 65)
    print("SOURCE CONCEPT")
    print("=" * 65)

    print(
        f"""
Name:            {source.get("concept_name")}
Code:            {source.get("concept_code")}
Vocabulary:      {source.get("vocabulary_id")}
OMOP concept_id: {source.get("concept_id")}
Domain:          {source.get("domain_id")}
Standard:        {source.get("standard_concept")}
"""
    )

    print("=" * 65)
    print("OMOP STANDARDIZATION")
    print("=" * 65)

    if result["status"] == "ALREADY_STANDARD":

        print("Source concept is already an OMOP Standard Concept.")

        return

    if result["status"] == "NO_MAPPING_FOUND":

        print("No verified OMOP Standard mapping found.")
        print("The AI will NOT guess a mapping.")

        return

    for i, target in enumerate(
        result["targets"],
        start=1
    ):

        print(
            f"""
[{i}]
Target concept:    {target.get("target_concept_name")}
Target code:       {target.get("target_concept_code")}
Vocabulary:        {target.get("target_vocabulary_id")}
OMOP concept_id:   {target.get("target_concept_id")}
Domain:            {target.get("target_domain_id")}
Standard concept:  {target.get("target_standard_concept")}
Relationship:      {target.get("relationship_id")}
Mapping type:      {target.get("mapping_type")}
"""
        )


# ============================================================
# MAIN AGENT
# ============================================================

def main():

    print("=" * 65)
    print("CLINICAL TERMINOLOGY MAPPING AGENT")
    print("=" * 65)

    user_input = input(
        "\nWhat would you like to map?\n> "
    ).strip()

    if not user_input:
        return

    # --------------------------------------------------------
    # Gemma understands the request
    # --------------------------------------------------------

    print("\n[1] Gemma: understanding request...")

    try:

        request = parse_request(user_input)

    except Exception as e:

        print("Gemma could not parse the request.")
        print(e)

        return

    print("\nParsed request:")

    print(
        json.dumps(
            request,
            indent=2,
            ensure_ascii=False,
        )
    )

    # --------------------------------------------------------
    # OMOPHub performs real terminology lookup
    # --------------------------------------------------------

    print("\n[2] OMOPHub: searching terminology...")

    try:

        concepts = find_source_concepts(request)

    except Exception as e:

        print("OMOPHub search failed.")
        print(e)

        return

    if not concepts:

        print("\nNo verified source concept found.")
        print("The AI will NOT invent a code.")

        return

    # --------------------------------------------------------
    # Select candidate
    # --------------------------------------------------------

    concept = select_concept(concepts)

    print("\nSelected concept:")

    print_concept(concept)

    # --------------------------------------------------------
    # OMOP Standardization
    # --------------------------------------------------------

    print("\n[3] OMOPHub: checking Standard Concept mapping...")

    try:

        result = standardize_concept(concept)

    except Exception as e:

        print("Mapping lookup failed.")
        print(e)

        return

    # --------------------------------------------------------
    # Verified output
    # --------------------------------------------------------

    print_result(result)


if __name__ == "__main__":
    main()