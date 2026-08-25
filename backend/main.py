import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

import validator
from auth import verify_admin, validate_token
from rag import generate_ai_analysis

load_dotenv()

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

ACCESS_REQUESTS = {}
NOTIFICATIONS = []
AUDIT_LOGS = []

CASE_LAW = [
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

app = FastAPI(title="Justice Auto API robuste")

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


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials if credentials else None
    user = validate_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Authentification requise")

    return user


def audit_log(actor: str, action: str, target: str, metadata: dict | None = None):
    AUDIT_LOGS.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "metadata": metadata or {}
    })


def normalize(text: str) -> str:
    if not text:
        return ""

    return re.sub(r"\s+", " ", text.lower().strip())


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


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "API Justice Auto robuste",
        "warning": "Information juridique automatisée, ne remplace pas un avocat."
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
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
            "message": "Aucune règle juridique fiable ne correspond suffisamment au contexte fourni.",
            "warnings": [
                "Complétez les faits.",
                "Précisez les acteurs.",
                "Ajoutez les documents disponibles."
            ]
        }

    hypotheses = build_hypotheses(rules)
    guardrail(hypotheses)

    return {
        "status": "ok",
        "hypotheses": hypotheses,
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

    ACCESS_REQUESTS[request_id] = {
        "id": request_id,
        "device_id": payload.device_id,
        "contact": payload.contact,
        "message": payload.message,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_at": None,
        "reviewed_by": None,
        "decision_reason": None
    }

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
    request = ACCESS_REQUESTS.get(request_id)

    if not request:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    return request


@app.get("/api/admin/access-requests")
def list_access_requests(user=Depends(require_auth)):
    requests = list(ACCESS_REQUESTS.values())
    requests.sort(key=lambda item: item.get("created_at", ""), reverse=True)

    return {
        "requests": requests
    }


@app.post("/api/admin/access-requests/{request_id}/review")
def review_access_request(
    request_id: str,
    payload: AccessReviewIn,
    user=Depends(require_auth)
):
    if request_id not in ACCESS_REQUESTS:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    if payload.decision not in ["approved", "refused"]:
        raise HTTPException(
            status_code=400,
            detail="La décision doit être 'approved' ou 'refused'."
        )

    ACCESS_REQUESTS[request_id]["status"] = payload.decision
    ACCESS_REQUESTS[request_id]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    ACCESS_REQUESTS[request_id]["reviewed_by"] = user.get("username")
    ACCESS_REQUESTS[request_id]["decision_reason"] = payload.reason

    notification_title = "Accès autorisé" if payload.decision == "approved" else "Accès refusé"
    notification_body = "Votre demande d'accès a été acceptée." if payload.decision == "approved" else "Votre demande d'accès a été refusée."

    NOTIFICATIONS.append({
        "id": str(uuid.uuid4()),
        "target_request_id": request_id,
        "title": notification_title,
        "body": notification_body,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent": False
    })

    audit_log(
        actor=user.get("username"),
        action="access_review",
        target=request_id,
        metadata={
            "decision": payload.decision,
            "reason": payload.reason
        }
    )

    return ACCESS_REQUESTS[request_id]


@app.get("/api/admin/notifications")
def list_notifications(user=Depends(require_auth)):
    return {
        "notifications": NOTIFICATIONS
    }


@app.get("/api/admin/audit-logs")
def list_audit_logs(user=Depends(require_auth)):
    return {
        "logs": AUDIT_LOGS
    }


@app.get("/api/case-law/search")
def search_case_law(
    q: str = "",
    actor: str = "",
    theme: str = "",
    user=Depends(require_auth)
):
    results = []
    nq = normalize(q)

    for decision in CASE_LAW:
        score = 0

        if nq:
            if nq in normalize(decision.get("summary") or ""):
                score += 3

            if nq in normalize(decision.get("reference") or ""):
                score += 3

            if any(nq in normalize(theme_item) for theme_item in decision.get("themes", [])):
                score += 4

        if actor and actor in decision.get("actors", []):
            score += 5

        if theme and theme in decision.get("themes", []):
            score += 5

        if score > 0 or (not q and not actor and not theme):
            results.append({
                **decision,
                "score": score
            })

    results.sort(key=lambda item: item.get("score", 0), reverse=True)

    return {
        "results": results,
        "warning": "Les décisions doivent être importées depuis des sources officielles et vérifiées."
    }
