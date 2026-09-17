# Summary v2 — des comptes-rendus de réunion enfin exploitables

*Contribution au Challenge LaSuite. Ce dossier `pitch/` explique l'idée, contient
le pitch (sketch + visuel) et le matériau réel qui l'étaye.*

---

## Le problème

La Suite (Visio, Dictaphone) sait transcrire une réunion. Mais le **compte-rendu**
généré aujourd'hui est décevant : locuteurs anonymes (`SPEAKER_00`), acronymes
massacrés par la reconnaissance vocale (« dix nomme » pour DINUM, « la quenil »
pour la CNIL), structure générique quel que soit le type de réunion. Résultat :
des agents qui assistent à des réunions inutiles faute de CR fiable.

## L'idée : **Summary v2**

Élever la **qualité du compte-rendu** en deux temps, sans jamais réécrire le
transcript de l'utilisateur :

1. **Nettoyer le transcript** (travail de l'équipe) : retrouver les vrais noms des
   locuteurs, corriger les sigles mal transcrits.
2. **Contextualiser le résumé** (cette contribution) : comprendre *de quelle
   organisation* et *de quel type de réunion* il s'agit, pour produire un CR
   pertinent et au bon format.

Le tout **souverain**, exécuté sur **Albert** (le LLM de l'État).

## Les 3 améliorations — une chaîne à 3 briques

```
Transcription
  → [1] Résolution des locuteurs      SPEAKER_00 → Nadia Berger
  → [2] Correction des acronymes ASR  « la quenil » → CNIL
  → [3] Génération de CR contextualisé  format + jargon adaptés à l'organisation
```

| # | Brique | Branche | Statut |
|---|---|---|---|
| 1 | Résolution des locuteurs (indices de la conversation) | `feat/cue-based-speaker-fallback` | équipe |
| 2 | Correction phonétique des acronymes (glossaire 7769 entrées) | `feat/acronym-correction` | équipe |
| 3 | **CR contextualisé au bon format** | `feat/context-aware-summary` → **PR #1** | cette contribution |

Les trois briques sont **complémentaires** et **composables** : chacune sous son
flag, elles ne se marchent pas dessus. La brique 3 ne touche pas aux prompts de
génération existants (diff 100 % additif).

## Comment marche la brique 3 (le `prompt.py`)

Avant de résumer, une **phase d'analyse de contexte** déduit du transcript (et de
métadonnées éventuelles) : le **type de réunion** (gouvernance, suivi de projet,
team meeting, arbitrage…), le **contexte métier** (organisation, domaine) et le
**format de CR attendu**. Ce contexte adapte ensuite le vocabulaire, le ton et la
**structure** du compte-rendu.

Décisions produit importantes :
- **On ne développe PAS les acronymes** : le CR les **retranscrit tels quels** (les
  agents les maîtrisent). Le rôle du CR est la fidélité, pas la traduction.
- **On n'invente jamais** : garde-fous contre l'extrapolation de dates, le small
  talk, et l'hallucination de remplissage sur une réunion sans substance.
- **Attribution par vrais noms**, jamais un `SPEAKER_00` brut dans le CR.

### Le levier : la « fiche organisation »
Une petite fiche par organisation (nom, domaine, acronymes maison, format de CR
préféré) suffit à rendre le CR *vraiment* pertinent. Fournie d'abord via un
modèle à déposer ; à terme, une base de fiches appelée automatiquement.
**Une org : une fiche.**

## Le pitch (dans ce dossier)

- **`sketch-summary-v2.md`** — sketch de 2 min, **parodie de pub de lessive** :
  un t-shirt grisâtre (CR sale) vs éclatant (CR propre). Présente les bénéfices
  sans jargon, avec des exemples fonction publique (DINUM, CNIL).
- **`summary-v2-pub.html`** — l'**illustration avant/après** à projeter derrière le
  sketch (tricolore bleu-blanc-rouge, 16:9). *Ouvrir dans un navigateur → plein
  écran.*

## Le matériau : un vrai avant/après (pas une maquette)

Les extraits du visuel viennent de **vrais outputs** générés sur Albert, dans
`demo-material/` :
- `pub-before.md` / `pub-after.md` — un COPIL fonction publique, avant/après
  nettoyage du transcript (SPEAKER + sigles ASR → noms + sigles corrects).
- `fiche-ministere.md` — la fiche de contexte utilisée.

Les sigles « corrigés » (AIPD, CNIL, ANSSI, DINUM) sont tous **présents dans le
glossaire** de la brique de correction (`acronyms.json`) : la correction est donc
prouvable, pas inventée.

## Où est quoi

| Emplacement | Contenu |
|---|---|
| **PR #1** (`feat/context-aware-summary`) | le produit : `prompt.py` |
| **PR #2** (`pitch/challenge-summary-v2`) | ce dossier `pitch/` : idée + sketch + visuel + matériau |
| Repo local `lasuite-summary` (hors GitHub) | corpus élargi, harness de test, docs de conception |

## Reproduire l'avant/après

Avec un endpoint Albert (compatible OpenAI) et le harness de test
(`run_summary.py`, dans le repo local) :

```bash
export LLM_BASE_URL=https://albert.api.etalab.gouv.fr/v1 LLM_MODEL=openweight-large LLM_API_KEY=...
python harness/run_summary.py --mode baseline --transcript demo-material/pub-before.md
python harness/run_summary.py --mode enriched --transcript demo-material/pub-after.md --fiche demo-material/fiche-ministere.md
```

## Prochaines étapes

1. Merger PR #1 et brancher la phase de contexte dans `celery_worker` (recette dans
   la docstring de `prompt.py`), gardée par un flag.
2. Réunir les 3 briques (résolution locuteurs + correction acronymes + CR contexte)
   pour une démo de bout en bout.
3. Base de fiches par organisation ; à terme, empreinte vocale locale et temporaire
   (RGPD) pour la reconnaissance des participants.
