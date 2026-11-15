#!/usr/bin/env python3
"""The platform barrier: is this application authorised, and in which class?

Reads the POLICY repository only: its decisions (politique/decisions/), its
allowed_signers and its register of requests. From the candidate repository
it reads application.yaml, to compare its sha256 with the one the decision
signed. It never reads a decision, a key or a class from the candidate
repository: the contract there is a request, not a decision.

A reduced version of the course gate: there is no artefact yet at this
stage, so no digest is compared.

Exit codes:
  0   authorised
  10  no decision for this application in the policy repository
  11  signature missing or invalid, or signer absent from allowed_signers
  12  the decider is the requester
  13  role insufficient for the retained class (C4 needs a second decision
      from security; C1 is not deployed on the platform)
  14  decision expired, or longer than the class allows
  15  application.yaml differs from the one the decision signed
  16  classe_retenue is below the class the policy grid computes for
      application.yaml (a class may be raised, never lowered)
  2   a file or ssh-keygen cannot be used

The date of the day can be replaced with the DATE_SIMULEE variable
(YYYY-MM-DD). Standard library and ssh-keygen only.

    python3 plateforme/barriere.py portail-achats
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
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
)

NAMESPACE = "decision-applicative"
ACCEPTATIONS = ("accepte", "accepte_sous_conditions")
CHAMPS = (
    "id", "application", "fiche_sha256", "classe_retenue", "decision",
    "demandeur", "decideur", "date_decision", "expire_le",
)


def signature_valide(fichier: Path, signataire: str, allowed: Path) -> bool:
    signature = fichier.with_name(fichier.name + ".sig")
    if not signature.is_file() or not signataire:
        return False
    with fichier.open("rb") as entree:
        res = subprocess.run(  # noqa: S603
            ["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I", signataire,
             "-n", NAMESPACE, "-s", str(signature)],
            stdin=entree, capture_output=True, check=False, timeout=30,
        )
    return res.returncode == 0


def examiner(
    fichier: Path, app: str, demandeur: str, empreinte: str, allowed: Path,
    grille: dict[str, Any], jour: date, calculee: str | None,
) -> dict[str, Any]:
    """One decision: (code, reason). Code 0 = valid on its own."""
    def refus(code: int, motif: str) -> dict[str, Any]:
        return {"fichier": fichier.name, "code": code, "motif": motif}

    try:
        d = lire_fichier_yaml(fichier)
    except Illisible as erreur:
        return refus(10, f"unreadable decision: {erreur}")
    manquants = [c for c in CHAMPS if not isinstance(d, dict) or c not in d]
    if manquants:
        return refus(10, f"incomplete decision, missing {manquants}")
    decideur = d["decideur"] if isinstance(d["decideur"], dict) else {}
    qui = str(decideur.get("identifiant") or "")
    if d["application"] != app:
        return refus(10, f"decision for `{d['application']}`, not `{app}`")
    if d["decision"] not in ACCEPTATIONS:
        return refus(10, f"decision is `{d['decision']}`, not an acceptance")
    if not signature_valide(fichier, qui, allowed):
        return refus(11, f"no valid signature by `{qui}` known to allowed_signers")
    if qui in (demandeur, d["demandeur"]):
        return refus(12, f"`{qui}` decides on their own request")
    if d["fiche_sha256"] != empreinte:
        return refus(15, "application.yaml is not the one this decision signed")
    classe = d["classe_retenue"]
    if calculee is None:
        return refus(16, "the class of application.yaml cannot be computed with the "
                     "policy grid: run valider_fiche.py")
    if rang(classe) < rang(calculee):
        return refus(16, f"classe_retenue {classe} is below {calculee}, the class the "
                     "policy grid computes for application.yaml")
    mois = grille["classes"].get(classe, {}).get("duree_autorisation_mois")
    try:
        debut = date.fromisoformat(str(d["date_decision"]))
        fin = date.fromisoformat(str(d["expire_le"]))
    except ValueError:
        return refus(14, "date_decision or expire_le is not a date YYYY-MM-DD")
    if mois is None:
        return refus(13, f"classe_retenue `{classe}` is not a class")
    if mois == 0 or fin > ajouter_mois(debut, mois):
        return refus(14, f"expire_le goes beyond the {mois} months {classe} allows")
    if jour > fin:
        return refus(14, f"expired on {fin}")
    return {"fichier": fichier.name, "code": 0, "motif": "valid",
            "classe_retenue": classe, "role": decideur.get("role"), "expire_le": str(fin)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("application")
    parser.add_argument("--politique", type=Path, default=WORK / "politique")
    parser.add_argument("--candidat", type=Path, default=WORK / "candidat")
    parser.add_argument("--allowed-signers", type=Path, help="default: <politique>/allowed_signers")
    parser.add_argument("--demandes", type=Path, help="default: <politique>/demandes.toml")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    allowed = args.allowed_signers or args.politique / "allowed_signers"
    demandes_chemin = args.demandes or args.politique / "demandes.toml"

    def rendre(code: int, motif: str, **plus: Any) -> int:
        if args.json:
            print(json.dumps({"application": args.application, "code": code,
                              "autorisee": code == 0, "motif": motif, **plus},
                             indent=2, ensure_ascii=False))
        else:
            for d in plus.get("decisions", []):
                print(f"    {d['fichier']}: {d['code']} {d['motif']}")
            print(f"{args.application}: {'AUTHORISED' if code == 0 else 'REFUSED'} "
                  f"({code}) {motif}")
        return code

    try:
        jour = date.fromisoformat(os.environ.get("DATE_SIMULEE") or date.today().isoformat())
    except ValueError:
        return rendre(2, "DATE_SIMULEE is not a date YYYY-MM-DD")
    if not shutil.which("ssh-keygen"):
        return rendre(2, "ssh-keygen is not installed: no signature can be checked")
    try:
        grille = lire_json(args.politique / "classification.json")
        demandes = lire_toml(demandes_chemin)
        fiche = (args.candidat / "application.yaml").read_bytes()
    except (Illisible, OSError) as erreur:
        return rendre(2, f"cannot read: {erreur}")
    if not allowed.is_file():
        return rendre(2, f"cannot read: {allowed}")
    demandeur = demandes.get(args.application, {}).get("demandeur")
    if not demandeur:
        return rendre(10, "no request recorded for this application")
    empreinte = hashlib.sha256(fiche).hexdigest()
    # The class is recomputed from the contract with the grid of the POLICY
    # repository, never taken from classe_declaree: a decision may raise it,
    # not lower it.
    try:
        contenu = lire_fichier_yaml(args.candidat / "application.yaml")
        calculee = classe_calculee(contenu, grille) if isinstance(contenu, dict) else None
    except Illisible:
        calculee = None

    fichiers = sorted((args.politique / "decisions").glob(f"{args.application}-*.yaml"))
    if not fichiers:
        return rendre(10, "no decision in the policy repository", fiche_sha256=empreinte)
    decisions = [examiner(f, args.application, demandeur, empreinte, allowed, grille, jour,
                          calculee)
                 for f in fichiers]
    valides = [d for d in decisions if d["code"] == 0]
    if not valides:
        premier = decisions[-1]
        return rendre(premier["code"], premier["motif"], decisions=decisions,
                      fiche_sha256=empreinte)
    classe = max((d["classe_retenue"] for d in valides), key=rang)
    exiges = set(grille["classes"][classe]["decisions_signees"])
    roles = {d["role"] for d in valides if d["classe_retenue"] == classe}
    if classe == "C1":
        return rendre(13, "C1 is not deployed on the platform", decisions=decisions,
                      classe_retenue=classe, fiche_sha256=empreinte)
    if not exiges <= roles:
        return rendre(13, f"{classe} needs signed decisions from {sorted(exiges)}, "
                      f"found {sorted(r for r in roles if r)}", decisions=decisions,
                      classe_retenue=classe, fiche_sha256=empreinte)
    fin = min(d["expire_le"] for d in valides if d["classe_retenue"] == classe)
    return rendre(0, f"class {classe} until {fin}", decisions=decisions,
                  classe_retenue=classe, expire_le=fin, fiche_sha256=empreinte)


if __name__ == "__main__":
    sys.exit(main())
