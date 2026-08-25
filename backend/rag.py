import os
import json
import httpx

SYSTEM_PROMPT = """
Tu es un assistant d'aide à l'analyse juridique en droit automobile français.

Tu ne remplaces pas un avocat.
Tu fournis uniquement une information juridique générale.

Tu dois répondre exclusivement à partir des documents juridiques fournis.
Si les documents sont insuffisants, tu dois le dire.

Tu ne dois jamais inventer :
- un article de loi ;
- une décision de justice ;
- une date ;
- une référence ;
- une solution juridique.

Tu dois produire une réponse JSON valide avec cette structure :

{
  "status": "ok" | "insufficient_data",
  "hypotheses": [
    {
      "party": "...",
      "ground": "...",
      "plausibility": "faible" | "moyenne" | "elevee",
      "explanation": "...",
      "sources": ["..."]
    }
  ],
  "missing_facts": ["..."],
  "warnings": ["..."]
}
"""


def build_documents(context: str, rules: list, source_by_id: dict):
    documents = []

    for rule in rules:
        sources = []

        for source_id in rule.get("source_ids", []):
            source = source_by_id.get(source_id)

            if source:
                sources.append({
                    "id": source["id"],
                    "name": source["name"],
                    "url": source["url"],
                    "trust_level": source["trust_level"]
                })

        documents.append({
            "rule_id": rule.get("id"),
            "title": rule.get("title"),
            "summary": rule.get("summary"),
            "legal_basis": rule.get("legal_basis", []),
            "conditions": rule.get("conditions", []),
            "effects": rule.get("effects", []),
            "sources": sources
        })

    return documents


def build_prompt(context: str, documents: list):
    prompt = []

    prompt.append(SYSTEM_PROMPT)
    prompt.append("")
    prompt.append("CONTEXTE DU LITIGE :")
    prompt.append(context)
    prompt.append("")
    prompt.append("DOCUMENTS JURIDIQUES UTILISABLES :")
    prompt.append(json.dumps(documents, ensure_ascii=False, indent=2))
    prompt.append("")
    prompt.append("Réponds uniquement avec du JSON valide.")

    return "\n".join(prompt)


def safe_parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def call_llm(prompt: str):
    provider = os.getenv("LLM_PROVIDER", "").lower()

    if not provider:
        return None

    if provider == "ollama":
        url = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
        model = os.getenv("OLLAMA_MODEL", "mistral")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        response = httpx.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()

        return data.get("response")

    if provider == "custom":
        url = os.getenv("LLM_API_URL")
        api_key = os.getenv("LLM_API_KEY", "")

        headers = {
            "Content-Type": "application/json"
        }

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": os.getenv("LLM_MODEL", "legal-model"),
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0
        }

        response = httpx.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]

    return None


def generate_ai_analysis(context: str, rules: list, source_by_id: dict):
    documents = build_documents(context, rules, source_by_id)

    if not documents:
        return {
            "status": "insufficient_data",
            "hypotheses": [],
            "missing_facts": [
                "Aucune règle juridique fiable n'a été trouvée."
            ],
            "warnings": [
                "L'analyse IA nécessite des documents juridiques fiables."
            ]
        }

    prompt = build_prompt(context, documents)

    try:
        raw_response = call_llm(prompt)
    except Exception as error:
        return {
            "status": "llm_error",
            "message": "Impossible de contacter le modèle IA.",
            "error": str(error),
            "documents": documents
        }

    if not raw_response:
        return {
            "status": "llm_not_configured",
            "message": "Aucun LLM configuré. Définissez LLM_PROVIDER, OLLAMA_API_URL ou LLM_API_URL.",
            "documents": documents
        }

    parsed = safe_parse_json(raw_response)

    if not parsed:
        return {
            "status": "llm_invalid_json",
            "message": "Le modèle IA n'a pas renvoyé un JSON valide.",
            "raw_response": raw_response,
            "documents": documents
        }

    return parsed
