#!/usr/bin/env python3
"""Validate an application contract (application.yaml) against the policy.

Reads, from the POLICY repository, the JSON schema
(politique/schemas/application.schema.json), the classification grid
(politique/classification.json) and the register of requests
(politique/demandes.toml). A schema found in the candidate repository is
never used: a repository that brings its own rules validates itself.

Checks, in order:

- the contract matches the schema (required fields, types, values, no
  unknown field);
- classe_declaree is not below the class the grid computes;
- expire_le comes after date_creation and within the longest authorisation
  of the class;
- from C3, the business owner is not the requester.

Exit code: 0 valid, 1 invalid, 2 when a file cannot be read.
Standard library only (Python 3.11 or later).

    python3 plateforme/valider_fiche.py
    python3 plateforme/valider_fiche.py candidat/application.yaml --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from commun import (
    WORK,
    Illisible,
    ajouter_mois,
    classe_calculee,
    lire_fichier_yaml,
    lire_json,
    lire_toml,
    rang,
    valider,
    verifier_schema,
)


def regles_de_politique(
    fiche: dict[str, Any], grille: dict[str, Any], demandes: dict[str, Any]
) -> tuple[str | None, list[str]]:
    erreurs: list[str] = []
    calculee = classe_calculee(fiche, grille)
    declaree = fiche.get("classe_declaree")
    if calculee and rang(declaree) and rang(declaree) < rang(calculee):
        erreurs.append(
            f"classe_declaree: {declaree} is below {calculee}, the class the grid "
            "computes from this contract"
        )
    exigeante = declaree if rang(declaree) > rang(calculee) else calculee
    regles = grille["classes"].get(exigeante or "", {})
    try:
        debut = date.fromisoformat(str(fiche.get("date_creation")))
        fin = date.fromisoformat(str(fiche.get("expire_le")))
    except ValueError:
        debut = fin = None
    if debut and fin:
        if fin <= debut:
            erreurs.append("expire_le: must come after date_creation")
        mois = regles.get("duree_autorisation_mois", 0)
        if mois and fin > ajouter_mois(debut, mois):
            erreurs.append(
                f"expire_le: {fin} is beyond {mois} months after date_creation, "
                f"the longest authorisation of {exigeante}"
            )
    demandeur = demandes.get(str(fiche.get("id")), {}).get("demandeur")
    metier = fiche.get("proprietaire_metier")
    if (
        regles.get("proprietaire_metier_distinct_du_demandeur")
        and isinstance(metier, dict)
        and demandeur
        and metier.get("identifiant") == demandeur
    ):
        erreurs.append(
            f"proprietaire_metier: {demandeur} is the requester; from {exigeante} the "
            "business owner is someone else"
        )
    return calculee, erreurs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fiche", nargs="?", type=Path, default=WORK / "candidat" / "application.yaml")
    parser.add_argument("--politique", type=Path, default=WORK / "politique")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        schema = lire_json(args.politique / "schemas" / "application.schema.json")
        verifier_schema(schema)
        grille = lire_json(args.politique / "classification.json")
        demandes = lire_toml(args.politique / "demandes.toml")
        fiche = lire_fichier_yaml(args.fiche)
    except Illisible as erreur:
        if args.json:
            print(json.dumps({"lisible": False, "erreur": str(erreur)}, ensure_ascii=False))
        else:
            print(f"cannot read: {erreur}", file=sys.stderr)
        return 2

    if isinstance(fiche, dict):
        erreurs = valider(fiche, schema)
        calculee, autres = regles_de_politique(fiche, grille, demandes)
        erreurs += autres
    else:
        erreurs, calculee = ["(root): the contract is not a mapping of fields"], None

    if args.json:
        print(json.dumps({
            "lisible": True,
            "fichier": str(args.fiche),
            "valide": not erreurs,
            "erreurs": erreurs,
            "classe_calculee": calculee,
            "fiche": fiche,
        }, indent=2, ensure_ascii=False))
    else:
        try:
            nom = args.fiche.resolve().relative_to(Path.cwd())
        except ValueError:
            nom = args.fiche
        print(f"{nom}: computed class {calculee or '?'}")
        for erreur in erreurs:
            print(f"    - {erreur}")
        print("valid" if not erreurs else f"invalid: {len(erreurs)} problem(s)")
    return 0 if not erreurs else 1


if __name__ == "__main__":
    sys.exit(main())
