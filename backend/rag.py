import os
import json

import httpx


SYSTEM_PROMPT = (
    "Tu es un assistant juridique français strict. "
    "Tu réponds UNIQUEMENT avec du JSON valide, sans aucun texte autour. "
    "Tu n'inventes jamais d'article, de décision ou de source. "
    "Tu bases ta réponse exclusivement sur les documents juridiques fournis. "
    "Si l'information est insuffisante, tu listes ce qui manque dans missing_facts."
)


def safe_parse_json(text: str):
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    return None


def build_prompt(context: str, rules: list, source_by_id: dict) -> str:
    documents = []

    for rule in rules:
        sources = []

        for source_id in rule.get("source_ids", []):
            source = source_by_id.get(source_id)

            if source:
                sources.append({
                    "name": source.get("name"),
                    "url": source.get("url"),
                    "trust_level": source.get("trust_level")
                })

        documents.append({
            "title": rule.get("title"),
            "summary": rule.get("summary"),
            "legal_basis": rule.get("legal_basis", []),
            "conditions": rule.get("conditions", []),
            "effects": rule.get("effects", []),
            "sources": sources
        })

    prompt = f"""
Contexte du litige :
{context}

Documents juridiques de référence :
{json.dumps(documents, ensure_ascii=False, indent=2)}

Réponds UNIQUEMENT avec ce JSON :
{{
  "status": "ok",
  "hypotheses": [
    {{
      "party": "...",
      "ground": "...",
      "plausibility": "faible|moyenne|elevee",
      "explanation": "..."
    }}
  ],
  "missing_facts": ["..."]
}}
"""

    return prompt


def generate_ai_analysis(context: str, rules: list, source_by_id: dict):
    provider = os.getenv("LLM_PROVIDER", "")

    if not provider:
        return {
            "status": "llm_not_configured",
            "message": "Aucun LLM configuré. Définissez LLM_PROVIDER, OLLAMA_API_URL ou LLM_API_URL.",
            "hypotheses": []
        }

    prompt = build_prompt(context, rules, source_by_id)

    try:
        raw = None

        if provider == "ollama":
            api_url = os.getenv(
                "OLLAMA_API_URL",
                "http://localhost:11434/api/generate"
            )
            model = os.getenv("OLLAMA_MODEL", "mistral")

            response = httpx.post(
                api_url,
                json={
                    "model": model,
                    "prompt": SYSTEM_PROMPT + "\n\n" + prompt,
                    "stream": False
                },
                timeout=120
            )
            response.raise_for_status()
            raw = response.json().get("response", "")

        if provider == "pollinations":
            response = httpx.post(
                "https://text.pollinations.ai/",
                json={
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "model": "openai",
                    "temperature": 0
                },
                timeout=120
            )
            response.raise_for_status()
            raw = response.text

        if provider == "custom":
            api_url = os.getenv("LLM_API_URL")
            api_key = os.getenv("LLM_API_KEY", "")

            if not api_url:
                return {
                    "status": "llm_not_configured",
                    "message": "LLM_API_URL manquant.",
                    "hypotheses": []
                }

            headers = {}

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            response = httpx.post(
                api_url,
                headers=headers,
                json={
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"]

        if raw is None:
            return {
                "status": "llm_not_configured",
                "message": "Fournisseur LLM inconnu.",
                "hypotheses": []
            }

        parsed = safe_parse_json(raw)

        if not parsed:
            return {
                "status": "llm_invalid_json",
                "message": "Le LLM a répondu dans un format invalide. Utilisez l'analyse documentaire.",
                "hypotheses": []
            }

        allowed = ["faible", "moyenne", "elevee"]
        hypotheses = []

        for item in parsed.get("hypotheses", []):
            plausibility = item.get("plausibility", "moyenne")

            if plausibility not in allowed:
                plausibility = "moyenne"

            hypotheses.append({
                "party": item.get("party", "partie_a_determiner"),
                "ground": item.get("ground", "a_documenter"),
                "plausibility": plausibility,
                "explanation": item.get("explanation", "")
            })

        return {
            "status": "ok",
            "hypotheses": hypotheses,
            "missing_facts": parsed.get("missing_facts", [])
        }

    except Exception as error:
        return {
            "status": "llm_error",
            "message": f"Erreur LLM : {error}",
            "hypotheses": []
        }
