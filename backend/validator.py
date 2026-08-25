import json
import sys


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate():
    errors = []

    try:
        sources_data = load_json("sources.json")
    except Exception as e:
        return [f"Impossible de charger sources.json : {e}"]

    try:
        kb = load_json("legal_kb.json")
    except Exception as e:
        return [f"Impossible de charger legal_kb.json : {e}"]

    sources = sources_data.get("sources", [])

    if not sources:
        errors.append("sources.json doit contenir une liste 'sources'.")

    source_by_id = {}

    for source in sources:
        source_id = source.get("id")

        if not source_id:
            errors.append("Une source n'a pas d'id.")
            continue

        if source_id in source_by_id:
            errors.append(f"Source en double : {source_id}")

        if not source.get("name"):
            errors.append(f"Source {source_id} : name manquant.")

        if not source.get("url"):
            errors.append(f"Source {source_id} : url manquante.")
        elif not str(source.get("url")).startswith("https://"):
            errors.append(f"Source {source_id} : l'URL doit être HTTPS.")

        if source.get("trust_level") not in [1, 2, 3, 4]:
            errors.append(f"Source {source_id} : trust_level invalide.")

        if source.get("type") not in [
            "official",
            "case_law",
            "open_data",
            "doctrine",
            "institution"
        ]:
            errors.append(f"Source {source_id} : type invalide.")

        source_by_id[source_id] = source

    primary_source_ids = {
        source_id
        for source_id, source in source_by_id.items()
        if source.get("trust_level") in [1, 2]
    }

    if not isinstance(kb, list):
        errors.append("legal_kb.json doit contenir une liste.")
        return errors

    for rule in kb:
        rule_id = rule.get("id", "inconnu")

        if not rule.get("id"):
            errors.append("Une règle juridique n'a pas d'id.")

        if not rule.get("title"):
            errors.append(f"Règle {rule_id} : title manquant.")

        if not rule.get("summary"):
            errors.append(f"Règle {rule_id} : summary manquant.")

        if not rule.get("actors"):
            errors.append(f"Règle {rule_id} : actors manquant.")

        if not rule.get("keywords"):
            errors.append(f"Règle {rule_id} : keywords manquants.")

        source_ids = rule.get("source_ids", [])

        if not source_ids:
            errors.append(f"Règle {rule_id} : source_ids manquant.")

        has_primary_source = False

        for source_id in source_ids:
            if source_id not in source_by_id:
                errors.append(f"Règle {rule_id} : source inconnue : {source_id}")
                continue

            if source_id in primary_source_ids:
                has_primary_source = True

        if not has_primary_source:
            errors.append(
                f"Règle {rule_id} : doit contenir au moins une source officielle ou jurisprudentielle."
            )

        legal_basis = rule.get("legal_basis", [])

        if not legal_basis:
            errors.append(f"Règle {rule_id} : legal_basis manquant.")
        else:
            for basis in legal_basis:
                if not basis.get("code"):
                    errors.append(f"Règle {rule_id} : code manquant dans legal_basis.")

                if not basis.get("articles"):
                    errors.append(f"Règle {rule_id} : articles manquants dans legal_basis.")

        hypotheses = rule.get("hypotheses", [])

        for hypothesis in hypotheses:
            if hypothesis.get("plausibility") not in ["faible", "moyenne", "elevee"]:
                errors.append(
                    f"Règle {rule_id} : plausibility invalide dans hypotheses."
                )

            if not hypothesis.get("party"):
                errors.append(f"Règle {rule_id} : party manquant dans hypotheses.")

            if not hypothesis.get("ground"):
                errors.append(f"Règle {rule_id} : ground manquant dans hypotheses.")

    return errors


if __name__ == "__main__":
    errors = validate()

    if errors:
        print("ERREURS DE VALIDATION :")

        for error in errors:
            print("-", error)

        sys.exit(1)

    print("Validation OK : sources et base juridique sont structurellement valides.")
