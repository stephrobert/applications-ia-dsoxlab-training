"""De la demande métier aux critères vérifiables : quatre contrôles, un par point du cadrage.

## Ce que ces tests rejouent eux-mêmes

Aucun contrôle ne croit l'apprenant sur parole. Chacun travaille sur une COPIE
de son projet, dans laquelle il pose lui-même la version de `approvals.py`
qu'il veut éprouver : le module livré (sans implémentation), celui de l'agent
factice des fixtures, ou un mutant de `mutants/`. Il relance alors pytest sur
les tests de l'apprenant, avec le `pytest.ini` des fixtures. L'agent est lui
aussi rejoué depuis les fixtures, avec la proposition des fixtures : modifier
`agent/agent.py` ou `agent/proposal.json` dans le répertoire de travail ne
change rien au verdict.

## Pourquoi un critère doit être rouge AVANT l'implémentation

Un test relié à un critère et qui passe sur le module livré (`assert True`,
`pytest.raises(Exception)` qui attrape le `NotImplementedError`) ne vérifie
rien. P01 exige donc, pour chaque test cité par un critère, un échec sur le
module livré ET une réussite sur l'implémentation de l'agent.

## Pourquoi des mutants

« Chaque critère a un test » ne dit pas que chaque exigence de la demande est
couverte. P02 rejoue les tests cités contre cinq versions cassées de
l'implémentation, une par règle de la demande, dont le refus qu'elle ne
formule qu'implicitement (une commande de zéro ou moins).

L'apprenant ne connaît pas nos numéros : l'appariement se fait par les tests,
pas par les noms. Pour chaque mutant, on relève les exigences dont un test
cité échoue. La règle est alors :

- au moins une (sinon la règle n'est pas couverte) ;
- une seule (sinon les tests d'une exigence vérifient aussi une autre règle) ;
- et deux mutants ne tombent jamais sur la même exigence (sinon une exigence
  regroupe plusieurs règles).

C'est ce qui refuse une spécification à une seule exigence dont un test tue
tout, et aussi cinq exigences qui citent chacune une copie de ce test.

Les mutants vivent ici, à côté des tests, et non dans `fixtures/` : copiés
dans le répertoire de travail, ils diraient à l'apprenant ce qu'il doit
trouver dans la demande. Pour la même raison, l'implémentation de l'agent est
stockée en base64 dans les fixtures : ce n'est pas un secret, seulement un
garde-fou contre la lecture distraite.

## Pourquoi P03 et P04 se partagent les fichiers

P03 porte sur ce que l'agent ne doit jamais toucher (`SPEC.md` et `tests/`),
P04 sur le reste du projet. Un même plan trop large ne coûte donc pas deux
fois la même faute.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-specification-agent"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
MUTANTS = Path(__file__).resolve().parent / "mutants"
AGENT = FIXTURES / "agent" / "agent.py"
PROPOSITION = FIXTURES / "agent" / "proposal.json"
# Stockée en base64 dans les fixtures, décodée ici comme l'agent la décode.
IMPLEMENTATION = base64.b64decode(
    (FIXTURES / "agent" / "proposal" / "approvals.py.b64").read_bytes())
MODULE_LIVRE = (FIXTURES / "approvals.py").read_bytes()
SEUL_MODULE_DEMANDE = "approvals.py"
TENTATIVE_HORS_PLAN = "wire-orders"

# Une exigence de la demande par mutant, dite sans livrer le cas qui la casse.
REGLES = {
    "mutant_r1_limite.py": (
        "the rule for small orders (up to 1,000 EUR, as the request words it)",
        "la règle des petites commandes (jusqu'à 1 000 EUR, dans les mots de la demande)",
    ),
    "mutant_r2_sans_manager.py": (
        "the rule for orders between the two thresholds",
        "la règle des commandes entre les deux seuils",
    ),
    "mutant_r3_sans_finance.py": (
        "the rule for big orders (above 10,000 EUR)",
        "la règle des grosses commandes (au-dessus de 10 000 EUR)",
    ),
    "mutant_r4_devise.py": (
        "the rule on the currency of an order",
        "la règle sur la devise d'une commande",
    ),
    "mutant_r5_montant.py": (
        "a refusal the request only implies (read again what an order always is)",
        "un refus que la demande ne dit qu'implicitement (relisez ce qu'est toujours "
        "une commande)",
    ),
}

GREFFON = '''
import json, os
_etats = {}
def pytest_runtest_logreport(report):
    if report.when == "call":
        _etats[report.nodeid] = report.outcome
    elif report.outcome != "passed":
        _etats[report.nodeid] = "skipped" if report.skipped else "error"
def pytest_sessionfinish(session):
    with open(os.environ["DSOXLAB_ETATS"], "w", encoding="utf-8") as f:
        json.dump(_etats, f)
'''


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


@pytest.fixture(scope="module")
def greffon(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Un greffon pytest qui rend l'état de chaque test, paramètres compris."""
    repertoire = tmp_path_factory.mktemp("greffon")
    (repertoire / "etats_dsoxlab.py").write_text(GREFFON, encoding="utf-8")
    return repertoire


# --- outils -------------------------------------------------------------------


def _ignorer(repertoire: str, noms: list[str]) -> set[str]:
    ignores = {"__pycache__", ".pytest_cache"}
    if Path(repertoire).name == "agent":
        ignores |= {n for n in noms if n.startswith("journal")}
    return {n for n in noms if n in ignores}


def _copie(projet: Path, cible: Path, module: bytes | None) -> Path:
    """Copie du projet, avec la version de `approvals.py` choisie par le test."""
    shutil.copytree(projet, cible, symlinks=True, ignore=_ignorer)
    shutil.copy(FIXTURES / "pytest.ini", cible / "pytest.ini")
    if module is not None:
        (cible / "approvals.py").write_bytes(module)
    return cible


def _pytest(repertoire: Path, greffon: Path) -> tuple[dict[str, str], str]:
    """Lance pytest dans `repertoire`, rend ({node id: état}, fin de la sortie)."""
    fichier_etats = repertoire / ".dsoxlab-etats.json"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env |= {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(greffon),
            "DSOXLAB_ETATS": str(fichier_etats)}
    execution = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "etats_dsoxlab"],
        cwd=repertoire, env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    etats: dict[str, str] = {}
    if fichier_etats.is_file():
        etats = json.loads(fichier_etats.read_text(encoding="utf-8"))
        fichier_etats.unlink()
    return etats, (execution.stdout + execution.stderr)[-1200:]


def _etat(etats: dict[str, str], noeud: str) -> str:
    """L'état d'un test cité ; un test paramétré réussit si tous ses cas réussissent."""
    cas = [e for n, e in etats.items() if n == noeud or n.startswith(noeud + "[")]
    if not cas:
        return "absent"
    if any(e in ("failed", "error") for e in cas):
        return "failed"
    return "passed" if all(e == "passed" for e in cas) else "skipped"


def _specification(projet: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Les exigences et les critères de `SPEC.md`, un élément de liste chacun."""
    chemin = projet / "SPEC.md"
    assert chemin.is_file(), message(
        en="SPEC.md is missing from challenge/work.",
        fr="SPEC.md est absent de challenge/work.",
    )
    texte = chemin.read_text(encoding="utf-8")

    def elements(titre: str) -> list[str]:
        section = texte.split(f"## {titre}", 1)
        if len(section) < 2:
            return []
        items: list[str] = []
        for ligne in section[1].split("\n## ", 1)[0].splitlines():
            if ligne.lstrip().startswith("- "):
                items.append(ligne.strip())
            elif items and ligne.strip():
                items[-1] += " " + ligne.strip()
        return items

    exigences = [
        m.group(1) for item in elements("Requirements")
        if (m := re.match(r"-\s+\**(R\d+)\**\s*:\s*\S", item)) and "..." not in item
    ]
    criteres = []
    for item in elements("Acceptance criteria"):
        m = re.match(r"-\s+(AC-\d+)\s*\[([^\]]*)\]", item)
        if not m:
            continue
        criteres.append({
            "id": m.group(1),
            "exigences": re.findall(r"R\d+", m.group(2)),
            "tests": sorted(set(re.findall(r"`(tests/[^`\s]+\.py::[^`\s]+)`", item))),
        })
    return exigences, criteres


def _empreintes(projet: Path) -> dict[str, str]:
    """Les empreintes de ce que l'agent ne doit jamais toucher, calculées comme lui."""
    fichiers = [projet / "SPEC.md"]
    if (projet / "tests").is_dir():
        fichiers += sorted(
            p for p in (projet / "tests").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    return {
        f.relative_to(projet).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in fichiers if f.is_file()
    }


def _photo(repertoire: Path) -> dict[str, str]:
    return {
        p.relative_to(repertoire).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(repertoire.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def _protege(chemin: str) -> bool:
    return chemin == "SPEC.md" or chemin.startswith("tests/")


def _rejouer_agent(
    projet: Path, tmp: Path
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """Relance l'agent des fixtures sur une copie du projet.

    Rend (journal, photo avant, photo après) : les photos sont prises par le
    test, pas lues dans le journal de l'agent.
    """
    copie = _copie(projet, tmp / "projet-agent", None)
    avant = _photo(copie)
    journal = tmp / "journal-rejoue.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(AGENT), "--project", str(copie), "--proposal", str(PROPOSITION),
         "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=120, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The agent does not start on your project: {execution.stderr.strip()[-600:]}",
        fr=f"L'agent ne démarre pas sur votre projet : {execution.stderr.strip()[-600:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8")), avant, _photo(copie)


# --- P01 ----------------------------------------------------------------------


def test_chaque_critere_est_relie_a_un_test_rouge_puis_vert(
    projet: Path, greffon: Path, tmp_path: Path
) -> None:
    exigences, criteres = _specification(projet)
    assert exigences, message(
        en="SPEC.md lists no requirement: write one item `- **Rn**: ...` per rule of "
        "the request, in the Requirements section.",
        fr="SPEC.md ne liste aucune exigence : écrivez un élément `- **Rn**: ...` par "
        "règle de la demande, dans la section Requirements.",
    )
    assert criteres, message(
        en="SPEC.md has no acceptance criterion (`- AC-n [Rn]: ...` in the Acceptance "
        "criteria section).",
        fr="SPEC.md n'a aucun critère d'acceptation (`- AC-n [Rn]: ...` dans la section "
        "Acceptance criteria).",
    )
    defauts = []
    for critere in criteres:
        if not critere["exigences"]:
            defauts.append(message(
                en=f"{critere['id']} names no requirement between its brackets",
                fr=f"{critere['id']} ne nomme aucune exigence entre ses crochets",
            ))
        inconnues = sorted(set(critere["exigences"]) - set(exigences))
        if inconnues:
            defauts.append(message(
                en=f"{critere['id']} names {inconnues}, which is not a requirement of SPEC.md",
                fr=f"{critere['id']} nomme {inconnues}, qui n'est pas une exigence de SPEC.md",
            ))
        if not critere["tests"]:
            defauts.append(message(
                en=f"{critere['id']} names no test (`tests/test_approvals.py::test_name`)",
                fr=f"{critere['id']} ne nomme aucun test (`tests/test_approvals.py::test_nom`)",
            ))
    couvertes = {r for c in criteres for r in c["exigences"]}
    for exigence in exigences:
        if exigence not in couvertes:
            defauts.append(message(
                en=f"{exigence} has no acceptance criterion: nobody can say whether the code "
                "meets it",
                fr=f"{exigence} n'a aucun critère d'acceptation : personne ne peut dire si le "
                "code la respecte",
            ))
    assert not defauts, "\n  ".join([message(en="SPEC.md:", fr="SPEC.md :"), *defauts])

    sans, sortie_sans = _pytest(_copie(projet, tmp_path / "sans", MODULE_LIVRE), greffon)
    avec, sortie_avec = _pytest(_copie(projet, tmp_path / "avec", IMPLEMENTATION), greffon)
    bilan = []
    for critere in criteres:
        for noeud in critere["tests"]:
            avant, apres = _etat(sans, noeud), _etat(avec, noeud)
            if avant != "failed" or apres != "passed":
                bilan.append(message(
                    en=f"{critere['id']} {noeud}: without the implementation {avant}, "
                    f"with the agent's {apres}",
                    fr=f"{critere['id']} {noeud} : sans l'implémentation {avant}, "
                    f"avec celle de l'agent {apres}",
                ))
    assert not bilan, message(
        en="Each test a criterion cites must fail on approvals.py as delivered (nothing "
        "implemented) and pass on the agent's implementation. A test that passes before "
        "anything is implemented checks nothing.\n  " + "\n  ".join(bilan)
        + f"\n--- pytest, without the implementation:\n{sortie_sans}"
        + f"\n--- pytest, with the agent's implementation:\n{sortie_avec}",
        fr="Chaque test cité par un critère doit échouer sur approvals.py tel que livré "
        "(rien d'implémenté) et réussir sur l'implémentation de l'agent. Un test qui "
        "réussit avant toute implémentation ne vérifie rien.\n  " + "\n  ".join(bilan)
        + f"\n--- pytest, sans l'implémentation :\n{sortie_sans}"
        + f"\n--- pytest, avec l'implémentation de l'agent :\n{sortie_avec}",
    )


# --- P02 ----------------------------------------------------------------------


def test_chaque_exigence_de_la_demande_fait_echouer_un_test(
    projet: Path, greffon: Path, tmp_path: Path
) -> None:
    _, criteres = _specification(projet)
    cites = sorted({n for c in criteres for n in c["tests"]})
    assert cites, message(
        en="No acceptance criterion of SPEC.md cites a test: there is nothing to play "
        "against a broken implementation.",
        fr="Aucun critère d'acceptation de SPEC.md ne cite de test : rien à jouer contre "
        "une implémentation cassée.",
    )
    avec, sortie = _pytest(_copie(projet, tmp_path / "avec", IMPLEMENTATION), greffon)
    valides = [n for n in cites if _etat(avec, n) == "passed"]
    assert valides, message(
        en=f"None of the tests your criteria cite passes on the agent's implementation: "
        f"a test that always fails proves nothing.\n{sortie}",
        fr=f"Aucun des tests cités par vos critères ne réussit sur l'implémentation de "
        f"l'agent : un test qui échoue toujours ne prouve rien.\n{sortie}",
    )

    # Les exigences de chaque test cité : un test cité sous deux exigences
    # compte pour les deux.
    exigences_du_test: dict[str, set[str]] = {}
    for critere in criteres:
        for noeud in critere["tests"]:
            exigences_du_test.setdefault(noeud, set()).update(critere["exigences"])

    survivants, melanges = [], []
    exigence_de: dict[str, str] = {}
    for nom, (en, fr) in REGLES.items():
        mutant = (MUTANTS / nom).read_bytes()
        etats, _ = _pytest(_copie(projet, tmp_path / nom.removesuffix(".py"), mutant), greffon)
        touchees = sorted({r for n in valides if _etat(etats, n) == "failed"
                           for r in exigences_du_test[n]})
        regle = message(en=en, fr=fr)
        if not touchees:
            survivants.append(regle)
        elif len(touchees) > 1:
            melanges.append(f"{regle}: {', '.join(touchees)}")
        else:
            exigence_de[regle] = touchees[0]
    assert not survivants, message(
        en=f"A version of approvals.py that breaks each rule below still passes every "
        f"test your criteria cite ({len(valides)} test(s) checked). Each rule of the "
        f"request needs a criterion whose test fails when it is broken:\n  - "
        + "\n  - ".join(survivants),
        fr=f"Une version d'approvals.py qui casse chaque règle ci-dessous passe encore "
        f"tous les tests cités par vos critères ({len(valides)} test(s) éprouvé(s)). "
        f"Chaque règle de la demande a besoin d'un critère dont le test échoue quand "
        f"elle est cassée :\n  - " + "\n  - ".join(survivants),
    )
    assert not melanges, message(
        en="Breaking one rule of the request makes the tests of several requirements "
        "fail. Each requirement covers one rule, and its tests check that rule only: a "
        "case on the border of two rules belongs to one requirement.\n  - "
        + "\n  - ".join(melanges),
        fr="Casser une seule règle de la demande fait échouer les tests de plusieurs "
        "exigences. Chaque exigence couvre une règle, et ses tests ne vérifient que "
        "celle-là : un cas à la frontière de deux règles appartient à une seule "
        "exigence.\n  - " + "\n  - ".join(melanges),
    )
    regroupees: dict[str, list[str]] = {}
    for regle, exigence in exigence_de.items():
        regroupees.setdefault(exigence, []).append(regle)
    doublons = [f"{r}: {' ; '.join(regles)}" for r, regles in sorted(regroupees.items())
                if len(regles) > 1]
    assert not doublons, message(
        en="One requirement covers several rules of the request. Write one requirement "
        "per rule, each with its own criteria and tests.\n  - " + "\n  - ".join(doublons),
        fr="Une exigence couvre plusieurs règles de la demande. Écrivez une exigence par "
        "règle, chacune avec ses critères et ses tests.\n  - " + "\n  - ".join(doublons),
    )


# --- P03 ----------------------------------------------------------------------


def test_la_specification_et_les_tests_sont_inchanges_par_l_agent(
    projet: Path, tmp_path: Path
) -> None:
    for chemin in ("SPEC.md", "tests/test_approvals.py"):
        assert (projet / chemin).is_file() and (projet / chemin).read_bytes() != (
            FIXTURES / chemin).read_bytes(), message(
            en=f"{chemin} is still the file as delivered: write your specification and your "
            "tests first, then run the agent.",
            fr=f"{chemin} est encore le fichier livré : écrivez d'abord votre spécification "
            "et vos tests, puis lancez l'agent.",
        )

    chemin_journal = projet / "agent" / "journal.json"
    assert chemin_journal.is_file(), message(
        en="agent/journal.json is missing: run the agent (`python3 agent/agent.py`, "
        "without --dry-run) once your specification and tests are written.",
        fr="agent/journal.json est absent : lancez l'agent (`python3 agent/agent.py`, "
        "sans --dry-run) une fois votre spécification et vos tests écrits.",
    )
    try:
        journal = json.loads(chemin_journal.read_text(encoding="utf-8"))
        avant, apres = journal["fingerprints_before"], journal["fingerprints_after"]
        modifications = journal["edits"]
    except (json.JSONDecodeError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"agent/journal.json is not a journal written by the agent ({erreur}): "
            "run the agent again.",
            fr=f"agent/journal.json n'est pas un journal écrit par l'agent ({erreur}) : "
            "relancez l'agent.",
        ))
    assert avant == apres, message(
        en="During its run, the agent changed what it must never change: "
        f"{sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k))}. "
        "Restore these files, then check what your plan allows.",
        fr="Pendant son passage, l'agent a modifié ce qu'il ne doit jamais toucher : "
        f"{sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k))}. "
        "Restaurez ces fichiers, puis vérifiez ce que votre plan autorise.",
    )
    maintenant = _empreintes(projet)
    ecarts = sorted(k for k in set(apres) | set(maintenant) if apres.get(k) != maintenant.get(k))
    assert not ecarts, message(
        en=f"These files differ from the fingerprints the agent recorded: {ecarts}. The "
        "journal must describe the run on your current specification and tests: run "
        "the agent again.",
        fr=f"Ces fichiers diffèrent des empreintes consignées par l'agent : {ecarts}. Le "
        "journal doit décrire le passage sur votre spécification et vos tests actuels : "
        "relancez l'agent.",
    )
    assert not journal.get("dry_run") and all(
        m.get("decision") == "refused" for m in modifications if _protege(str(m.get("file")))
    ), message(
        en="agent/journal.json must record a real run (without --dry-run) in which every "
        "change to SPEC.md or tests/ was refused.",
        fr="agent/journal.json doit consigner un vrai passage (sans --dry-run) où chaque "
        "modification de SPEC.md ou de tests/ a été refusée.",
    )

    rejoue, photo_avant, photo_apres = _rejouer_agent(projet, tmp_path)
    touches = sorted(
        k for k in set(photo_avant) | set(photo_apres)
        if _protege(k) and photo_avant.get(k) != photo_apres.get(k)
    )
    appliquees = [m["id"] for m in rejoue["edits"]
                  if _protege(m["file"]) and m["decision"] != "refused"]
    assert not touches and not appliquees, message(
        en=f"Run again on a copy of your project, the agent changes {touches or appliquees}: "
        "your plan lets it rewrite the specification or the tests it is measured by.",
        fr=f"Rejoué sur une copie de votre projet, l'agent modifie {touches or appliquees} : "
        "votre plan le laisse réécrire la spécification ou les tests qui le mesurent.",
    )


# --- P04 ----------------------------------------------------------------------


def test_l_agent_ne_touche_que_les_fichiers_du_plan(projet: Path, tmp_path: Path) -> None:
    journal, avant, apres = _rejouer_agent(projet, tmp_path)
    autorises = journal["plan"]["allowed_files"]
    modifies = sorted(
        k for k in set(avant) | set(apres)
        if not _protege(k) and avant.get(k) != apres.get(k)
    )
    hors_plan = [f for f in modifies if not any(fnmatch.fnmatchcase(f, p) for p in autorises)]
    assert not hors_plan, message(
        en=f"The agent changed files your plan does not allow: {hors_plan}.",
        fr=f"L'agent a modifié des fichiers que votre plan n'autorise pas : {hors_plan}.",
    )
    implemente = apres.get(SEUL_MODULE_DEMANDE) == hashlib.sha256(IMPLEMENTATION).hexdigest()
    assert implemente, message(
        en=f"The agent could not implement {SEUL_MODULE_DEMANDE}: your plan does not allow "
        f"the file the request asks to change (allowed: {autorises}).",
        fr=f"L'agent n'a pas pu implémenter {SEUL_MODULE_DEMANDE} : votre plan n'autorise pas "
        f"le fichier que la demande fait modifier (autorisés : {autorises}).",
    )
    en_trop = [f for f in modifies if f != SEUL_MODULE_DEMANDE]
    tentative = next(m for m in journal["edits"] if m["id"] == TENTATIVE_HORS_PLAN)
    assert not en_trop and tentative["decision"] == "refused", message(
        en=f"The agent changed {en_trop or tentative['file']}, which the request does not "
        f"concern: the plan allows {autorises}. Its attempt must be refused and recorded.",
        fr=f"L'agent a modifié {en_trop or tentative['file']}, que la demande ne concerne "
        f"pas : le plan autorise {autorises}. Sa tentative doit être refusée et consignée.",
    )
    assert (projet / "orders.py").read_bytes() == (FIXTURES / "orders.py").read_bytes(), message(
        en="orders.py in your project is no longer the module of the orders team: an "
        "earlier run of the agent changed it. Restore it.",
        fr="orders.py, dans votre projet, n'est plus le module de l'équipe des commandes : "
        "un passage précédent de l'agent l'a modifié. Restaurez-le.",
    )
