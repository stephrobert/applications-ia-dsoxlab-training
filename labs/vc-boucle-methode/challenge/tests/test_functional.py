"""La boucle de méthode : trois contrôles, un par point du cadrage.

## Ce que ces tests rejouent eux-mêmes

Aucun contrôle ne croit l'apprenant sur parole. Chacun relance pytest sur le
projet de `challenge/work` (dans un sous-processus, avec le `pytest.ini` du
projet), importe le module pour en mesurer le comportement, ou relit les
fichiers que l'apprenant a écrits.

## Pourquoi « la suite est verte » ne suffit pas

La seconde proposition de l'agent garde la suite verte : elle pose un `skip`
sur le test qu'elle casse. Un contrôle qui se contenterait du code de retour
de pytest la laisserait passer. P02 exige donc que CHAQUE test d'origine soit
exécuté ET réussi, et mesure le comportement lui-même sur des montants que le
calcul en flottant arrondit mal.

## Pourquoi le test du critère doit échouer quand R3 est cassée

Un critère relié à `assert True` est relié à un test qui existe et passe, et
ne vérifie rien. P03 rejoue donc le test cité contre deux mutants du module de
l'apprenant, où `initial_status` rend toujours le même statut : il doit en
faire échouer au moins un.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-boucle-methode"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

# Les tests de la suite d'origine, et ceux qu'apporte la proposition saine.
TESTS_ORIGINE = (
    "tests/test_orders.py::test_total_sums_lines",
    "tests/test_orders.py::test_total_rounded_to_cent",
    "tests/test_orders.py::test_zero_quantity_refused",
)
TESTS_PROPOSITION_SAINE = (
    "tests/test_orders.py::test_above_threshold_needs_approval",
    "tests/test_orders.py::test_at_threshold_approved",
)
TEST_NEUTRALISE = "test_total_rounded_to_cent"
MUTANTS_R3 = ("approved", "pending_approval")
REFUS = {"refused", "refuse", "rejected", "reject", "refusé", "refusée", "rejeté", "rejetée"}


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _pytest(repertoire: Path, *args: str) -> tuple[int, dict[str, str], str]:
    """Lance pytest dans `repertoire` et rend (code, {node id: état}, sortie).

    L'état vient du rapport JUnit, pas du code de retour : un test ignoré
    (`skip`) rend 0 comme un test réussi, et c'est précisément le piège.
    """
    rapport = repertoire / ".dsoxlab-junit.xml"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--junitxml={rapport}", *args],
        cwd=repertoire, env=env, capture_output=True, text=True, timeout=120,
        check=False,
    )
    etats: dict[str, str] = {}
    if rapport.is_file():
        # Le rapport vient de notre propre pytest, pas d'une source extérieure.
        for cas in ET.parse(rapport).getroot().iter("testcase"):  # noqa: S314
            fichier = cas.get("classname", "").replace(".", "/") + ".py"
            etat = "passed"
            for enfant in cas:
                if enfant.tag in ("failure", "error", "skipped"):
                    etat = enfant.tag
            etats[f"{fichier}::{cas.get('name')}"] = etat
        rapport.unlink()
    sortie = (execution.stdout + execution.stderr)[-1500:]
    return execution.returncode, etats, sortie


def _module(repertoire: Path) -> ModuleType:
    """Le module `orders.py` du projet, chargé à neuf."""
    chemin = repertoire / "orders.py"
    spec = importlib.util.spec_from_file_location(f"orders_{id(chemin)}", chemin)
    assert spec and spec.loader, message(
        en=f"{chemin} cannot be loaded.", fr=f"{chemin} ne peut pas être chargé."
    )
    module = importlib.util.module_from_spec(spec)
    # `dataclass` relit le module dans sys.modules : il doit y être inscrit.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _criteres(spec_md: str) -> list[str]:
    """Les critères de la section « Acceptance criteria », un par élément de liste."""
    section = spec_md.split("## Acceptance criteria", 1)
    if len(section) < 2:
        return []
    corps = section[1].split("\n## ", 1)[0]
    criteres: list[str] = []
    for ligne in corps.splitlines():
        if ligne.lstrip().startswith("- "):
            criteres.append(ligne.strip())
        elif criteres and ligne.strip():
            criteres[-1] += " " + ligne.strip()
    return criteres


def test_la_proposition_saine_est_appliquee_et_la_suite_passe(projet: Path) -> None:
    assert (projet / "orders.py").is_file(), message(
        en="orders.py is missing from challenge/work.",
        fr="orders.py est absent de challenge/work.",
    )
    module = _module(projet)
    assert hasattr(module, "initial_status"), message(
        en="orders.py has no initial_status function: the proposal that "
        "implements R3 is not applied.",
        fr="orders.py n'a pas de fonction initial_status : la proposition qui "
        "implémente R3 n'est pas appliquée.",
    )
    ligne = module.Line
    cas = {
        Decimal("1000.00"): "approved",
        Decimal("1000.01"): "pending_approval",
        Decimal("200.00"): "approved",
    }
    for prix, attendu in cas.items():
        obtenu = module.initial_status([ligne("laptop", 5, prix)])
        assert obtenu == attendu, message(
            en=f"An order of 5 x {prix} EUR must start in `{attendu}` (R3), "
            f"initial_status returns `{obtenu}`.",
            fr=f"Une commande de 5 x {prix} EUR doit démarrer en `{attendu}` "
            f"(R3), initial_status rend `{obtenu}`.",
        )

    code, etats, sortie = _pytest(projet)
    for test in TESTS_PROPOSITION_SAINE:
        assert etats.get(test) == "passed", message(
            en=f"{test} must exist and pass: it comes with the change you apply. "
            f"State: {etats.get(test, 'absent')}.\n{sortie}",
            fr=f"{test} doit exister et réussir : il accompagne le changement "
            f"appliqué. État : {etats.get(test, 'absent')}.\n{sortie}",
        )
    echecs = sorted(t for t, e in etats.items() if e in ("failure", "error"))
    assert code == 0 and not echecs, message(
        en=f"The project's suite must pass (pytest in challenge/work). "
        f"Failing: {echecs or 'see output'}.\n{sortie}",
        fr=f"La suite du projet doit passer (pytest dans challenge/work). "
        f"En échec : {echecs or 'voir la sortie'}.\n{sortie}",
    )


def test_la_proposition_qui_neutralise_un_test_est_refusee(projet: Path) -> None:
    _, etats, sortie = _pytest(projet)
    for test in TESTS_ORIGINE:
        etat = etats.get(test, "absent")
        assert etat == "passed", message(
            en=f"{test} must still be run and pass. State: {etat}. A test that "
            f"is deleted, renamed or skipped no longer proves anything.\n{sortie}",
            fr=f"{test} doit toujours être exécuté et réussir. État : {etat}. "
            f"Un test supprimé, renommé ou ignoré ne prouve plus rien.\n{sortie}",
        )

    module = _module(projet)
    ligne = module.Line
    for lignes, attendu in (
        ([ligne("stamps", 1, Decimal("1.005"))], Decimal("1.01")),
        ([ligne("pens", 3, Decimal("0.10"))], Decimal("0.30")),
        ([ligne("cable", 7, Decimal("2.675"))], Decimal("18.73")),
    ):
        total = module.order_total(lignes)
        assert isinstance(total, Decimal) and total == attendu, message(
            en=f"order_total must stay exact (R1): expected Decimal('{attendu}'), "
            f"got {total!r}.",
            fr=f"order_total doit rester exact (R1) : attendu Decimal('{attendu}'), "
            f"obtenu {total!r}.",
        )

    journal = projet / "decisions.yaml"
    assert journal.is_file(), message(
        en="decisions.yaml is missing from challenge/work.",
        fr="decisions.yaml est absent de challenge/work.",
    )
    try:
        contenu = yaml.safe_load(journal.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as erreur:
        pytest.fail(message(
            en=f"decisions.yaml is not valid YAML: {erreur}",
            fr=f"decisions.yaml n'est pas un YAML valide : {erreur}",
        ))
    decisions = contenu.get("decisions") if isinstance(contenu, dict) else None
    entrees = [
        d for d in (decisions or [])
        if isinstance(d, dict) and "proposal-2" in str(d.get("proposal", ""))
    ]
    assert entrees, message(
        en="decisions.yaml has no entry for proposal-2.patch.",
        fr="decisions.yaml n'a aucune entrée pour proposal-2.patch.",
    )
    entree = entrees[-1]
    assert str(entree.get("decision", "")).strip().lower() in REFUS, message(
        en=f"The decision recorded for proposal-2.patch is "
        f"`{entree.get('decision')}`: the log must say it is refused.",
        fr=f"La décision consignée pour proposal-2.patch est "
        f"`{entree.get('decision')}` : le journal doit dire qu'elle est refusée.",
    )
    raison = str(entree.get("reason", ""))
    assert TEST_NEUTRALISE in raison or re.search(r"\bskip", raison, re.I), message(
        en="The reason must say precisely what is refused in proposal-2.patch, "
        "precisely enough for its author to find it: which test it touches, and how.",
        fr="La raison doit dire précisément ce qui est refusé dans "
        "proposal-2.patch, assez pour que son auteur le retrouve : quel test "
        "elle touche, et comment.",
    )


def test_la_specification_porte_un_critere_verifiable(projet: Path, tmp_path: Path) -> None:
    spec = projet / "SPEC.md"
    assert spec.is_file(), message(
        en="SPEC.md is missing from challenge/work.",
        fr="SPEC.md est absent de challenge/work.",
    )
    criteres = [c for c in _criteres(spec.read_text(encoding="utf-8")) if "[R3]" in c]
    assert criteres, message(
        en="SPEC.md has no acceptance criterion for R3 (an item `- AC-n [R3]: ...` "
        "in the Acceptance criteria section).",
        fr="SPEC.md n'a aucun critère d'acceptation pour R3 (un élément "
        "`- AC-n [R3]: ...` dans la section Acceptance criteria).",
    )
    noeuds = sorted({n for c in criteres for n in re.findall(r"`(tests/[^`\s]+\.py::\w+)`", c)})
    assert noeuds, message(
        en="The R3 criterion names no test: write its pytest node id between "
        "backticks, as the other criteria do.",
        fr="Le critère de R3 ne nomme aucun test : écrivez son identifiant pytest "
        "entre accents graves, comme les autres critères.",
    )

    # Deux mutants de R3 : le module ACTUEL de l'apprenant, dont initial_status
    # est redéfini pour rendre toujours le même statut. Un test qui vérifie R3
    # en tue au moins un ; `assert True` n'en tue aucun.
    source = (projet / "orders.py").read_text(encoding="utf-8")
    mutants = []
    for statut in MUTANTS_R3:
        mutant = tmp_path / f"mutant-{statut}"
        mutant.mkdir()
        (mutant / "orders.py").write_text(
            source + f"\n\ndef initial_status(lines):\n    return {statut!r}\n",
            encoding="utf-8",
        )
        shutil.copy(FIXTURES / "pytest.ini", mutant / "pytest.ini")
        if (projet / "tests").is_dir():
            shutil.copytree(projet / "tests", mutant / "tests")
        mutants.append(mutant)

    verifiables = []
    bilan = []
    for noeud in noeuds:
        _, maintenant, _ = _pytest(projet, noeud)
        etat_maintenant = maintenant.get(noeud, "absent")
        etats_mutants = [_pytest(m, noeud)[1].get(noeud, "absent") for m in mutants]
        bilan.append(f"{noeud}: now={etat_maintenant}, broken R3={etats_mutants}")
        if etat_maintenant == "passed" and any(e in ("failure", "error") for e in etats_mutants):
            verifiables.append(noeud)
    assert verifiables, message(
        en="The R3 criterion must cite a test that exists, passes on the current "
        "code and fails when R3 is broken (initial_status always returning the "
        "same status). Otherwise it checks nothing about R3.\n  " + "\n  ".join(bilan),
        fr="Le critère de R3 doit citer un test qui existe, réussit sur le code "
        "actuel et échoue quand R3 est cassée (initial_status qui rend toujours "
        "le même statut). Sinon il ne vérifie rien de R3.\n  " + "\n  ".join(bilan),
    )
