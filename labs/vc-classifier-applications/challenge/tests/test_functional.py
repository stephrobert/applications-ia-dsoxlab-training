"""Classer quatre demandes : trois contrôles, un par point du cadrage.

## D'où viennent les valeurs

La grille (critères, échelles, classe par score, règle de relèvement, politique
de chaque classe) vit dans UN seul fichier, `fixtures/grille.toml`, tiré de
`doctrine_labs.classification` du cadrage (seuils décidés le 2026-11-15).
Ces tests la relisent depuis `fixtures/` (jamais depuis `challenge/work`,
que l'apprenant peut modifier) : un seuil qui change ne touche que ce fichier.

Ce que ces tests ajoutent à la grille, ce sont les LECTURES de référence des
quatre demandes (`LECTURES` ci-dessous) : la valeur de chaque critère telle
que le texte de la demande la donne. La classe attendue se CALCULE à partir
d'elles et de la grille, elle n'est écrite nulle part.

## Ce que les tests rejouent

Le script de calcul `classify.py` de `fixtures/` (intact), lancé sur le
`classification.toml` de l'apprenant. Le script vérifie la cohérence ; les
tests vérifient en plus que les critères correspondent aux demandes, ce
qu'aucun script ne peut savoir à la place de l'apprenant.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-classifier-applications"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
GRILLE = tomllib.loads((FIXTURES / "grille.toml").read_text(encoding="utf-8"))

# La lecture de référence de chaque demande de fixtures/demandes/.
LECTURES: dict[str, dict[str, str]] = {
    "portail-achats": {
        "donnees": "personnelles",
        "flux_si": "lecture",
        "utilisateurs": "equipe",
        "criticite_metier": "importante",
    },
    "convertisseur-unites": {
        "donnees": "aucune",
        "flux_si": "aucun",
        "utilisateurs": "auteur_seul",
        "criticite_metier": "aucune",
    },
    "glossaire-achats": {
        "donnees": "internes",
        "flux_si": "aucun",
        "utilisateurs": "equipe",
        "criticite_metier": "utile",
    },
    "reassort-stock": {
        "donnees": "internes",
        "flux_si": "ecriture",
        "utilisateurs": "equipe",
        "criticite_metier": "utile",
    },
}


def _classe(lecture: dict[str, str]) -> str:
    """La classe d'une lecture : le critère le plus élevé l'emporte."""
    score = max(GRILLE["criteres"][c][v] for c, v in lecture.items())
    return str(GRILLE["classe_par_score"][str(score)])


def _rang(classe: object) -> int:
    return int(classe[1]) if isinstance(classe, str) and classe in ("C1", "C2", "C3", "C4") else 0


ATTENDUES = {nom: _classe(lecture) for nom, lecture in LECTURES.items()}
DEMANDEES = {
    nom: app["classe_demandee"]
    for nom, app in tomllib.loads(
        (FIXTURES / "classification.toml").read_text(encoding="utf-8")
    )["applications"].items()
}


@pytest.fixture(scope="module")
def classification() -> dict[str, Any]:
    exiger_workdir(WORKDIR, LAB_ID)
    chemin = WORKDIR / "classification.toml"
    assert chemin.is_file(), message(
        en="classification.toml is missing from challenge/work.",
        fr="classification.toml est absent de challenge/work.",
    )
    try:
        contenu = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        pytest.fail(message(
            en=f"classification.toml is not valid TOML: {erreur}",
            fr=f"classification.toml n'est pas un TOML valide : {erreur}",
        ))
    applications = contenu.get("applications", {})
    return applications if isinstance(applications, dict) else {}


@pytest.fixture(scope="module")
def verdicts(classification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Le script de calcul d'origine, rejoué sur le fichier de l'apprenant."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(FIXTURES / "classify.py"), "--json",
         "--grille", str(FIXTURES / "grille.toml"),
         "--classification", str(WORKDIR / "classification.toml")],
        capture_output=True, text=True, timeout=60, check=False, env=env,
    )
    try:
        sortie = json.loads(execution.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"classify.py gave no usable result:\n{execution.stderr[-800:]}",
            fr=f"classify.py n'a rendu aucun résultat exploitable :\n{execution.stderr[-800:]}",
        ))
    return {r["application"]: r for r in sortie.get("applications", [])}


def _application(classification: dict[str, Any], nom: str) -> dict[str, Any]:
    app = classification.get(nom)
    assert isinstance(app, dict), message(
        en=f"classification.toml has no [applications.{nom}] table.",
        fr=f"classification.toml n'a pas de table [applications.{nom}].",
    )
    return app


def _lecture_conforme(app: dict[str, Any], nom: str) -> None:
    criteres = app.get("criteres", {})
    for critere, attendu in LECTURES[nom].items():
        obtenu = criteres.get(critere) if isinstance(criteres, dict) else None
        assert obtenu == attendu, message(
            en=f"{nom}: criterion {critere} is `{obtenu}`. Read the request again "
            f"(demandes/{nom}.md) and the examples of grille.toml.",
            fr=f"{nom} : le critère {critere} vaut `{obtenu}`. Relisez la demande "
            f"(demandes/{nom}.md) et les exemples de grille.toml.",
        )


def test_la_classe_sous_evaluee_est_rejetee(
    classification: dict[str, Any], verdicts: dict[str, dict[str, Any]]
) -> None:
    portail = _application(classification, "portail-achats")
    _lecture_conforme(portail, "portail-achats")

    for nom, demandee in DEMANDEES.items():
        app = _application(classification, nom)
        assert app.get("classe_demandee") == demandee, message(
            en=f"{nom}: classe_demandee is what the requester asked for "
            f"({demandee}); it is not yours to change.",
            fr=f"{nom} : classe_demandee est ce que le demandeur a demandé "
            f"({demandee}) ; ce n'est pas à vous de la changer.",
        )
        attendue = "rejetee" if _rang(demandee) < _rang(ATTENDUES[nom]) else "acceptee"
        assert app.get("decision_demande") == attendue, message(
            en=f"{nom}: the request for {demandee} must be `{attendue}`, it is "
            f"`{app.get('decision_demande')}`. A request is rejected when, and only "
            "when, it asks for less than the grid gives.",
            fr=f"{nom} : la demande de {demandee} doit être `{attendue}`, elle est "
            f"`{app.get('decision_demande')}`. Une demande est rejetée quand, et "
            "seulement quand, elle demande moins que ce que donne la grille.",
        )

    retenue = portail.get("classe_retenue")
    assert _rang(retenue) >= _rang(ATTENDUES["portail-achats"]), message(
        en=f"portail-achats is retained in `{retenue}`, below what the grid gives. "
        "The requester's class is not a decision.",
        fr=f"portail-achats est retenu en `{retenue}`, sous ce que donne la grille. "
        "La classe du demandeur n'est pas une décision.",
    )
    verdict = verdicts.get("portail-achats", {})
    assert verdict.get("request_ok") and verdict.get("class_ok"), message(
        en=f"classify.py does not accept the class of portail-achats: "
        f"{verdict.get('problems')}",
        fr=f"classify.py n'accepte pas la classe de portail-achats : "
        f"{verdict.get('problems')}",
    )


def test_la_politique_suit_la_classe(
    classification: dict[str, Any], verdicts: dict[str, dict[str, Any]]
) -> None:
    politiques = set()
    for nom, attendue in ATTENDUES.items():
        app = _application(classification, nom)
        retenue = app.get("classe_retenue")
        ecart = _rang(retenue) - _rang(attendue)
        assert _rang(retenue) and ecart >= 0, message(
            en=f"{nom}: retained in `{retenue}`. A class may be raised, never lowered "
            "below the one the grid gives without a written human decision.",
            fr=f"{nom} : retenu en `{retenue}`. Une classe peut être relevée, jamais "
            "abaissée sous celle que donne la grille sans décision humaine écrite.",
        )
        verdict = verdicts.get(nom, {})
        assert verdict.get("policy_ok"), message(
            en=f"{nom}: the policy applied is not the one {retenue} imposes: "
            f"{verdict.get('problems')}",
            fr=f"{nom} : la politique appliquée n'est pas celle qu'impose "
            f"{retenue} : {verdict.get('problems')}",
        )
        politique = app.get("politique", {})
        politiques.add((
            tuple(sorted(politique.get("controles", []))),
            politique.get("duree_autorisation_mois"),
            politique.get("fiches_decision_signees"),
        ))
    assert len(politiques) >= 3, message(
        en="Four applications of different risk end up with fewer than three "
        "different policies.",
        fr="Quatre applications de risques différents finissent avec moins de "
        "trois politiques différentes.",
    )


def test_le_critere_le_plus_eleve_l_emporte(
    classification: dict[str, Any], verdicts: dict[str, dict[str, Any]]
) -> None:
    reassort = _application(classification, "reassort-stock")
    _lecture_conforme(reassort, "reassort-stock")
    attendue = ATTENDUES["reassort-stock"]
    assert reassort.get("classe_retenue") == attendue, message(
        en=f"reassort-stock is retained in `{reassort.get('classe_retenue')}`. A "
        "small team does not lower the class: the highest criterion wins.",
        fr=f"reassort-stock est retenu en `{reassort.get('classe_retenue')}`. Une "
        "petite équipe ne fait pas baisser la classe : le critère le plus élevé "
        "l'emporte.",
    )
    verdict = verdicts.get("reassort-stock", {})
    assert verdict.get("computed_class") == attendue and verdict.get("class_ok"), message(
        en=f"classify.py computes `{verdict.get('computed_class')}` for "
        f"reassort-stock: {verdict.get('problems')}",
        fr=f"classify.py calcule `{verdict.get('computed_class')}` pour "
        f"reassort-stock : {verdict.get('problems')}",
    )
