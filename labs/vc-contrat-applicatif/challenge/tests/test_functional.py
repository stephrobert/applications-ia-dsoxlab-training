"""La fiche applicative du portail-achats : quatre contrôles, un par point du cadrage.

## D'où viennent les valeurs

Tout ce qui fait foi vient du dépôt de politique de `fixtures/politique/`,
jamais de `challenge/work`, que l'apprenant peut modifier : le schéma
(`schemas/application.schema.json`), la grille (`classification.json`), le
registre des demandes (`demandes.toml`) et `allowed_signers`. Ces fichiers
sont tirés de `doctrine_labs.contrat_applicatif` et
`doctrine_labs.classification` du cadrage.

Ce que ces tests ajoutent, c'est la LECTURE de référence des deux documents
remis à l'apprenant (`fixtures/demande/`) : propriétaires, durées de
conservation, flux et dépendances, ci-dessous dans `LECTURE`.

## Ce que les tests rejouent

Les outils d'origine de `fixtures/plateforme/` (intacts) : `valider_fiche.py`
sur la fiche de l'apprenant, puis sur des copies altérées de cette fiche
(propriétaire retiré, conservation retirée) qui DOIVENT être refusées ; et
`barriere.py` sur un dépôt de politique de référence où sont posées les
décisions de l'apprenant, puis sur une copie où ces MÊMES décisions signées
sont déplacées dans le dépôt candidat, qui ne doit rien autoriser.

La date de la barrière est celle de la décision (`DATE_SIMULEE`) : P04 porte
sur l'endroit où vit la décision, pas sur son expiration, et un lab réussi ne
doit pas repasser au rouge parce que le temps a passé.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-contrat-applicatif"
APP = "portail-achats"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PLATEFORME = FIXTURES / "plateforme"
POLITIQUE = FIXTURES / "politique"
GRILLE = json.loads((POLITIQUE / "classification.json").read_text(encoding="utf-8"))
DEMANDEUR = tomllib.loads((POLITIQUE / "demandes.toml").read_text(encoding="utf-8"))[APP][
    "demandeur"
]
CLASSES = ("C1", "C2", "C3", "C4")

# La lecture de référence de fixtures/demande/portail-achats.md et precisions.md.
LECTURE: dict[str, Any] = {
    "id": APP,
    "genere_par_ia": True,
    "utilisateurs": "equipe",
    "criticite_metier": "importante",
    "flux_si": [("erp-achats", "lecture")],
    "dependance": "erp-achats",
    "proprietaire_metier": "m.leroy",
    "proprietaire_technique": "s.moreau",
    "conservation_jours": {"personnelles": 1095, "internes": 30},
}


def _rang(classe: object) -> int:
    return CLASSES.index(classe) + 1 if classe in CLASSES else 0


def _classe_de_la_lecture() -> str:
    c = GRILLE["criteres"]
    score = max(
        max(c["donnees"][cat] for cat in LECTURE["conservation_jours"]),
        max(c["flux_si"][mode] for _, mode in LECTURE["flux_si"]),
        c["utilisateurs"][LECTURE["utilisateurs"]],
        c["criticite_metier"][LECTURE["criticite_metier"]],
    )
    return str(GRILLE["classe_par_score"][str(score)])


ATTENDUE = _classe_de_la_lecture()


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "DATE_SIMULEE")}
    # Les outils sont lancés depuis fixtures/ : aucun __pycache__ n'y est écrit.
    return {**env, "PYTHONDONTWRITEBYTECODE": "1"}


def _valider(fiche: Path) -> dict[str, Any]:
    """`valider_fiche.py` d'origine, avec le dépôt de politique de référence."""
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(PLATEFORME / "valider_fiche.py"), str(fiche),
         "--politique", str(POLITIQUE), "--json"],
        capture_output=True, text=True, timeout=60, check=False, env=_env(),
    )
    try:
        return json.loads(execution.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"valider_fiche.py gave no usable result:\n{execution.stderr[-800:]}",
            fr=f"valider_fiche.py n'a rendu aucun résultat exploitable :\n"
            f"{execution.stderr[-800:]}",
        ))


def _variante(tmp_path: Path, nom: str, fiche: dict[str, Any]) -> dict[str, Any]:
    chemin = tmp_path / f"{nom}.yaml"
    chemin.write_text(yaml.safe_dump(fiche, sort_keys=False, allow_unicode=True),
                      encoding="utf-8")
    return _valider(chemin)


REQUIS = re.compile(r"^\$(?:\.(?P<chemin>[^:]*))?: '(?P<champ>[^']+)' is a required property$")


def _chemin(erreur: str) -> str:
    """Le champ visé par une erreur, quelle que soit la forme du message.

    Un champ absent s'écrit comme jsonschema, `$.donnees[0]: 'finalite' is a
    required property` ; les autres refus commencent par le chemin du champ.
    """
    requis = REQUIS.match(erreur)
    if requis:
        return ".".join(p for p in (requis["chemin"], requis["champ"]) if p)
    return erreur.split(":", 1)[0]


def _erreurs(resultat: dict[str, Any], prefixe: str) -> list[str]:
    return [e for e in resultat.get("erreurs", []) if _chemin(e).startswith(prefixe)]


@pytest.fixture(scope="module")
def validation() -> dict[str, Any]:
    exiger_workdir(WORKDIR, LAB_ID)
    chemin = WORKDIR / "candidat" / "application.yaml"
    assert chemin.is_file(), message(
        en="candidat/application.yaml is missing from challenge/work.",
        fr="candidat/application.yaml est absent de challenge/work.",
    )
    resultat = _valider(chemin)
    assert resultat.get("lisible"), message(
        en=f"valider_fiche.py cannot read candidat/application.yaml: {resultat.get('erreur')}",
        fr=f"valider_fiche.py ne peut pas lire candidat/application.yaml : "
        f"{resultat.get('erreur')}",
    )
    assert isinstance(resultat.get("fiche"), dict), message(
        en="candidat/application.yaml is not a mapping of fields.",
        fr="candidat/application.yaml n'est pas une suite de champs.",
    )
    return resultat


def test_la_fiche_respecte_le_schema_de_la_politique(validation: dict[str, Any]) -> None:
    erreurs = validation["erreurs"]
    assert validation["valide"], message(
        en="The policy schema refuses candidat/application.yaml:\n  - "
        + "\n  - ".join(erreurs),
        fr="Le schéma de la politique refuse candidat/application.yaml :\n  - "
        + "\n  - ".join(erreurs),
    )
    fiche = validation["fiche"]
    for champ in ("id", "genere_par_ia", "utilisateurs", "criticite_metier"):
        assert fiche.get(champ) == LECTURE[champ], message(
            en=f"{champ} is `{fiche.get(champ)}`. Read the request again "
            "(demande/portail-achats.md): what the portal does, not what its requester "
            "concludes.",
            fr=f"{champ} vaut `{fiche.get(champ)}`. Relisez la demande "
            "(demande/portail-achats.md) : ce que fait le portail, pas ce qu'en conclut "
            "sa demandeuse.",
        )
    flux = sorted((f.get("cible"), f.get("mode")) for f in fiche["flux_si"])
    assert flux == LECTURE["flux_si"], message(
        en=f"flux_si declares {flux}. The portal reads the ERP erp-achats, and only "
        "reads it.",
        fr=f"flux_si déclare {flux}. Le portail lit l'ERP erp-achats, et ne fait que "
        "le lire.",
    )
    categories = sorted(d.get("categorie") for d in fiche["donnees"])
    assert categories == sorted(LECTURE["conservation_jours"]), message(
        en=f"donnees lists the categories {categories}. The portal holds supplier "
        "contacts and a local copy of the orders: two data, two categories.",
        fr=f"donnees liste les catégories {categories}. Le portail détient des contacts "
        "fournisseurs et une copie locale des commandes : deux données, deux catégories.",
    )
    assert LECTURE["dependance"] in fiche["dependances_critiques"], message(
        en="dependances_critiques does not name erp-achats, whose outage stops the portal.",
        fr="dependances_critiques ne nomme pas erp-achats, dont l'arrêt arrête le portail.",
    )
    assert validation["classe_calculee"] == ATTENDUE, message(
        en=f"The grid computes {validation['classe_calculee']} from this contract, "
        f"{ATTENDUE} from the request.",
        fr=f"La grille calcule {validation['classe_calculee']} à partir de cette fiche, "
        f"{ATTENDUE} à partir de la demande.",
    )


def test_la_fiche_nomme_ses_proprietaires(
    validation: dict[str, Any], tmp_path: Path
) -> None:
    erreurs = _erreurs(validation, "proprietaire_")
    assert not erreurs, message(
        en="The policy refuses the owners of the contract:\n  - " + "\n  - ".join(erreurs),
        fr="La politique refuse les propriétaires de la fiche :\n  - " + "\n  - ".join(erreurs),
    )
    fiche = validation["fiche"]
    for role in ("proprietaire_metier", "proprietaire_technique"):
        identifiant = (fiche.get(role) or {}).get("identifiant")
        assert identifiant == LECTURE[role], message(
            en=f"{role} is `{identifiant}`. demande/precisions.md says who accepted the role.",
            fr=f"{role} vaut `{identifiant}`. demande/precisions.md dit qui a accepté le rôle.",
        )

    # Le refus se rejoue sur la fiche de l'apprenant elle-même.
    sans = {k: v for k, v in fiche.items() if k != "proprietaire_metier"}
    vide = {**fiche, "proprietaire_metier": {"identifiant": "", "nom": ""}}
    demandeur = {**fiche, "proprietaire_metier": {"identifiant": DEMANDEUR, "nom": "Julie Petit"}}
    for nom, variante in (("sans", sans), ("vide", vide), ("demandeur", demandeur)):
        assert _erreurs(_variante(tmp_path, nom, variante), "proprietaire_metier"), message(
            en=f"The contract without a real business owner ({nom}) is accepted.",
            fr=f"La fiche sans vrai propriétaire métier ({nom}) est acceptée.",
        )


def test_chaque_donnee_a_sa_conservation_et_sa_finalite(
    validation: dict[str, Any], tmp_path: Path
) -> None:
    erreurs = _erreurs(validation, "donnees")
    assert not erreurs, message(
        en="The policy refuses the data of the contract:\n  - " + "\n  - ".join(erreurs),
        fr="La politique refuse les données de la fiche :\n  - " + "\n  - ".join(erreurs),
    )
    fiche = validation["fiche"]
    donnees = fiche.get("donnees")
    assert isinstance(donnees, list) and donnees, message(
        en="donnees is empty: the portal holds data.",
        fr="donnees est vide : le portail détient des données.",
    )
    for donnee in donnees:
        categorie = donnee.get("categorie")
        attendu = LECTURE["conservation_jours"].get(categorie)
        assert donnee.get("conservation_jours") == attendu, message(
            en=f"The {categorie} data is kept {donnee.get('conservation_jours')} days; the "
            f"data protection officer set {attendu} (demande/precisions.md).",
            fr=f"La donnée {categorie} est conservée {donnee.get('conservation_jours')} jours ; "
            f"le délégué à la protection des données a fixé {attendu} "
            "(demande/precisions.md).",
        )

    # Les refus se rejouent sur la fiche de l'apprenant elle-même.
    premiere = dict(donnees[0])

    def sans(champ: str) -> dict[str, Any]:
        return {**fiche, "donnees": [{k: v for k, v in premiere.items() if k != champ},
                                     *donnees[1:]]}

    def avec(champ: str, valeur: object) -> dict[str, Any]:
        return {**fiche, "donnees": [{**premiere, champ: valeur}, *donnees[1:]]}

    variantes = (
        ("conservation absente", sans("conservation_jours")),
        ("conservation nulle", avec("conservation_jours", 0)),
        ("finalite absente", sans("finalite")),
        ("finalite trop courte", avec("finalite", "achats")),
    )
    for nom, variante in variantes:
        assert _erreurs(_variante(tmp_path, nom.replace(" ", "-"), variante), "donnees[0]"), (
            message(
                en=f"A contract whose data has its {nom.replace('finalite', 'purpose')} "
                "is accepted.",
                fr=f"Une fiche dont la donnée a sa {nom.replace('finalite', 'finalité')} "
                "est acceptée.",
            )
        )
    refus = _variante(tmp_path, "finalite-absente", sans("finalite"))
    assert "$.donnees[0]: 'finalite' is a required property" in refus["erreurs"], message(
        en=f"A data item without a purpose is not refused as expected: {refus['erreurs']}",
        fr=f"Une donnée sans finalité n'est pas refusée comme attendu : {refus['erreurs']}",
    )


# --- P04 ---------------------------------------------------------------------

CONSEILS = {
    10: ("no decision in the policy repository authorises the portal",
         "aucune décision du dépôt de politique n'autorise le portail"),
    11: ("the signature does not come from a key of the reference allowed_signers",
         "la signature ne vient pas d'une clé de l'allowed_signers de référence"),
    12: ("the requester decides on her own request",
         "la demandeuse statue sur sa propre demande"),
    13: ("the role does not match what the retained class requires",
         "le rôle ne correspond pas à ce qu'exige la classe retenue"),
    14: ("the decision lasts longer than its class allows",
         "la décision dure plus longtemps que sa classe ne le permet"),
    15: ("candidat/application.yaml is not the file the decision signed",
         "candidat/application.yaml n'est pas le fichier que la décision a signé"),
}


def _decisions_de_l_apprenant() -> list[Path]:
    dossier = WORKDIR / "politique" / "decisions"
    return sorted(dossier.glob(f"{APP}-*.yaml")) if dossier.is_dir() else []


def _date_simulee(decisions: list[Path]) -> str:
    dates = []
    for chemin in decisions:
        try:
            contenu = yaml.safe_load(chemin.read_text(encoding="utf-8"))
            dates.append(date.fromisoformat(str(contenu["date_decision"])))
        except (yaml.YAMLError, OSError, KeyError, TypeError, ValueError):
            continue
    return max(dates).isoformat() if dates else date.today().isoformat()


def _monter(racine: Path, decisions: list[Path], dans_le_candidat: bool) -> Path:
    """Un poste de référence : politique d'origine, candidat de l'apprenant."""
    politique = racine / "politique"
    shutil.copytree(POLITIQUE, politique)
    shutil.copytree(WORKDIR / "candidat", racine / "candidat")
    cible = racine / "candidat" / "decisions" if dans_le_candidat else politique / "decisions"
    cible.mkdir(parents=True, exist_ok=True)
    for chemin in decisions:
        shutil.copy2(chemin, cible / chemin.name)
        signature = chemin.with_name(chemin.name + ".sig")
        if signature.is_file():
            shutil.copy2(signature, cible / signature.name)
    return racine


def _barriere(racine: Path, jour: str) -> dict[str, Any]:
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(PLATEFORME / "barriere.py"), APP,
         "--politique", str(racine / "politique"), "--candidat", str(racine / "candidat"),
         "--json"],
        capture_output=True, text=True, timeout=60, check=False,
        env={**_env(), "DATE_SIMULEE": jour},
    )
    try:
        return json.loads(execution.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"barriere.py gave no usable result:\n{execution.stderr[-800:]}",
            fr=f"barriere.py n'a rendu aucun résultat exploitable :\n{execution.stderr[-800:]}",
        ))


def test_seul_le_depot_de_politique_autorise(tmp_path: Path) -> None:
    exiger_workdir(WORKDIR, LAB_ID)
    decisions = _decisions_de_l_apprenant()
    assert decisions, message(
        en=f"politique/decisions/ holds no {APP}-<date>.yaml: nothing authorises the portal.",
        fr=f"politique/decisions/ ne contient aucun {APP}-<date>.yaml : rien n'autorise "
        "le portail.",
    )
    jour = _date_simulee(decisions)

    verdict = _barriere(_monter(tmp_path / "politique-fait-foi", decisions, False), jour)
    code = verdict.get("code")
    conseil = CONSEILS.get(code, (verdict.get("motif"), verdict.get("motif")))
    assert code == 0, message(
        en=f"The barrier refuses the portal ({code}): {conseil[0]}. {verdict.get('motif')}",
        fr=f"La barrière refuse le portail ({code}) : {conseil[1]}. {verdict.get('motif')}",
    )
    assert _rang(verdict.get("classe_retenue")) >= _rang(ATTENDUE), message(
        en=f"The decision retains {verdict.get('classe_retenue')}, below {ATTENDUE}, the "
        "class the grid gives. Nothing in the file justifies lowering it.",
        fr=f"La décision retient {verdict.get('classe_retenue')}, sous {ATTENDUE}, la classe "
        "que donne la grille. Rien dans le dossier ne justifie de l'abaisser.",
    )

    # Les MÊMES décisions signées, posées dans le dépôt candidat : rien n'est autorisé.
    candidat = _barriere(_monter(tmp_path / "candidat-seul", decisions, True), jour)
    assert candidat.get("code") == 10 and not candidat.get("autorisee"), message(
        en=f"With the decision moved into the candidate repository, the barrier answers "
        f"{candidat.get('code')}: the candidate repository authorises itself.",
        fr=f"Décision déplacée dans le dépôt candidat, la barrière répond "
        f"{candidat.get('code')} : le dépôt candidat s'autorise lui-même.",
    )

    # La classe déclarée abaissée dans la fiche ne change pas la classe retenue :
    # elle fait tomber l'autorisation.
    abaissee = _monter(tmp_path / "classe-abaissee", decisions, False)
    fiche = abaissee / "candidat" / "application.yaml"
    texte = fiche.read_text(encoding="utf-8")
    fiche.write_text(re.sub(r"(?m)^classe_declaree:.*$", "classe_declaree: C1", texte),
                     encoding="utf-8")
    apres = _barriere(abaissee, jour)
    assert not apres.get("autorisee") and apres.get("classe_retenue") != "C1", message(
        en=f"With classe_declaree lowered in the contract, the barrier answers "
        f"{apres.get('code')}, class {apres.get('classe_retenue')}.",
        fr=f"Avec classe_declaree abaissée dans la fiche, la barrière répond "
        f"{apres.get('code')}, classe {apres.get('classe_retenue')}.",
    )
