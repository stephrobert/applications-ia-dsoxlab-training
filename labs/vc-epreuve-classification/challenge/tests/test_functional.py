"""Épreuve du niveau 1 : qualifier le portail-achats, une application non documentée.

## Ce que l'épreuve remobilise

Les outils de deux labs livrés, copiés à l'identique dans `fixtures/` :

- `grille.toml` et `classify.py` de vc-classifier-applications ;
- le dépôt de politique (`politique/`), les outils de la plateforme
  (`plateforme/`) et les deux clés de lab (`cles/`) de vc-contrat-applicatif.

Ce qui est propre à l'épreuve : le code du portail (`candidat/src/`), seule
description de ce qu'il fait, la fiche rédigée par l'agent
(`candidat/application.yaml`), et ce que le code ne peut pas dire
(`accueil/`).

## D'où viennent les valeurs

Tout ce qui fait foi est relu dans `fixtures/`, jamais dans `challenge/work`,
que l'apprenant peut modifier. Ces tests n'ajoutent que la LECTURE de
référence du code et de `accueil/` (`LECTURE` ci-dessous). La classe attendue
se CALCULE à partir d'elle et de la grille : elle n'est écrite nulle part.

Lecture du code : `erp.py` lit commandes et fournisseurs dans erp-achats
(GET seulement), `budgets.py` lit les lignes budgétaires dans budgets-finance
(GET seulement, et le portail continue sans elles), `stockage.py` garde une
copie des commandes sans contact et les contacts fournisseurs (nom, courriel,
téléphone), `views.py` réserve l'accès au groupe achats. Les budgets ne sont
pas conservés : la ligne « copie des lignes budgétaires » du registre ne
s'applique pas.

## Cadrage

P01 (critique) : données personnelles et flux de lecture remontés, classe C3
retenue. Tests C1 et C2. P02 (critique) : sans fiche de décision signée, le
déploiement reste bloqué. Test C5. C3 et C4 portent le contrat et la fiche de
décision de la mission.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-epreuve-classification"
APP = "portail-achats"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PLATEFORME = FIXTURES / "plateforme"
POLITIQUE = FIXTURES / "politique"
GRILLE = tomllib.loads((FIXTURES / "grille.toml").read_text(encoding="utf-8"))
DEMANDEUR = tomllib.loads((POLITIQUE / "demandes.toml").read_text(encoding="utf-8"))[APP][
    "demandeur"
]
CLASSE_DEMANDEE = tomllib.loads(
    (FIXTURES / "classification.toml").read_text(encoding="utf-8")
)["applications"][APP]["classe_demandee"]
CLASSES = ("C1", "C2", "C3", "C4")

# La lecture de référence du code (candidat/src/) et de accueil/.
LECTURE: dict[str, Any] = {
    "criteres": {
        "donnees": "personnelles",
        "flux_si": "lecture",
        "utilisateurs": "equipe",
        "criticite_metier": "importante",
    },
    "flux_si": [("budgets-finance", "lecture"), ("erp-achats", "lecture")],
    "conservation_jours": {"internes": 30, "personnelles": 1095},
    "dependance": "erp-achats",
    "proprietaire_metier": "m.leroy",
    "proprietaire_technique": "s.moreau",
}


def _rang(classe: object) -> int:
    return CLASSES.index(classe) + 1 if classe in CLASSES else 0


def _classe(criteres: dict[str, str]) -> str:
    score = max(GRILLE["criteres"][c][v] for c, v in criteres.items())
    return str(GRILLE["classe_par_score"][str(score)])


ATTENDUE = _classe(LECTURE["criteres"])


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "DATE_SIMULEE")}
    # Les outils sont lancés depuis fixtures/ : aucun __pycache__ n'y est écrit.
    return {**env, "PYTHONDONTWRITEBYTECODE": "1"}


def _json(execution: subprocess.CompletedProcess[str], outil: str) -> dict[str, Any]:
    try:
        return json.loads(execution.stdout)
    except json.JSONDecodeError:
        pytest.fail(message(
            en=f"{outil} gave no usable result:\n{execution.stderr[-800:]}",
            fr=f"{outil} n'a rendu aucun résultat exploitable :\n{execution.stderr[-800:]}",
        ))


# --- C1 : la classification -------------------------------------------------


def test_c1_la_classe_retenue_vient_du_critere_le_plus_eleve() -> None:
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
    app = (contenu.get("applications") or {}).get(APP)
    assert isinstance(app, dict), message(
        en=f"classification.toml has no [applications.{APP}] table.",
        fr=f"classification.toml n'a pas de table [applications.{APP}].",
    )
    criteres = app.get("criteres") if isinstance(app.get("criteres"), dict) else {}
    for critere, attendu in LECTURE["criteres"].items():
        assert criteres.get(critere) == attendu, message(
            en=f"Criterion {critere} is `{criteres.get(critere)}`. Read what the code "
            "does, and what accueil/ says the code cannot.",
            fr=f"Le critère {critere} vaut `{criteres.get(critere)}`. Lisez ce que fait "
            "le code, et ce que accueil/ dit que le code ne peut pas dire.",
        )
    assert app.get("classe_demandee") == CLASSE_DEMANDEE, message(
        en=f"classe_demandee is what the requester asked for ({CLASSE_DEMANDEE}); "
        "it is not yours to change.",
        fr=f"classe_demandee est ce que la demandeuse a demandé ({CLASSE_DEMANDEE}) ; "
        "ce n'est pas à vous de la changer.",
    )
    attendue = "rejetee" if _rang(CLASSE_DEMANDEE) < _rang(ATTENDUE) else "acceptee"
    assert app.get("decision_demande") == attendue, message(
        en=f"The request for {CLASSE_DEMANDEE} is `{app.get('decision_demande')}`.",
        fr=f"La demande de {CLASSE_DEMANDEE} est `{app.get('decision_demande')}`.",
    )
    assert _rang(app.get("classe_retenue")) >= _rang(ATTENDUE), message(
        en=f"The portal is retained in `{app.get('classe_retenue')}`, below what the "
        "grid gives.",
        fr=f"Le portail est retenu en `{app.get('classe_retenue')}`, sous ce que donne "
        "la grille.",
    )

    # Le script de calcul d'origine, rejoué sur le fichier de l'apprenant.
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(FIXTURES / "classify.py"), "--json",
         "--grille", str(FIXTURES / "grille.toml"), "--classification", str(chemin)],
        capture_output=True, text=True, timeout=60, check=False, env=_env(),
    )
    verdicts = {r["application"]: r for r in _json(execution, "classify.py")["applications"]}
    verdict = verdicts.get(APP, {})
    assert verdict.get("request_ok") and verdict.get("class_ok") and verdict.get(
        "policy_ok"
    ), message(
        en=f"classify.py does not accept the classification: {verdict.get('problems')}",
        fr=f"classify.py n'accepte pas la classification : {verdict.get('problems')}",
    )


# --- C2 et C3 : la fiche applicative ------------------------------------------


def _valider(fiche: Path) -> dict[str, Any]:
    """`valider_fiche.py` d'origine, avec le dépôt de politique de référence."""
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(PLATEFORME / "valider_fiche.py"), str(fiche),
         "--politique", str(POLITIQUE), "--json"],
        capture_output=True, text=True, timeout=60, check=False, env=_env(),
    )
    return _json(execution, "valider_fiche.py")


def _variante(tmp_path: Path, nom: str, fiche: dict[str, Any]) -> dict[str, Any]:
    chemin = tmp_path / f"{nom}.yaml"
    chemin.write_text(yaml.safe_dump(fiche, sort_keys=False, allow_unicode=True),
                      encoding="utf-8")
    return _valider(chemin)


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


def _liste(fiche: dict[str, Any], champ: str) -> list[dict[str, Any]]:
    valeur = fiche.get(champ)
    return [v for v in valeur if isinstance(v, dict)] if isinstance(valeur, list) else []


def test_c2_la_fiche_declare_ce_que_fait_le_code(validation: dict[str, Any]) -> None:
    fiche = validation["fiche"]
    flux = sorted((f.get("cible"), f.get("mode")) for f in _liste(fiche, "flux_si"))
    assert flux == LECTURE["flux_si"], message(
        en=f"flux_si declares {flux}. Every system of the company the code calls is a "
        "flow, with the mode the code uses.",
        fr=f"flux_si déclare {flux}. Chaque système de l'entreprise que le code appelle "
        "est un flux, avec le mode qu'emploie le code.",
    )
    categories = sorted(str(d.get("categorie")) for d in _liste(fiche, "donnees"))
    assert categories == sorted(LECTURE["conservation_jours"]), message(
        en=f"donnees lists the categories {categories}. Declare each data item the "
        "portal keeps, and only those.",
        fr=f"donnees liste les catégories {categories}. Déclarez chaque donnée que le "
        "portail conserve, et seulement celles-là.",
    )
    for champ in ("utilisateurs", "criticite_metier"):
        attendu = LECTURE["criteres"][champ]
        assert fiche.get(champ) == attendu, message(
            en=f"{champ} is `{fiche.get(champ)}`.",
            fr=f"{champ} vaut `{fiche.get(champ)}`.",
        )
    assert validation["classe_calculee"] == ATTENDUE, message(
        en=f"The grid computes {validation['classe_calculee']} from this contract.",
        fr=f"La grille calcule {validation['classe_calculee']} à partir de cette fiche.",
    )
    assert _rang(fiche.get("classe_declaree")) >= _rang(ATTENDUE), message(
        en=f"classe_declaree is `{fiche.get('classe_declaree')}`, below what the grid "
        "computes from this contract.",
        fr=f"classe_declaree vaut `{fiche.get('classe_declaree')}`, sous ce que la "
        "grille calcule à partir de cette fiche.",
    )


def test_c3_la_fiche_passe_la_politique(
    validation: dict[str, Any], tmp_path: Path
) -> None:
    erreurs = validation["erreurs"]
    assert validation["valide"], message(
        en="The policy refuses candidat/application.yaml:\n  - " + "\n  - ".join(erreurs),
        fr="La politique refuse candidat/application.yaml :\n  - " + "\n  - ".join(erreurs),
    )
    fiche = validation["fiche"]
    for role in ("proprietaire_metier", "proprietaire_technique"):
        identifiant = (fiche.get(role) or {}).get("identifiant")
        assert identifiant == LECTURE[role], message(
            en=f"{role} is `{identifiant}`. accueil/precisions.md says who accepted the role.",
            fr=f"{role} vaut `{identifiant}`. accueil/precisions.md dit qui a accepté le rôle.",
        )
    assert LECTURE["dependance"] in fiche["dependances_critiques"], message(
        en="dependances_critiques does not name the service whose outage stops the portal.",
        fr="dependances_critiques ne nomme pas le service dont l'arrêt arrête le portail.",
    )
    donnees = fiche["donnees"]
    for donnee in donnees:
        categorie = donnee.get("categorie")
        attendu = LECTURE["conservation_jours"].get(categorie)
        assert donnee.get("conservation_jours") == attendu, message(
            en=f"The {categorie} data is kept {donnee.get('conservation_jours')} days; "
            "the register of the data protection officer says otherwise.",
            fr=f"La donnée {categorie} est conservée {donnee.get('conservation_jours')} "
            "jours ; le registre du délégué à la protection des données dit autre chose.",
        )

    # Les refus se rejouent sur la fiche de l'apprenant elle-même.
    premiere = {k: v for k, v in donnees[0].items() if k != "finalite"}
    sans_finalite = {**fiche, "donnees": [premiere, *donnees[1:]]}
    refus = _variante(tmp_path, "sans-finalite", sans_finalite)
    assert "$.donnees[0]: 'finalite' is a required property" in refus["erreurs"], message(
        en=f"A data item without a purpose is not refused: {refus['erreurs']}",
        fr=f"Une donnée sans finalité n'est pas refusée : {refus['erreurs']}",
    )
    demandeuse = {**fiche, "proprietaire_metier": {"identifiant": DEMANDEUR, "nom": "Julie Petit"}}
    refus = _variante(tmp_path, "demandeuse-proprietaire", demandeuse)
    assert any(e.startswith("proprietaire_metier") for e in refus["erreurs"]), message(
        en="The contract is accepted with the requester as business owner.",
        fr="La fiche est acceptée avec la demandeuse comme propriétaire métier.",
    )


# --- C4 et C5 : la fiche de décision et la barrière ---------------------------

CHAMPS_DECISION = (
    "id", "application", "fiche_sha256", "classe_retenue", "decision",
    "demandeur", "decideur", "date_decision", "expire_le",
)


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


def _monter(
    racine: Path, decisions: list[Path], dans_le_candidat: bool, signees: bool = True
) -> Path:
    """Un poste de référence : politique d'origine, candidat de l'apprenant."""
    politique = racine / "politique"
    shutil.copytree(POLITIQUE, politique)
    shutil.copytree(WORKDIR / "candidat", racine / "candidat")
    cible = racine / "candidat" / "decisions" if dans_le_candidat else politique / "decisions"
    cible.mkdir(parents=True, exist_ok=True)
    for chemin in decisions:
        shutil.copy2(chemin, cible / chemin.name)
        signature = chemin.with_name(chemin.name + ".sig")
        if signees and signature.is_file():
            shutil.copy2(signature, cible / signature.name)
    return racine


def _decision_abaissee(racine: Path, classe: str, jour: str) -> None:
    """Une décision qui retient `classe`, signée par la décideuse habilitée.

    Tout y est en règle (empreinte de la fiche, signataire d'allowed_signers,
    rôle, durée), sauf la classe : seule elle peut faire refuser.
    """
    debut = date.fromisoformat(jour)
    empreinte = hashlib.sha256((racine / "candidat" / "application.yaml").read_bytes())
    decision = racine / "politique" / "decisions" / f"{APP}-{jour}-abaissee.yaml"
    decision.write_text(yaml.safe_dump({
        "id": f"{APP}-{jour}-abaissee",
        "application": APP,
        "fiche_sha256": empreinte.hexdigest(),
        "classe_retenue": classe,
        "decision": "accepte",
        "risques_acceptes": [],
        "conditions": [],
        "demandeur": DEMANDEUR,
        "decideur": {"identifiant": "m.leroy", "role": "responsable_service"},
        "date_decision": jour,
        "expire_le": (debut + timedelta(days=60)).isoformat(),
    }, sort_keys=False), encoding="utf-8")
    cle = racine / "cle-approbatrice"
    shutil.copy2(FIXTURES / "cles" / "approbateur", cle)
    cle.chmod(0o600)
    subprocess.run(  # noqa: S603
        ["ssh-keygen", "-q", "-Y", "sign", "-f", str(cle),  # noqa: S607
         "-n", "decision-applicative", str(decision)],
        capture_output=True, check=True, timeout=30,
    )


def _barriere(racine: Path, jour: str) -> dict[str, Any]:
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(PLATEFORME / "barriere.py"), APP,
         "--politique", str(racine / "politique"), "--candidat", str(racine / "candidat"),
         "--json"],
        capture_output=True, text=True, timeout=60, check=False,
        env={**_env(), "DATE_SIMULEE": jour},
    )
    return _json(execution, "barriere.py")


def _exiger_decisions() -> list[Path]:
    exiger_workdir(WORKDIR, LAB_ID)
    decisions = _decisions_de_l_apprenant()
    assert decisions, message(
        en=f"politique/decisions/ holds no {APP}-<date>.yaml.",
        fr=f"politique/decisions/ ne contient aucun {APP}-<date>.yaml.",
    )
    return decisions


def test_c4_une_decision_signee_de_la_politique_autorise(tmp_path: Path) -> None:
    decisions = _exiger_decisions()
    jour = _date_simulee(decisions)
    verdict = _barriere(_monter(tmp_path / "politique-fait-foi", decisions, False), jour)
    assert verdict.get("code") == 0, message(
        en=f"The barrier refuses the portal ({verdict.get('code')}): {verdict.get('motif')}",
        fr=f"La barrière refuse le portail ({verdict.get('code')}) : {verdict.get('motif')}",
    )
    assert _rang(verdict.get("classe_retenue")) >= _rang(ATTENDUE), message(
        en=f"The decision retains {verdict.get('classe_retenue')}, below what the grid gives.",
        fr=f"La décision retient {verdict.get('classe_retenue')}, sous ce que donne la grille.",
    )


def test_c5_sans_decision_signee_de_la_politique_le_deploiement_reste_bloque(
    tmp_path: Path,
) -> None:
    decisions = _exiger_decisions()
    empreinte = hashlib.sha256((WORKDIR / "candidat" / "application.yaml").read_bytes())
    for chemin in decisions:
        try:
            contenu = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        except yaml.YAMLError as erreur:
            pytest.fail(message(
                en=f"{chemin.name} is not valid YAML: {erreur}",
                fr=f"{chemin.name} n'est pas un YAML valide : {erreur}",
            ))
        manquants = [c for c in CHAMPS_DECISION
                     if not isinstance(contenu, dict) or c not in contenu]
        assert not manquants, message(
            en=f"{chemin.name} misses {manquants} (politique/decisions/README.md).",
            fr=f"{chemin.name} n'a pas {manquants} (politique/decisions/README.md).",
        )
        assert contenu["fiche_sha256"] == empreinte.hexdigest(), message(
            en=f"{chemin.name} does not carry the sha256 of candidat/application.yaml.",
            fr=f"{chemin.name} ne porte pas le sha256 de candidat/application.yaml.",
        )
        assert contenu["demandeur"] == DEMANDEUR, message(
            en=f"{chemin.name} names `{contenu['demandeur']}` as requester.",
            fr=f"{chemin.name} nomme `{contenu['demandeur']}` comme demandeur.",
        )
    jour = _date_simulee(decisions)

    # Les MÊMES décisions, sans leur signature : la barrière bloque sur la signature.
    sans = _barriere(_monter(tmp_path / "sans-signature", decisions, False, signees=False), jour)
    assert sans.get("code") == 11 and not sans.get("autorisee"), message(
        en=f"With the decisions unsigned, the barrier answers {sans.get('code')}: "
        f"{sans.get('motif')}",
        fr=f"Décisions sans signature, la barrière répond {sans.get('code')} : "
        f"{sans.get('motif')}",
    )
    # Les MÊMES décisions signées, posées dans le dépôt candidat : rien n'est autorisé.
    ailleurs = _barriere(_monter(tmp_path / "candidat-seul", decisions, True), jour)
    assert ailleurs.get("code") == 10 and not ailleurs.get("autorisee"), message(
        en=f"With the decisions moved into the candidate repository, the barrier answers "
        f"{ailleurs.get('code')}: the candidate repository authorises itself.",
        fr=f"Décisions déplacées dans le dépôt candidat, la barrière répond "
        f"{ailleurs.get('code')} : le dépôt candidat s'autorise lui-même.",
    )
    # La classe déclarée abaissée dans la fiche après la décision : la fiche n'est
    # plus celle qui a été signée, rien n'est autorisé.
    abaissee = _monter(tmp_path / "classe-abaissee", decisions, False)
    fiche = abaissee / "candidat" / "application.yaml"
    fiche.write_text(
        re.sub(r"(?m)^classe_declaree:.*$", "classe_declaree: C1",
               fiche.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    apres = _barriere(abaissee, jour)
    assert apres.get("code") != 0 and not apres.get("autorisee"), message(
        en=f"With classe_declaree lowered after the decision, the barrier answers "
        f"{apres.get('code')}.",
        fr=f"Avec classe_declaree abaissée après la décision, la barrière répond "
        f"{apres.get('code')}.",
    )
    # Une décision en règle, signée par la décideuse habilitée, qui retient une
    # classe SOUS celle que donne la grille : la barrière la refuse (D29).
    if _rang(ATTENDUE) > 1:
        dessous = CLASSES[_rang(ATTENDUE) - 2]
        sous_la_grille = tmp_path / "decision-sous-la-grille"
        shutil.copytree(POLITIQUE, sous_la_grille / "politique")
        shutil.copytree(WORKDIR / "candidat", sous_la_grille / "candidat")
        _decision_abaissee(sous_la_grille, dessous, jour)
        sous = _barriere(sous_la_grille, jour)
        assert sous.get("code") == 16 and not sous.get("autorisee"), message(
            en=f"A signed decision retaining {dessous}, below {ATTENDUE}, gets the answer "
            f"{sous.get('code')}: {sous.get('motif')}",
            fr=f"Une décision signée qui retient {dessous}, sous {ATTENDUE}, reçoit la "
            f"réponse {sous.get('code')} : {sous.get('motif')}",
        )
