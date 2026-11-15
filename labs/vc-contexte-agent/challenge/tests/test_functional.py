"""Le contexte d'un agent : quatre contrôles, un par point du cadrage (P01 à P04).

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance l'agent factice DES FIXTURES sur une COPIE du
répertoire de travail, avec la tâche et le budget des fixtures : modifier
`agent/agent.py`, `agent/task.json` ou `agent/budget.json` dans le répertoire
de travail ne change rien au verdict. Le budget de lignes vit dans UN seul
fichier, `fixtures/agent/budget.json`, lu par l'agent et par ces tests.

## Points critiques

Le cadrage marque P01, P02 et P03 critiques, P04 non critique. dsoxlab ne
pondère pas les tests : les quatre comptent autant dans la note. La
distinction vit dans le cadrage et dans l'ordre des critères, pas dans le
barème.

## Ce que le journal de l'apprenant prouve, et ce qu'il ne prouve pas

`agent/journal.json` dit que l'apprenant a lancé l'agent sur sa configuration
finale. P01 le compare à la rejoue, fichier par fichier : un journal écrit à
la main ou périmé ne correspond pas. Aucun point n'est accordé sur la foi du
journal : c'est la rejoue qui note.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-contexte-agent"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
AGENT = FIXTURES / "agent" / "agent.py"
TACHE = FIXTURES / "agent" / "task.json"
BUDGET = FIXTURES / "agent" / "budget.json"
GROS_DOCUMENT = "docs/erp-history.md"
# Une tâche hors du dossier ciblé : la règle des montants ne doit pas s'y charger.
SONDE_HORS_PERIMETRE = {"id": "probe-reports", "action": "read", "file": "src/rapports/monthly.py"}
CAUSES_CIBLEES = ("path_glob_match", "nested_traversal")
SENTINELLE = "def test_sentinel_of_the_check():\n    assert False, 'sentinel'\n"


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _copier(projet: Path, cible: Path) -> Path:
    shutil.copytree(projet, cible, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    return cible


def _tests_des_fixtures(copie: Path, sauf: tuple[str, ...] = ()) -> None:
    """Remplace les tests du projet par ceux des fixtures : on note le code, pas les tests."""
    shutil.rmtree(copie / "tests", ignore_errors=True)
    shutil.copytree(FIXTURES / "tests", copie / "tests",
                    ignore=shutil.ignore_patterns("__pycache__", *sauf))


def _rejouer(projet: Path, tmp: Path, tache: dict[str, Any] | None = None
             ) -> tuple[dict[str, Any], Path]:
    """Relance l'agent des fixtures sur une copie du projet, rend (journal, copie)."""
    copie = _copier(projet, tmp / "projet")
    journal = tmp / "journal.json"
    args = [sys.executable, str(AGENT), "--project", str(copie), "--budget", str(BUDGET),
            "--journal", str(journal)]
    if tache is not None:
        fichier_tache = tmp / "task.json"
        fichier_tache.write_text(json.dumps(tache), encoding="utf-8")
        args += ["--task", str(fichier_tache)]
    else:
        args += ["--task", str(TACHE)]
    execution = subprocess.run(  # noqa: S603
        args, cwd=copie, capture_output=True, text=True, timeout=300, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The agent could not play its task on your project.\n{execution.stderr[-800:]}",
        fr=f"L'agent n'a pas pu jouer sa tâche sur votre projet.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8")), copie


def _pytest(copie: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=copie, capture_output=True, text=True, timeout=300, check=False,
    )


def _commande(commande: str, copie: Path) -> int | str:
    """La commande de l'apprenant, telle quelle, avec le Python de ce contrôle en tête du PATH."""
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONPATH", None)
    try:
        fait = subprocess.run(  # noqa: S602
            commande, shell=True, cwd=copie, env=env, capture_output=True, text=True,
            timeout=300, check=False,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    return fait.returncode


def _empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest() if chemin.is_file() else "absent"


def _fichiers(entrees: list[dict[str, Any]]) -> list[str]:
    return [e["file"] for e in entrees]


def _signature(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "startup": [(e["file"], e["cause"]) for e in journal["startup"]],
        "task_context": [(e["file"], e["cause"]) for e in journal["task_context"]],
        "on_demand": sorted(e["file"] for e in journal["on_demand"]),
    }


def test_la_regle_ciblee_se_charge_pour_son_dossier_et_la_tache_reussit(
        projet: Path, tmp_path: Path) -> None:
    """P01 (critique)."""
    rejoue, copie = _rejouer(projet, tmp_path / "tache")
    _tests_des_fixtures(copie)
    suite = _pytest(copie)
    assert suite.returncode == 0, message(
        en="The task on src/commandes/ fails: the tests of the project do not pass after "
        f"the agent's change (it wrote {rejoue['result']['amounts']} amounts).\n"
        f"{suite.stdout[-600:]}",
        fr="La tâche sur src/commandes/ échoue : les tests du projet ne passent pas après "
        f"le changement de l'agent (il a écrit des montants en {rejoue['result']['amounts']}).\n"
        f"{suite.stdout[-600:]}",
    )
    au_demarrage = [e["file"] for e in rejoue["startup"] if e["mentions_decimal"]]
    assert not au_demarrage, message(
        en=f"The rule on amounts (Decimal) is loaded at startup, by {', '.join(au_demarrage)}: "
        "it is loaded for every task, whatever file the agent touches. It must be loaded "
        "only when the agent works in src/commandes/.",
        fr=f"La règle des montants (Decimal) est chargée au démarrage, par "
        f"{', '.join(au_demarrage)} : elle se charge pour toutes les tâches, quel que soit le "
        "fichier touché. Elle ne doit se charger que quand l'agent travaille dans src/commandes/.",
    )
    ciblees = [e for e in rejoue["task_context"]
               if e["mentions_decimal"] and e["cause"] in CAUSES_CIBLEES]
    assert ciblees, message(
        en="The loading journal of the agent shows no rule on amounts (Decimal) loaded "
        f"because the touched file, {rejoue['task']['file']}, is in its scope.",
        fr="Le journal de chargement de l'agent ne montre aucune règle des montants (Decimal) "
        f"chargée parce que le fichier touché, {rejoue['task']['file']}, est dans son périmètre.",
    )
    sonde, _ = _rejouer(projet, tmp_path / "sonde", SONDE_HORS_PERIMETRE)
    hors = [e["file"] for e in sonde["task_context"] if e["mentions_decimal"]]
    assert not hors, message(
        en=f"For a task on {SONDE_HORS_PERIMETRE['file']}, the agent also loads the rule on "
        f"amounts ({', '.join(hors)}): its scope covers more than src/commandes/.",
        fr=f"Pour une tâche sur {SONDE_HORS_PERIMETRE['file']}, l'agent charge aussi la règle "
        f"des montants ({', '.join(hors)}) : son périmètre dépasse src/commandes/.",
    )

    journal = projet / "agent" / "journal.json"
    assert journal.is_file(), message(
        en="agent/journal.json is missing: run the agent on your configuration "
        "(python3 agent/agent.py, from challenge/work).",
        fr="agent/journal.json est absent : lancez l'agent sur votre configuration "
        "(python3 agent/agent.py, depuis challenge/work).",
    )
    try:
        votre = _signature(json.loads(journal.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"agent/journal.json is not a journal written by the agent: {erreur}",
            fr=f"agent/journal.json n'est pas un journal écrit par l'agent : {erreur}",
        ))
    attendue = _signature(rejoue)
    assert votre == attendue, message(
        en="agent/journal.json does not match what the agent loads with your current "
        f"configuration: run the agent again after your last change.\n  yours: {votre}\n"
        f"  now:   {attendue}",
        fr="agent/journal.json ne correspond pas à ce que l'agent charge avec votre "
        f"configuration actuelle : relancez l'agent après votre dernière modification.\n"
        f"  le vôtre : {votre}\n  maintenant : {attendue}",
    )


def test_le_document_volumineux_est_cite_sans_etre_charge(projet: Path, tmp_path: Path) -> None:
    """P02 (critique)."""
    assert _empreinte(projet / GROS_DOCUMENT) == _empreinte(FIXTURES / GROS_DOCUMENT), message(
        en=f"{GROS_DOCUMENT} must still be there, unchanged: the team keeps it for audits. "
        "Keeping it out of the context means not loading it, not deleting it.",
        fr=f"{GROS_DOCUMENT} doit toujours être là, inchangé : l'équipe le garde pour les "
        "audits. Le tenir hors du contexte, c'est ne pas le charger, pas le supprimer.",
    )
    rejoue, _ = _rejouer(projet, tmp_path)
    entree = next((e for e in rejoue["startup"] + rejoue["task_context"]
                   if e["file"] == GROS_DOCUMENT), None)
    assert entree is None, message(
        en=f"{GROS_DOCUMENT} is loaded by the agent: "
        f"{entree}. "
        "An @ import loads the whole file into the context.",
        fr=f"{GROS_DOCUMENT} est chargé par l'agent : "
        f"{entree}. "
        "Un import @ charge le fichier entier dans le contexte.",
    )
    assert GROS_DOCUMENT in _fichiers(rejoue["on_demand"]), message(
        en=f"{GROS_DOCUMENT} is not cited anywhere the agent reads: it does not know the "
        "document exists. Write its path, without @, in the instructions it loads.",
        fr=f"{GROS_DOCUMENT} n'est cité nulle part où l'agent lit : il ignore que le document "
        "existe. Écrivez son chemin, sans @, dans les instructions qu'il charge.",
    )


def test_le_contexte_de_demarrage_tient_dans_le_budget(projet: Path, tmp_path: Path) -> None:
    """P03 (critique). Les lignes sont comptées ici, sur les fichiers que l'agent a chargés."""
    budget = int(json.loads(BUDGET.read_text(encoding="utf-8"))["startup_max_lines"])
    rejoue, copie = _rejouer(projet, tmp_path)
    fichiers = _fichiers(rejoue["startup"])
    assert "CLAUDE.md" in fichiers, message(
        en="CLAUDE.md is missing or not loaded: an empty context fits any budget, and "
        "teaches the agent nothing.",
        fr="CLAUDE.md est absent ou non chargé : un contexte vide tient dans tous les "
        "budgets, et n'apprend rien à l'agent.",
    )
    lignes = {f: len((copie / f).read_text(encoding="utf-8", errors="replace").splitlines())
              for f in fichiers}
    total = sum(lignes.values())
    detail = ", ".join(f"{f} {n}" for f, n in lignes.items())
    assert total <= budget, message(
        en=f"The startup context is {total} lines, over the budget of {budget}: {detail}. "
        "An @ import counts as much as the file that imports it.",
        fr=f"Le contexte de démarrage fait {total} lignes, au-delà du budget de {budget} : "
        f"{detail}. Un import @ compte autant que le fichier qui l'importe.",
    )


def test_la_commande_de_test_ecrite_dans_claude_md_fonctionne(projet: Path, tmp_path: Path) -> None:
    """P04 (non critique). Indépendant de la tâche : test_discount.py est retiré de la copie."""
    rejoue, _ = _rejouer(projet, tmp_path / "rejoue")
    commande = rejoue["test_command"]
    assert commande, message(
        en="The agent finds no test command in CLAUDE.md or its imports. Write it on a "
        "line of the form: - Tests: `the command`",
        fr="L'agent ne trouve aucune commande de test dans CLAUDE.md ni dans ses imports. "
        "Écrivez-la sur une ligne de la forme : - Tests: `la commande`",
    )
    copie = _copier(projet, tmp_path / "commande")
    _tests_des_fixtures(copie, sauf=("test_discount.py",))
    code = _commande(commande, copie)
    assert code == 0, message(
        en=f"`{commande}` (written in {rejoue['test_command_in']}), run as is from the root "
        f"of the project, exits with {code}, not 0.",
        fr=f"`{commande}` (écrite dans {rejoue['test_command_in']}), lancée telle quelle "
        f"depuis la racine du projet, sort en {code}, pas en 0.",
    )
    (copie / "tests" / "test_zz_sentinel.py").write_text(SENTINELLE, encoding="utf-8")
    code = _commande(commande, copie)
    assert code not in (0, "timeout"), message(
        en=f"`{commande}` still exits with 0 when a test of tests/ fails: it does not run "
        "the test suite of the project.",
        fr=f"`{commande}` sort encore en 0 quand un test de tests/ échoue : elle ne lance "
        "pas la suite de tests du projet.",
    )
