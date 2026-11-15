#!/usr/bin/env python3
"""Compute the class of each application and compare it with yours.

Reads the grid (grille.toml) and your classification (classification.toml).
For each application it computes the class from the four criteria (the
highest criterion wins), then checks three things:

- the requested class: REJECTED when it is below the computed class;
- your retained class: refused below the computed class, or more than the
  allowed steps above it;
- the policy you applied: it must be the one the retained class imposes.

Exit code: 0 when every application is consistent, 1 otherwise, 2 when a
file cannot be read. Standard library only (Python 3.11 or later).

    python3 classify.py
    python3 classify.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

CRITERES = ("donnees", "flux_si", "utilisateurs", "criticite_metier")
CHAMPS_POLITIQUE = (
    "deploiement_plateforme",
    "controles",
    "approbation",
    "fiches_decision_signees",
    "duree_autorisation_mois",
)


def charger(chemin: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        print(f"cannot read {chemin}: {erreur}", file=sys.stderr)
        sys.exit(2)


def rang(classe: object) -> int | None:
    if isinstance(classe, str) and classe in ("C1", "C2", "C3", "C4"):
        return int(classe[1])
    return None


def classe_calculee(
    grille: dict[str, Any], criteres: dict[str, Any]
) -> tuple[str | None, list[str]]:
    erreurs = []
    scores = []
    for critere in CRITERES:
        valeur = criteres.get(critere)
        echelle = grille["criteres"][critere]
        if valeur not in echelle:
            erreurs.append(f"{critere} = {valeur!r} (expected one of: {', '.join(echelle)})")
        else:
            scores.append(echelle[valeur])
    if erreurs:
        return None, erreurs
    return grille["classe_par_score"][str(max(scores))], []


def politique_ok(grille: dict[str, Any], classe: str, politique: dict[str, Any]) -> list[str]:
    impose = grille["classes"][classe]["impose"]
    ecarts = []
    for champ in CHAMPS_POLITIQUE:
        if champ not in politique:
            ecarts.append(f"{champ} missing")
    if ecarts:
        return ecarts
    if politique["deploiement_plateforme"] is not impose["deploiement_plateforme"]:
        attendu = str(impose["deploiement_plateforme"]).lower()
        ecarts.append(f"deploiement_plateforme must be {attendu}")
    if sorted(politique["controles"]) != sorted(impose["controles"]):
        manquants = sorted(set(impose["controles"]) - set(politique["controles"]))
        en_trop = sorted(set(politique["controles"]) - set(impose["controles"]))
        ecarts.append(f"controles: missing {manquants}, not imposed {en_trop}")
    if politique["approbation"] != impose["approbation"]:
        ecarts.append(f"approbation must be {impose['approbation']!r}")
    if politique["fiches_decision_signees"] != impose["fiches_decision_signees"]:
        ecarts.append(f"fiches_decision_signees must be {impose['fiches_decision_signees']}")
    duree, maxi = politique["duree_autorisation_mois"], impose["duree_autorisation_mois"]
    if maxi == 0 and duree != 0:
        ecarts.append("duree_autorisation_mois must be 0 (no authorisation)")
    elif maxi and not (isinstance(duree, int) and 0 < duree <= maxi):
        ecarts.append(f"duree_autorisation_mois must be between 1 and {maxi}")
    return ecarts


def examiner(grille: dict[str, Any], nom: str, app: dict[str, Any]) -> dict[str, Any]:
    resultat: dict[str, Any] = {"application": nom, "problems": []}
    calculee, erreurs = classe_calculee(grille, app.get("criteres", {}))
    resultat["computed_class"] = calculee
    resultat["problems"] += erreurs
    demandee = app.get("classe_demandee")
    retenue = app.get("classe_retenue")
    resultat["requested_class"] = demandee
    resultat["retained_class"] = retenue

    if calculee is None:
        resultat.update(request_ok=False, class_ok=False, policy_ok=False)
        return resultat

    attendu = "rejetee" if (rang(demandee) or 0) < rang(calculee) else "acceptee"
    resultat["request_expected"] = attendu
    resultat["request_ok"] = app.get("decision_demande") == attendu
    if not resultat["request_ok"]:
        resultat["problems"].append(
            f"decision_demande = {app.get('decision_demande')!r}: requested {demandee}, "
            f"computed {calculee}"
        )

    r = rang(retenue)
    if r is None:
        resultat["class_ok"] = False
        resultat["problems"].append(f"classe_retenue = {retenue!r} (expected C1 to C4)")
    elif r < rang(calculee):
        resultat["class_ok"] = False
        resultat["problems"].append(
            f"classe_retenue {retenue} is below the computed class {calculee}"
        )
    else:
        resultat["class_ok"] = True

    if r is None:
        resultat["policy_ok"] = False
    else:
        ecarts = politique_ok(grille, retenue, app.get("politique", {}))
        resultat["policy_ok"] = not ecarts
        resultat["problems"] += [f"politique: {e}" for e in ecarts]
    return resultat


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grille", type=Path, default=Path("grille.toml"))
    parser.add_argument("--classification", type=Path, default=Path("classification.toml"))
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    grille = charger(args.grille)
    classification = charger(args.classification)
    applications = classification.get("applications", {})
    resultats = [examiner(grille, nom, app) for nom, app in applications.items()]
    bon = bool(resultats) and all(
        r["request_ok"] and r["class_ok"] and r["policy_ok"] for r in resultats
    )

    if args.json:
        print(json.dumps({"ok": bon, "applications": resultats}, indent=2, ensure_ascii=False))
    else:
        for r in resultats:
            etat = "OK" if r["request_ok"] and r["class_ok"] and r["policy_ok"] else "TO FIX"
            print(f"{r['application']:<22} requested {r['requested_class']!s:<4} "
                  f"computed {r['computed_class']!s:<4} retained {r['retained_class']!s:<4} {etat}")
            for probleme in r["problems"]:
                print(f"    - {probleme}")
        print("all consistent" if bon else "inconsistencies remain")
    return 0 if bon else 1


if __name__ == "__main__":
    sys.exit(main())
