import os
import re
import uuid
import json
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

import validator
import db
from auth import verify_admin, validate_token
from rag import generate_ai_analysis, ai_extract_themes

load_dotenv()

db.init_db()

errors = validator.validate()

if errors:
    raise RuntimeError(
        "Validation des sources et de la base juridique échouée : " + " | ".join(errors)
    )

SOURCES = validator.load_json("sources.json")["sources"]
KB = validator.load_json("legal_kb.json")

SOURCE_BY_ID = {
    source["id"]: source
    for source in SOURCES
}

CASE_LAW_SEED = [
    {
        "id": "placeholder_vices_caches",
        "court": "À compléter depuis source officielle",
        "decision_date": None,
        "reference": "À compléter",
        "themes": [
            "vices_caches"
        ],
        "actors": [
            "vendeur_professionnel",
            "vendeur_particulier",
            "acheteur"
        ],
        "summary": "Décision relative aux vices cachés à importer depuis une source officielle.",
        "url": "https://www.courdecassation.fr/",
        "source_id": "cour_cassation",
        "verified": False
    },
    {
        "id": "placeholder_conformite",
        "court": "À compléter depuis source officielle",
        "decision_date": None,
        "reference": "À compléter",
        "themes": [
            "garantie_legale_conformite"
        ],
        "actors": [
            "vendeur_professionnel",
            "acheteur"
        ],
        "summary": "Décision relative à la garantie légale de conformité à importer depuis une source officielle.",
        "url": "https://www.legifrance.gouv.fr/",
        "source_id": "legifrance",
        "verified": False
    },
    {
        "id": "placeholder_reparateur",
        "court": "À compléter depuis source officielle",
        "decision_date": None,
        "reference": "À compléter",
        "themes": [
            "reparateur_responsabilite"
        ],
        "actors": [
            "reparateur_professionnel",
            "proprietaire_vehicule"
        ],
        "summary": "Décision relative à la responsabilité du réparateur automobile à importer depuis une source officielle.",
        "url": "https://www.courdecassation.fr/",
        "source_id": "cour_cassation",
        "verified": False
    },
    {
        "id": "placeholder_expertise",
        "court": "À compléter depuis source officielle",
        "decision_date": None,
        "reference": "À compléter",
        "themes": [
            "expert_automobile",
            "contre_expertise"
        ],
        "actors": [
            "expert_automobile",
            "cabinet_expertise",
            "assurance"
        ],
        "summary": "Décision relative à l'expertise automobile à importer depuis une source officielle.",
        "url": "https://www.courdecassation.fr/",
        "source_id": "cour_cassation",
        "verified": False
    }
]

app = FastAPI(title="Justice Auto API robuste SQLite")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("API_ALLOWED_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class AnalyzeRequest(BaseModel):
    context: str
    actor: str | None = None


class AccessRequestIn(BaseModel):
    device_id: str
    contact: str | None = None
    message: str | None = None


class AccessReviewIn(BaseModel):
    decision: str
    reason: str | None = None


class CaseLawIn(BaseModel):
    id: str | None = None
    court: str | None = None
    decision_date: str | None = None
    reference: str | None = None
    themes: list[str] = []
    actors: list[str] = []
    summary: str
    url: str | None = None
    source_id: str | None = None
    verified: bool = False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials if credentials else None
    user = validate_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")

    return user


def audit_log(actor: str, action: str, target: str, metadata: dict | None = None):
    connection = db.get_connection()

    try:
        connection.execute(
            """
            INSERT INTO audit_logs (
                timestamp,
                actor,
                action,
                target,
                metadata
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                now_iso(),
                actor,
                action,
                target,
                json.dumps(metadata or {}, ensure_ascii=False)
            )
        )

        connection.commit()

    finally:
        connection.close()


def ensure_case_law_seed():
    connection = db.get_connection()

    try:
        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM case_law
            """
        ).fetchone()

        count = row["count"] if row else 0

        if count == 0:
            for decision in CASE_LAW_SEED:
                connection.execute(
                    """
                    INSERT INTO case_law (
                        id,
                        court,
                        decision_date,
                        reference,
                        themes,
                        actors,
                        summary,
                        url,
                        source_id,
                        verified
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        decision["id"],
                        decision["court"],
                        decision["decision_date"],
                        decision["reference"],
                        json.dumps(decision["themes"], ensure_ascii=False),
                        json.dumps(decision["actors"], ensure_ascii=False),
                        decision["summary"],
                        decision["url"],
                        decision["source_id"],
                        1 if decision["verified"] else 0
                    )
                )

            connection.commit()

    finally:
        connection.close()


ensure_case_law_seed()


def load_case_law_file():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "case_law.json")

    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        decisions = json.load(f)

    connection = db.get_connection()

    try:
        for decision in decisions:
            connection.execute(
                """
                INSERT INTO case_law (
                    id, court, decision_date, reference, themes, actors,
                    summary, url, source_id, verified
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    court = excluded.court,
                    decision_date = excluded.decision_date,
                    reference = excluded.reference,
                    themes = excluded.themes,
                    actors = excluded.actors,
                    summary = excluded.summary,
                    url = excluded.url,
                    source_id = excluded.source_id,
                    verified = excluded.verified
                """,
                (
                    decision["id"],
                    decision.get("court"),
                    decision.get("decision_date"),
                    decision.get("reference"),
                    json.dumps(decision.get("themes", []), ensure_ascii=False),
                    json.dumps(decision.get("actors", []), ensure_ascii=False),
                    decision.get("summary"),
                    decision.get("url"),
                    decision.get("source_id"),
                    1 if decision.get("verified") else 0
                )
            )

        connection.commit()
    finally:
        connection.close()


load_case_law_file()


def normalize(text: str) -> str:
    if not text:
        return ""

    return re.sub(r"\s+", " ", text.lower().strip())


THEME_SYNONYMS = {
    "vices_caches": [
        "vice caché",
        "vices cachés",
        "défaut caché",
        "panne",
        "moteur",
        "injecteur",
        "culasse",
        "usure",
        "vétusté",
        "impropre à l'usage",
        "caché"
    ],
    "garantie_legale_conformite": [
        "conformité",
        "non conforme",
        "garantie légale"
    ],
    "reparateur_responsabilite": [
        "garagiste",
        "réparateur",
        "réparation",
        "malfaçon",
        "devis",
        "facture",
        "atelier"
    ],
    "controle_technique": [
        "contrôle technique",
        "ct"
    ],
    "expert_automobile": [
        "expert",
        "expertise",
        "contre-expertise",
        "rapport"
    ],
    "documents_administratifs_vente": [
        "carte grise",
        "certificat",
        "cession",
        "non-gage",
        "documents"
    ]
}


def extract_themes_local(text: str):
    ctx = normalize(text)
    themes = set()

    for theme, synonyms in THEME_SYNONYMS.items():
        for synonym in synonyms:
            if normalize(synonym) in ctx:
                themes.add(theme)
                break

    return themes


def get_primary_sources(rule: dict):
    result = []

    for source_id in rule.get("source_ids", []):
        source = SOURCE_BY_ID.get(source_id)

        if not source:
            continue

        if source.get("trust_level") in [1, 2]:
            result.append(source)

    return result


def retrieve_rules(context: str, actor: str | None):
    ctx = normalize(context)
    scored = []

    for rule in KB:
        score = 0

        for keyword in rule.get("keywords", []):
            if normalize(keyword) in ctx:
                score += 3

        if actor and actor in rule.get("actors", []):
            score += 5

        primary_sources = get_primary_sources(rule)

        if not primary_sources:
            continue

        if score > 0:
            scored.append((score, rule))

    scored.sort(key=lambda item: item[0], reverse=True)

    return [rule for _, rule in scored[:8]]


def build_hypotheses(rules: list):
    hypotheses = []

    for rule in rules:
        sources = [
            SOURCE_BY_ID[source_id]
            for source_id in rule.get("source_ids", [])
            if source_id in SOURCE_BY_ID
        ]

        has_primary_source = any(
            source.get("trust_level") in [1, 2]
            for source in sources
        )

        if not has_primary_source:
            continue

        if rule.get("hypotheses"):
            for hypothesis in rule.get("hypotheses", []):
                item = {
                    "party": hypothesis.get("party"),
                    "ground": hypothesis.get("ground"),
                    "plausibility": hypothesis.get("plausibility"),
                    "priority": hypothesis.get("priority"),
                    "explanation": hypothesis.get("explanation"),
                    "rule_id": rule.get("id"),
                    "rule_title": rule.get("title"),
                    "legal_basis": rule.get("legal_basis", []),
                    "sources": sources
                }

                hypotheses.append(item)
        else:
            hypotheses.append({
                "party": "partie_a_determiner",
                "ground": rule.get("id"),
                "plausibility": "moyenne",
                "priority": 5,
                "explanation": rule.get("summary"),
                "rule_id": rule.get("id"),
                "rule_title": rule.get("title"),
                "legal_basis": rule.get("legal_basis", []),
                "sources": sources
            })

    hypotheses.sort(key=lambda item: item.get("priority", 999))

    return hypotheses


def guardrail(hypotheses: list):
    allowed_plausibility = ["faible", "moyenne", "elevee"]

    for hypothesis in hypotheses:
        if hypothesis.get("plausibility") not in allowed_plausibility:
            raise HTTPException(
                status_code=500,
                detail="Niveau de plausibilité invalide."
            )

        has_primary_source = any(
            source.get("trust_level") in [1, 2]
            for source in hypothesis.get("sources", [])
        )

        if not has_primary_source:
            raise HTTPException(
                status_code=500,
                detail="Hypothèse sans source officielle ou jurisprudentielle."
            )


def get_case_law_from_db():
    connection = db.get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM case_law
            """
        ).fetchall()

        result = []

        for row in rows:
            item = dict(row)

            try:
                item["themes"] = json.loads(item.get("themes") or "[]")
            except Exception:
                item["themes"] = []

            try:
                item["actors"] = json.loads(item.get("actors") or "[]")
            except Exception:
                item["actors"] = []

            item["verified"] = bool(item.get("verified"))

            result.append(item)

        return result

    finally:
        connection.close()


def retrieve_case_law(rules: list, context: str, actor: str | None):
    decisions = get_case_law_from_db()
    ctx = normalize(context)
    rule_ids = [rule.get("id") for rule in rules]

    theme_map = {
        "vices_caches": ["vices_caches"],
        "garantie_legale_conformite": ["garantie_legale_conformite"],
        "delivrance_conforme": [
            "garantie_legale_conformite",
            "documents_administratifs_vente"
        ],
        "dol_tromperie": [
            "vices_caches",
            "documents_administratifs_vente"
        ],
        "reparateur_responsabilite": ["reparateur_responsabilite"],
        "controle_technique": ["controle_technique"],
        "expert_automobile": ["expert_automobile"],
        "documents_administratifs_vente": ["documents_administratifs_vente"],
        "panne_moteur_injecteur_usure": [
            "vices_caches",
            "reparateur_responsabilite",
            "expert_automobile"
        ]
    }

    wanted_themes = set(extract_themes_local(context))

    ai_themes = ai_extract_themes(context, list(THEME_SYNONYMS.keys()))
    wanted_themes.update(ai_themes)

    for rule_id in rule_ids:
        wanted_themes.update(theme_map.get(rule_id, [rule_id]))

    results = []

    for decision in decisions:
        score = 0
        themes = decision.get("themes", [])

        if any(theme in wanted_themes for theme in themes):
            score += 5

        if ctx:
            for theme in themes:
                if normalize(theme) in ctx:
                    score += 2

            summary = normalize(decision.get("summary") or "")

            for word in ctx.split():
                if len(word) > 5 and word in summary:
                    score += 1

        if actor and actor in decision.get("actors", []):
            score += 2

        if score > 0:
            results.append({**decision, "score": score})

    results.sort(key=lambda item: item.get("score", 0), reverse=True)

    return results[:6]


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "API Justice Auto robuste SQLite",
        "warning": "Information juridique automatisée, ne remplace pas un avocat."
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": now_iso()
    }


@app.post("/api/login")
def login(payload: LoginRequest):
    token = verify_admin(payload.username, payload.password)

    if not token:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    audit_log(
        actor=payload.username,
        action="login_success",
        target="authentication"
    )

    return {
        "token": token,
        "username": payload.username
    }


@app.get("/api/sources")
def get_sources():
    return {
        "sources": SOURCES
    }


@app.get("/api/legal-rules")
def legal_rules(user=Depends(require_auth)):
    return {
        "rules": KB
    }


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest, user=Depends(require_auth)):
    if len(payload.context.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Le contexte est trop court. Décrivez précisément le litige."
        )

    rules = retrieve_rules(payload.context, payload.actor)

    if not rules:
        return {
            "status": "insufficient_data",
            "hypotheses": [],
            "case_law": [],
            "message": "Aucune règle juridique fiable ne correspond suffisamment au contexte fourni.",
            "warnings": [
                "Complétez les faits.",
                "Précisez les acteurs.",
                "Ajoutez les documents disponibles."
            ]
        }

    hypotheses = build_hypotheses(rules)
    guardrail(hypotheses)

    case_law = retrieve_case_law(rules, payload.context, payload.actor)

    return {
        "status": "ok",
        "hypotheses": hypotheses,
        "case_law": case_law,
        "warnings": [
            "Analyse fournie à titre d'information juridique.",
            "Ne constitue pas une consultation juridique.",
            "Les hypothèses doivent être vérifiées par un professionnel du droit."
        ]
    }


@app.post("/api/ai/analyze")
def ai_analyze(payload: AnalyzeRequest, user=Depends(require_auth)):
    if len(payload.context.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Le contexte est trop court. Décrivez précisément le litige."
        )

    rules = retrieve_rules(payload.context, payload.actor)

    if not rules:
        return {
            "status": "insufficient_data",
            "hypotheses": [],
            "message": "Aucune règle juridique fiable ne correspond au contexte.",
            "warnings": [
                "Complétez les faits.",
                "Précisez les acteurs.",
                "Ajoutez les documents disponibles."
            ]
        }

    ai_result = generate_ai_analysis(
        context=payload.context,
        rules=rules,
        source_by_id=SOURCE_BY_ID
    )

    if isinstance(ai_result, dict):
        ai_result.setdefault("warnings", [])

        ai_result["warnings"].extend([
            "Analyse IA fournie à titre d'information juridique.",
            "Ne constitue pas une consultation juridique."
        ])

    return ai_result


@app.post("/api/access/request")
def request_access(payload: AccessRequestIn):
    request_id = str(uuid.uuid4())
    created_at = now_iso()

    connection = db.get_connection()

    try:
        connection.execute(
            """
            INSERT INTO access_requests (
                id,
                device_id,
                contact,
                message,
                status,
                created_at,
                reviewed_at,
                reviewed_by,
                decision_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                payload.device_id,
                payload.contact,
                payload.message,
                "pending",
                created_at,
                None,
                None,
                None
            )
        )

        connection.commit()

    finally:
        connection.close()

    audit_log(
        actor="anonymous",
        action="access_request",
        target=request_id,
        metadata={
            "device_id": payload.device_id,
            "contact": payload.contact
        }
    )

    return {
        "id": request_id,
        "status": "pending",
        "message": "Demande d'accès enregistrée."
    }


@app.get("/api/access/status/{request_id}")
def access_status(request_id: str):
    connection = db.get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM access_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    return dict(row)


@app.get("/api/admin/access-requests")
def list_access_requests(user=Depends(require_auth)):
    connection = db.get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM access_requests
            ORDER BY created_at DESC
            """
        ).fetchall()

    finally:
        connection.close()

    return {
        "requests": [dict(row) for row in rows]
    }


@app.post("/api/admin/access-requests/{request_id}/review")
def review_access_request(
    request_id: str,
    payload: AccessReviewIn,
    user=Depends(require_auth)
):
    if payload.decision not in ["approved", "refused"]:
        raise HTTPException(
            status_code=400,
            detail="La décision doit être 'approved' ou 'refused'."
        )

    reviewed_at = now_iso()
    reviewed_by = user.get("username")

    notification_id = str(uuid.uuid4())
    notification_title = "Accès autorisé" if payload.decision == "approved" else "Accès refusé"
    notification_body = "Votre demande d'accès a été acceptée." if payload.decision == "approved" else "Votre demande d'accès a été refusée."

    connection = db.get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE access_requests
            SET
                status = ?,
                reviewed_at = ?,
                reviewed_by = ?,
                decision_reason = ?
            WHERE id = ?
            """,
            (
                payload.decision,
                reviewed_at,
                reviewed_by,
                payload.reason,
                request_id
            )
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Demande introuvable")

        connection.execute(
            """
            INSERT INTO notifications (
                id,
                target_request_id,
                title,
                body,
                created_at,
                sent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                request_id,
                notification_title,
                notification_body,
                now_iso(),
                0
            )
        )

        connection.commit()

        row = connection.execute(
            """
            SELECT *
            FROM access_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

    finally:
        connection.close()

    audit_log(
        actor=reviewed_by,
        action="access_review",
        target=request_id,
        metadata={
            "decision": payload.decision,
            "reason": payload.reason
        }
    )

    return dict(row)


@app.get("/api/admin/notifications")
def list_notifications(user=Depends(require_auth)):
    connection = db.get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM notifications
            ORDER BY created_at DESC
            """
        ).fetchall()

    finally:
        connection.close()

    return {
        "notifications": [dict(row) for row in rows]
    }


@app.get("/api/admin/audit-logs")
def list_audit_logs(user=Depends(require_auth)):
    connection = db.get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM audit_logs
            ORDER BY id DESC
            LIMIT 500
            """
        ).fetchall()

    finally:
        connection.close()

    logs = []

    for row in rows:
        item = dict(row)

        try:
            item["metadata"] = json.loads(item.get("metadata") or "{}")
        except Exception:
            item["metadata"] = {}

        logs.append(item)

    return {
        "logs": logs
    }


@app.post("/api/admin/case-law")
def add_case_law(payload: CaseLawIn, user=Depends(require_auth)):
    decision_id = payload.id or str(uuid.uuid4())

    if payload.source_id and payload.source_id not in SOURCE_BY_ID:
        raise HTTPException(
            status_code=400,
            detail="source_id inconnu. Utilisez une source définie dans sources.json."
        )

    connection = db.get_connection()

    try:
        connection.execute(
            """
            INSERT INTO case_law (
                id,
                court,
                decision_date,
                reference,
                themes,
                actors,
                summary,
                url,
                source_id,
                verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                court = excluded.court,
                decision_date = excluded.decision_date,
                reference = excluded.reference,
                themes = excluded.themes,
                actors = excluded.actors,
                summary = excluded.summary,
                url = excluded.url,
                source_id = excluded.source_id,
                verified = excluded.verified
            """,
            (
                decision_id,
                payload.court,
                payload.decision_date,
                payload.reference,
                json.dumps(payload.themes, ensure_ascii=False),
                json.dumps(payload.actors, ensure_ascii=False),
                payload.summary,
                payload.url,
                payload.source_id,
                1 if payload.verified else 0
            )
        )

        connection.commit()

    finally:
        connection.close()

    audit_log(
        actor=user.get("username"),
        action="case_law_saved",
        target=decision_id,
        metadata={
            "court": payload.court,
            "reference": payload.reference,
            "source_id": payload.source_id
        }
    )

    return {
        "id": decision_id,
        "status": "saved"
    }


@app.get("/api/case-law/search")
def search_case_law(
    q: str = "",
    actor: str = "",
    theme: str = "",
    user=Depends(require_auth)
):
    decisions = get_case_law_from_db()

    text = " ".join(part for part in [q, actor, theme] if part)

    themes = extract_themes_local(text)

    if theme:
        themes.add(theme)

    ai_themes = ai_extract_themes(q or text, list(THEME_SYNONYMS.keys()))
    themes.update(ai_themes)

    results = []
    nq = normalize(q)

    for decision in decisions:
        score = 0
        decision_themes = decision.get("themes", [])

        if any(t in themes for t in decision_themes):
            score += 5

        if nq:
            summary = normalize(decision.get("summary") or "")
            reference = normalize(decision.get("reference") or "")

            if nq in summary:
                score += 3

            if nq in reference:
                score += 3

            for word in nq.split():
                if len(word) > 3:
                    if word in summary:
                        score += 1

                    if word in reference:
                        score += 2

        if actor and actor in decision.get("actors", []):
            score += 2

        if score > 0 or (not q and not actor and not theme):
            results.append({
                **decision,
                "score": score
            })

    results.sort(key=lambda item: item.get("score", 0), reverse=True)

    return {
        "results": results[:10],
        "themes_detectes": sorted(themes),
        "warning": "Les décisions doivent être importées depuis des sources officielles et vérifiées."
    }
