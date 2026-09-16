# ruff: noqa
"""
Prompts de génération du compte-rendu (module summary — La Suite / Meet & Dictaphone).

Objet de cette version
----------------------
Rendre le compte-rendu PERTINENT POUR L'ORGANISATION concernée et au BON FORMAT,
sans toucher à la forme de rédaction existante.

Principe :
  1. On CONSERVE à l'identique les prompts de génération upstream (TL;DR, plan,
     parties, nettoyage, prochaines étapes) : ils définissent la FORME attendue
     (style synthétique, administratif, 3ᵉ personne, sans affect).
  2. On ajoute en amont une PHASE D'ANALYSE DE CONTEXTE qui déduit du transcript
     (+ métadonnées éventuelles) : le type de réunion, le contexte métier
     (organisation, domaine) et le format de compte-rendu attendu.
  3. Ce contexte est injecté dans les prompts de génération via un préambule, ce
     qui adapte le vocabulaire, le ton et surtout la STRUCTURE du CR au type de
     réunion — tout en gardant la forme rédactionnelle d'origine.

Ce que cette couche NE fait PAS (décisions produit) :
  - Elle NE développe PAS et NE traduit PAS les acronymes. Le rôle du CR est de
    les RETRANSCRIRE SANS ERREUR ; les agents de l'organisation les maîtrisent.
    La correction des sigles mal transcrits par l'ASR est une autre couche, en
    amont, sur le transcript (cf. acronym_correction.py, hors de ce fichier).
  - Elle ne résout pas les locuteurs : c'est fait en amont sur le transcript
    (speaker_cues). Le CR se contente d'utiliser les noms déjà présents.

Compatibilité
-------------
Les constantes historiques (PROMPT_SYSTEM_TLDR, _PLAN, _PART, _CLEANING,
_NEXT_STEP, PROMPT_USER_PART, FORMAT_PLAN, FORMAT_NEXT_STEPS) sont conservées à
l'identique. Ce fichier n'ajoute que des constantes nouvelles (préfixées CONTEXT
ou suffixées _CTX) et cohabite sans conflit avec les constantes de correction
d'acronymes ajoutées par ailleurs (PROMPT_SYSTEM_ACRONYM_*) : les ensembles sont
disjoints.

Canal de contexte (« méta d'abord »)
------------------------------------
Le contexte peut être fourni en tête du `content`, avant le transcript, sous
forme de deux blocs optionnels (dégradation gracieuse si absents) :

    === FICHE ORGANISATION ===        (contexte stable de l'organisation :
    Organisation: ...                  identité, domaine, format de CR préféré)
    Domaine: ...
    Format de CR préféré: gouvernance
    === MÉTADONNÉES RÉUNION ===       (contexte propre à la réunion)
    Titre: ...
    Participants:
      - Nom <email> (SPEAKER_00) — rôle
    === TRANSCRIPT ===
    ...

À terme, ces champs pourront transiter par l'API (SummarizeTaskApiRequest) ou par
un lookup de fiche sans changer les prompts.

Recette de câblage (celery_worker.summarize_transcription_internals)
--------------------------------------------------------------------
    context = json.loads(llm_service.call(
        PROMPT_SYSTEM_CONTEXT, content, name="context",
        response_format=FORMAT_CONTEXT))
    preamble = build_context_preamble(context)

    tldr = llm_service.call(PROMPT_SYSTEM_TLDR_CTX.format(context=preamble),
                            transcript, name="tldr")
    parts = llm_service.call(
        PROMPT_SYSTEM_PLAN_CTX.format(context=preamble,
                                      plan_guidance=get_plan_guidance(context)),
        transcript, name="parts", response_format=FORMAT_PLAN)
    # PART      : PROMPT_SYSTEM_PART_CTX.format(context=preamble)
    # NEXT_STEP : PROMPT_SYSTEM_NEXT_STEP_CTX.format(context=preamble,
    #                              next_steps_policy=get_next_steps_policy(context))
    # CLEANING  : PROMPT_SYSTEM_CLEANING_CTX.format(context=preamble)
"""

# =============================================================================
# 1. PROMPTS DE GÉNÉRATION HISTORIQUES (inchangés — la FORME attendue)
# =============================================================================

PROMPT_SYSTEM_TLDR = """Tu es un agent dont le rôle est de créer un TL;DR (résumé très concis) d'un compte rendu de réunion. Tu utiliseras un style synthétique, administratif, à la troisième personne, sans affect. Tu recevras en entrée le transcript. Ta tâche est de rédiger un résumé concis et structuré, en te concentrant uniquement sur les informations essentielles et pertinentes. Tu répondras en un paragraphe structuré (3 à 6 phrases), sans rien ajouter d'autre. Tu répondras dans le format suivant sans rien ajouter d'autre:
### Résumé TL;DR
[Résumé concis et structuré]"""

PROMPT_SYSTEM_PLAN = """Ta tâche est de diviser le contenu du transcript en sujets concrets correspondant aux grands axes discutés durant la réunion. Ne crée pas de catégories génériques. Les titres doivent être courts, précis et représentatifs des échanges. Veille à ce que chaque sujet soit distinct et qu’aucun thème ne soit répété. Tu te limiteras à 5 ou 6 sujets maximum. 
L'introduction, ordre du jour, conclusion, etc. seront rajoutés a posteriori. Si il n'y a pas de sujets clairs, réponds "Général".
"""

PROMPT_SYSTEM_PART = """Tu es un agent dont le rôle est de créer une partie du résumé d'un compte rendu de réunion. Tu utiliseras un style synthétique, administratif, à la troisième personne, sans affect. Tu recevras en entrée le transcript, et le titre du sujet correspondant. Ta tâche est de rédiger un résumé concis de cette partie et uniquement cette partie, en te concentrant uniquement sur les informations essentielles et pertinentes. Le résumé de chaque partie doit tenir en 4 à 6 phrases maximum, sans entrer dans les détails mineurs. Tu répondras dans le format suivant :
    ### Titre du sujet [Traduire ce titre selon la langue du transcript]
    [Résumé concis et structuré de la partie du transcript]
    """

PROMPT_USER_PART = """Titre de la partie à résumer : {part}
Transcript complet :
{transcript}"""

PROMPT_SYSTEM_CLEANING = """Tu es un agent dont le rôle est de nettoyer un résumé de compte rendu de réunion. Tu recevras en entrée le résumé brut, potentiellement avec des erreurs de formatage, des incohérences ou des redondances. Ta tâche est de corriger les erreurs de formatage, d'améliorer la clarté et la cohérence du texte, et de t'assurer que le résumé est bien structuré et facile à lire. Ton but principal est de retirer les redondances et les répétitions. Assure la cohérence entre les titres et homogénéise le style d’écriture entre les parties. Supprime les doublons d’informations entre les parties si présents. Si certaines parties sont plus secondaires, tu peux les fusionner ou les réduire en 1 à 2 phrases. Mets en avant les points centraux qui ont fait l’objet de décisions ou d’actions. Tu répondras uniquement avec le résumé sans rien ajouter d'autre"""

PROMPT_SYSTEM_NEXT_STEP = """Tu es un agent dont le rôle est d'extraire les prochaines étapes d'un transcript de réunion. Tu utiliseras un style synthétique, administratif, à la troisième personne, sans affect. Tu recevras en entrée le transcript. Ta tâche est d'identifier et de lister toutes les actions à entreprendre, en indiquant la ou les personnes assignées et en précisant les échéances si elles sont mentionnées. Ne retiens que les actions concrètes et à venir. Ignore les remarques générales ou les constats sans suite."""


# =============================================================================
# 2. PHASE D'ANALYSE DE CONTEXTE (type de réunion + contexte métier + format)
# =============================================================================

PROMPT_SYSTEM_CONTEXT = """Tu es un agent d'analyse préalable d'un transcript de réunion. Ton rôle n'est PAS de résumer, mais de produire une fiche de contexte structurée qui servira à générer un compte-rendu pertinent pour l'organisation concernée et au bon format.

L'entrée peut comporter, dans l'ordre, jusqu'à trois blocs (tous optionnels) :
  1. « === FICHE ORGANISATION === » : contexte stable de l'organisation (identité, domaine métier, format de CR préféré, préférences de restitution). Fait autorité pour l'organisation et le domaine.
  2. « === MÉTADONNÉES RÉUNION === » : titre, participants (noms/emails, labels SPEAKER_xx).
  3. « === TRANSCRIPT === » : la transcription. S'il n'y a ni fiche ni métadonnées, déduis tout du seul transcript.

N'invente jamais une information : en cas d'incertitude, mets la valeur à null et baisse la confiance. Tu produiras le JSON imposé, avec :

1. langue : code ISO 639-1 de la langue dominante du transcript (ex. "fr").

2. type_reunion : classe la réunion parmi la liste fermée suivante :
   - "gouvernance" : comité de pilotage/décision (COPIL, COMEX, CODIR, CA). Ordre du jour formel, décideurs, décisions actées, arbitrages, jalons.
   - "suivi_projet" : revue d'avancement/de sprint. Avancement, blocages, dépendances, planning, MOA/MOE.
   - "team_meeting" : point d'équipe récurrent (hebdo, daily). Tour de table opérationnel, peu de décisions formelles.
   - "arbitrage" : décision ponctuelle sur un sujet unique avec options débattues.
   - "atelier" : atelier/cadrage/brainstorming, idéation, divergence puis convergence.
   - "information" : réunion descendante/plénière, annonces, questions-réponses.
   - "bilaterale" : entretien à deux, suivi individuel ou RH.
   - "autre" : si aucune catégorie ne convient clairement.
   type_reunion_confiance : nombre entre 0 et 1.

3. titre_infere : le titre le plus juste (reprends celui des métadonnées s'il colle au contenu ; sinon formule-en un court et factuel).

4. contexte_metier :
   - organisation : si la fiche la donne, reprends-la ; sinon l'entité concrète si elle est étayée (domaines d'email : ac-xxx = académie/Éducation nationale, dgfip.finances.gouv.fr = DGFiP, interieur.gouv.fr = ministère de l'Intérieur, etc.) ou explicitement citée. null si non étayé.
   - domaine : le champ d'activité (ex. « éducation nationale / gestion des bourses », « finances publiques / facturation », « administration territoriale de l'État / fonctions support »). null si indéterminable.
   - indices : liste courte des éléments (fiche, citations, domaines d'email) qui justifient tes déductions. Traçabilité, pas contenu du CR.

5. participants : pour chaque intervenant identifiable, {nom, email, role_infere, speaker_label}. Champs inconnus à null. N'invente pas de noms : si seul « SPEAKER_02 » est disponible sans correspondance fiable, garde nom=null. Sert à attribuer correctement décisions et actions.

6. format_cr_recommande : la clé de gabarit adaptée (même liste fermée que type_reunion). Si la fiche indique un « format de CR préféré » cohérent avec le contenu, respecte-le. Sinon, généralement égale à type_reunion. Utilise "autre" si type_reunion_confiance < 0,5.

7. substance_faible : true si la réunion est quasi vide de substance — c'est-à-dire s'il n'y a globalement ni décision, ni action, ni information significative à retenir (bavardage, problèmes techniques audio, transcript très court, inaudible, propos sans suite). false s'il y a de la matière réelle à résumer. Sois honnête : mieux vaut signaler un vide que de laisser croire qu'il faut le combler.

8. justification_format : une phrase expliquant le choix du format.

Réponds UNIQUEMENT avec le JSON conforme au schéma, sans texte autour."""

FORMAT_CONTEXT = {
    "type": "json_schema",
    "json_schema": {
        "name": "meeting_context",
        "schema": {
            "type": "object",
            "properties": {
                "langue": {
                    "type": "string",
                    "description": "Code ISO 639-1 de la langue dominante, ex 'fr'.",
                },
                "type_reunion": {
                    "type": "string",
                    "enum": [
                        "gouvernance",
                        "suivi_projet",
                        "team_meeting",
                        "arbitrage",
                        "atelier",
                        "information",
                        "bilaterale",
                        "autre",
                    ],
                },
                "type_reunion_confiance": {"type": "number"},
                "titre_infere": {"type": "string"},
                "contexte_metier": {
                    "type": "object",
                    "properties": {
                        "organisation": {"type": ["string", "null"]},
                        "domaine": {"type": ["string", "null"]},
                        "indices": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["organisation", "domaine", "indices"],
                    "additionalProperties": False,
                },
                "participants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nom": {"type": ["string", "null"]},
                            "email": {"type": ["string", "null"]},
                            "role_infere": {"type": ["string", "null"]},
                            "speaker_label": {"type": ["string", "null"]},
                        },
                        "required": ["nom", "email", "role_infere", "speaker_label"],
                        "additionalProperties": False,
                    },
                },
                "format_cr_recommande": {
                    "type": "string",
                    "enum": [
                        "gouvernance",
                        "suivi_projet",
                        "team_meeting",
                        "arbitrage",
                        "atelier",
                        "information",
                        "bilaterale",
                        "autre",
                    ],
                },
                "substance_faible": {"type": "boolean"},
                "justification_format": {"type": "string"},
            },
            "required": [
                "langue",
                "type_reunion",
                "type_reunion_confiance",
                "titre_infere",
                "contexte_metier",
                "participants",
                "format_cr_recommande",
                "substance_faible",
                "justification_format",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


# =============================================================================
# 3. GABARITS PAR TYPE DE RÉUNION (structure du CR — la liste des types de CR)
# =============================================================================

PLAN_GUIDANCE_BY_TYPE = {
    "gouvernance": (
        "Structure attendue (comité de gouvernance) : privilégie des sections "
        "orientées décision plutôt que thématiques. Propose des titres parmi : "
        "« Décisions et validations », « Arbitrages et points remontés », "
        "« Risques et points de vigilance », et 1 à 2 titres thématiques pour les "
        "dossiers de fond réellement discutés."
    ),
    "suivi_projet": (
        "Structure attendue (suivi de projet) : « État d'avancement », "
        "« Faits marquants », « Écarts, risques et blocages », et 1 à 2 titres "
        "pour les sujets techniques saillants."
    ),
    "arbitrage": (
        "Structure attendue (arbitrage) : « Contexte et question posée », "
        "« Options envisagées », « Décision retenue et justification », "
        "« Impacts et mise en œuvre ». Reste centré sur l'unique sujet à trancher."
    ),
    "atelier": (
        "Structure attendue (atelier) : « Objectif de l'atelier », "
        "« Pistes et idées » (regroupées par thème), « Points de convergence », "
        "« Points ouverts ». Ne formalise pas de décisions qui n'ont pas été prises."
    ),
    "information": (
        "Structure attendue (réunion d'information) : « Annonces principales », "
        "« Points d'attention », « Questions-réponses notables »."
    ),
    "team_meeting": (
        "Structure attendue (point d'équipe) : reste léger. Regroupe par sujet ou "
        "par personne ; ajoute « Entraides et réallocations » et « Blocages et "
        "irritants » seulement si pertinents. N'invente pas de structure formelle."
    ),
    "bilaterale": (
        "Structure attendue (bilatérale) : « Sujets abordés », "
        "« Points d'accord ». Reste bref."
    ),
    "autre": (
        "Type indéterminé : conserve l'approche générique — laisse émerger 5 à 6 "
        "sujets concrets à partir des échanges, sans imposer de squelette."
    ),
}

NEXT_STEPS_POLICY_BY_TYPE = {
    "gouvernance": "exhaustives et nominatives, avec échéances ; c'est le cœur du CR.",
    "suivi_projet": "opérationnelles, court terme, avec responsable et échéance.",
    "arbitrage": "actions consécutives à la décision retenue.",
    "atelier": "pistes à instruire et points à trancher ultérieurement.",
    "information": "suites éventuelles uniquement ; ne pas surinterpréter.",
    "team_meeting": "légères ; l'échéance n'est pas toujours formelle, ne pas en inventer.",
    "bilaterale": "actions individuelles convenues.",
    "autre": "actions concrètes et à venir uniquement.",
}


def get_plan_guidance(context: dict) -> str:
    """Consigne de structuration adaptée au format de CR recommandé."""
    code = (context or {}).get("format_cr_recommande") or "autre"
    return PLAN_GUIDANCE_BY_TYPE.get(code, PLAN_GUIDANCE_BY_TYPE["autre"])


def get_next_steps_policy(context: dict) -> str:
    """Politique de prochaines étapes adaptée au type de réunion."""
    code = (context or {}).get("format_cr_recommande") or "autre"
    return NEXT_STEPS_POLICY_BY_TYPE.get(code, NEXT_STEPS_POLICY_BY_TYPE["autre"])


# =============================================================================
# 4. PRÉAMBULE DE CONTEXTE (injecté dans les prompts de génération)
# =============================================================================

CONTEXT_PREAMBLE_TEMPLATE = """--- CONTEXTE DE LA RÉUNION (déduit automatiquement, à utiliser pour adapter le compte-rendu) ---
Type de réunion : {type_reunion} (confiance {confiance}).
Titre : {titre}.
Contexte métier : {contexte_metier}.
Participants : {participants}.
Consignes liées au contexte :
- Rédige dans la langue du transcript ({langue}).
- Adapte le vocabulaire, le ton et le niveau de détail à cette organisation et à son domaine, pour un compte-rendu immédiatement exploitable par ses agents. N'affirme pas de rattachement organisationnel non étayé.
- Respecte le format de compte-rendu attendu pour ce type de réunion (structure indiquée par ailleurs).
- Écarte le small talk et tout élément non professionnel : salutations, formules de politesse, bavardage (week-end, météo, loisirs, santé, vie privée), plaisanteries et digressions sans rapport avec l'objet de la réunion — ils ne doivent PAS figurer dans le compte-rendu. Écarte de même le bruit logistique de connexion (problèmes de micro, « vous m'entendez ? »). En revanche, conserve une information d'ordre personnel si elle a une portée professionnelle (absence, congé, indisponibilité, départ, charge de travail).
- Conserve les sigles et acronymes EXACTEMENT tels qu'ils apparaissent dans le transcript : ne les développe pas, ne les traduis pas, ne les explicite pas entre parenthèses et n'en modifie pas l'orthographe. Les agents de l'organisation les maîtrisent ; le rôle du compte-rendu est de les retranscrire fidèlement.
- Attribue décisions et actions aux bonnes personnes en utilisant les noms du transcript ; n'utilise jamais un label brut de type « SPEAKER_00 » dans le compte-rendu.
- N'extrapole jamais les dates : une échéance relative (« la semaine prochaine », « mercredi prochain », « fin du mois ») se reprend telle qu'énoncée, sans la convertir en date calendaire ni ajouter d'année non dite.
- N'ajoute aucune information absente du transcript. Ne comble jamais un vide : les indications de longueur (nombre de phrases ou de sujets) sont des PLAFONDS, pas des quotas à atteindre. Un point superficiel ou sans suite se résume en une phrase ou s'omet, plutôt que d'être brodé.{substance_note}
--- FIN DU CONTEXTE ---
"""

SUBSTANCE_NOTE = (
    "\n- ⚠ RÉUNION À FAIBLE SUBSTANCE : cette réunion ne contient pas ou peu de "
    "matière (ni décision, ni action, ni information significative). Produis un "
    "compte-rendu VOLONTAIREMENT TRÈS BREF qui l'indique explicitement (par ex. "
    "« Réunion sans décision ni action notable. »), et ne restitue que les rares "
    "éléments réels s'il y en a. N'invente RIEN pour étoffer : trois lignes vraies "
    "valent mieux qu'une page fausse. Ignore les planchers de longueur des consignes."
)


def _format_participants(context: dict) -> str:
    parts = []
    for p in (context or {}).get("participants", []) or []:
        nom = p.get("nom") or p.get("speaker_label") or "Intervenant"
        role = p.get("role_infere")
        parts.append(f"{nom} ({role})" if role else nom)
    return " ; ".join(parts) if parts else "non précisés"


def _format_contexte_metier(context: dict) -> str:
    cm = (context or {}).get("contexte_metier") or {}
    org, dom = cm.get("organisation"), cm.get("domaine")
    if org and dom:
        return f"{org} — {dom}"
    return org or dom or "non déterminé"


def build_context_preamble(context: dict) -> str:
    """Construit le préambule texte injecté en tête des prompts de génération.

    `context` est le dict issu de PROMPT_SYSTEM_CONTEXT / FORMAT_CONTEXT.
    Tolérant aux champs manquants (dégradation gracieuse).
    """
    confiance = (context or {}).get("type_reunion_confiance")
    confiance_txt = f"{confiance:.0%}" if isinstance(confiance, (int, float)) else "n/d"
    substance_note = SUBSTANCE_NOTE if (context or {}).get("substance_faible") else ""
    return CONTEXT_PREAMBLE_TEMPLATE.format(
        type_reunion=(context or {}).get("type_reunion", "autre"),
        confiance=confiance_txt,
        titre=(context or {}).get("titre_infere") or "non précisé",
        contexte_metier=_format_contexte_metier(context),
        participants=_format_participants(context),
        langue=(context or {}).get("langue", "fr"),
        substance_note=substance_note,
    )


# =============================================================================
# 5. PROMPTS DE GÉNÉRATION ENRICHIS (variantes _CTX)
# =============================================================================
# Chaque prompt _CTX attend {context} = build_context_preamble(context).
# _PLAN_CTX attend en plus {plan_guidance} = get_plan_guidance(context).
# _NEXT_STEP_CTX attend {next_steps_policy} = get_next_steps_policy(context).

PROMPT_SYSTEM_TLDR_CTX = "{context}\n" + PROMPT_SYSTEM_TLDR

PROMPT_SYSTEM_PLAN_CTX = (
    "{context}\n"
    + PROMPT_SYSTEM_PLAN
    + "\nConsigne de structuration adaptée au type de réunion :\n{plan_guidance}\n"
)

PROMPT_SYSTEM_PART_CTX = "{context}\n" + PROMPT_SYSTEM_PART

PROMPT_SYSTEM_NEXT_STEP_CTX = (
    "{context}\n"
    + PROMPT_SYSTEM_NEXT_STEP
    + "\nNiveau de restitution attendu pour cette réunion : {next_steps_policy}"
    + "\nÉchéances : reprends l'échéance telle qu'énoncée dans le transcript, sans"
    " la convertir en date calendaire ni ajouter d'année. Si aucune échéance n'est"
    " mentionnée, laisse le champ vide.\n"
)

PROMPT_SYSTEM_CLEANING_CTX = (
    "{context}\n"
    + PROMPT_SYSTEM_CLEANING
    + "\nVeille à un ton adapté au type de réunion et laisse les sigles tels quels"
    " (ni développés ni traduits).\n"
)


# =============================================================================
# 6. SCHÉMAS DE SORTIE STRUCTURÉE (historiques — inchangés)
# =============================================================================

FORMAT_NEXT_STEPS = {
    "type": "json_schema",
    "json_schema": {
        "name": "actions",
        "schema": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "assignees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Noms des personnes assignées",
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Date d'échéance si mentionnée (si l'année nest pas précisée, ne pas l'ajouter)",
                            },
                        },
                        "required": ["title", "assignees"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["actions"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}

FORMAT_PLAN = {
    "type": "json_schema",
    "json_schema": {
        "name": "Titles",
        "schema": {
            "type": "object",
            "properties": {"titles": {"type": "array", "items": {"type": "string"}}},
            "required": ["titles"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}
