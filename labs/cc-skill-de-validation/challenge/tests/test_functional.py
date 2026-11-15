"""Une skill de validation qui ne s'est jamais chargée : cinq contrôles.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance le banc des fixtures (`bench/skill_bench.py`) sur une
COPIE du répertoire de travail : modifier le banc dans le répertoire de
travail ne change rien au verdict. Le banc lit `.claude/skills/valider/` comme
Claude Code pour cette partie seulement, et EXÉCUTE les commandes que les
étapes de la skill désignent.

## Pourquoi cinq contrôles

P01 (structure) : le fichier s'appelle `SKILL.md`, son frontmatter se lit,
`name` vaut le nom du dossier, la description existe, et la validation ne se
lance qu'à la demande (`disable-model-invocation: true`).

P02 (scripts) : les trois scripts vivent dans `scripts/` de la skill, copiés
SANS modification (comparés octet par octet aux originaux des fixtures),
exécutables, et les étapes les appellent directement, dans l'ordre et avec
les arguments de `docs/validation.md`. Un appel par `python3 ...` contourne le
bit d'exécution que la consigne exige : il échoue ici.

P03 (validation réelle) : la skill est jouée sur trois copies du projet, une
saine et deux où un défaut a été INJECTÉ (un secret dans `src/`, puis un test
qui échoue et une ligne trop longue). Chaque défaut doit faire échouer la
bonne étape, et elle seule. Un script remplacé par un `exit 0`, ou une étape
qui s'arrête au premier échec, ne passe pas.

P04 (allowed-tools) : chaque étape est pré-approuvée, et aucune autre
commande ne l'est. Les commandes sondées ne figurent nulle part dans le lab :
`rm`, `git push`, un autre script du dossier, l'appel par un interpréteur.

P05 (journal) : `bench/journal.json` correspond à la rejoue sur le projet
tel quel. Aucun point n'est accordé sur la foi du journal.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "cc-skill-de-validation"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BANC = FIXTURES / "bench" / "skill_bench.py"
SKILL = Path(".claude/skills/valider")
SCRIPTS = SKILL / "scripts"
# Ordre et arguments de docs/validation.md.
ATTENDU = [
    ("check_style.py", ["src", "tests"]),
    ("run_tests.py", []),
    ("check_secrets.py", ["src"]),
]
# Commandes qu'aucune entrée d'allowed-tools ne doit approuver.
SONDES = [
    "rm -rf src",
    "git push",
    "bash -c id",
    "python3 .claude/skills/valider/scripts/check_style.py src tests",
    ".claude/skills/valider/scripts/deploy.py",
    "tools/validation/check_secrets.py src",
]


def _banc() -> ModuleType:
    spec = importlib.util.spec_from_file_location("skill_bench_fixtures", BANC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _copie(projet: Path, tmp: Path, nom: str) -> Path:
    copie = tmp / nom
    shutil.copytree(projet, copie, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    return copie


def _jouer(copie: Path, tmp: Path) -> dict[str, Any]:
    journal = tmp / f"journal-{copie.name}.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(BANC), "--project", str(copie), "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=300, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The bench could not read your skill.\n{execution.stderr[-800:]}",
        fr=f"Le banc n'a pas pu lire votre skill.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8"))


def _structure_valide(journal: dict[str, Any]) -> None:
    assert journal["structure"] == "valid", message(
        en="The skill is not readable as a skill: " + "; ".join(journal["structure_faults"]),
        fr="La skill ne se lit pas comme une skill : " + "; ".join(journal["structure_faults"]),
    )


def _etats(journal: dict[str, Any]) -> list[str]:
    return [f"{s['status']} ({s['command']}: {s['detail']})" for s in journal["steps"]]


def test_la_structure_de_la_skill_est_valide(projet: Path, tmp_path: Path) -> None:
    journal = _jouer(_copie(projet, tmp_path, "projet"), tmp_path)
    _structure_valide(journal)
    assert journal["disable_model_invocation"], message(
        en="The validation must start on demand only, with /valider: add "
        "`disable-model-invocation: true` to the frontmatter.",
        fr="La validation ne doit se lancer qu'à la demande, par /valider : ajoutez "
        "`disable-model-invocation: true` au frontmatter.",
    )


def test_les_scripts_sont_dans_la_skill_et_executables(projet: Path, tmp_path: Path) -> None:
    for nom, _ in ATTENDU:
        script = projet / SCRIPTS / nom
        original = FIXTURES / "tools" / "validation" / nom
        assert script.is_file(), message(
            en=f"{SCRIPTS / nom} is missing: the skill must carry its scripts in its own "
            "scripts/ folder.",
            fr=f"{SCRIPTS / nom} est absent : la skill doit porter ses scripts dans son "
            "propre dossier scripts/.",
        )
        assert script.read_bytes() == original.read_bytes(), message(
            en=f"{SCRIPTS / nom} differs from tools/validation/{nom}: copy the scripts "
            "unchanged.",
            fr=f"{SCRIPTS / nom} diffère de tools/validation/{nom} : copiez les scripts "
            "sans les modifier.",
        )
        assert os.access(script, os.X_OK), message(
            en=f"{SCRIPTS / nom} is not executable (chmod +x).",
            fr=f"{SCRIPTS / nom} n'est pas exécutable (chmod +x).",
        )
    journal = _jouer(_copie(projet, tmp_path, "projet"), tmp_path)
    _structure_valide(journal)
    attendues = [" ".join([str(SCRIPTS / nom), *args]) for nom, args in ATTENDU]
    vues = [s["command"] for s in journal["steps"]]
    assert vues == attendues, message(
        en="The steps of the skill do not call the three scripts directly, in the order "
        f"and with the arguments of docs/validation.md.\n  yours:    {vues}\n  expected: "
        f"{attendues}",
        fr="Les étapes de la skill n'appellent pas les trois scripts directement, dans "
        f"l'ordre et avec les arguments de docs/validation.md.\n  les vôtres : {vues}\n"
        f"  attendues : {attendues}",
    )


def test_la_skill_detecte_les_defauts_injectes(projet: Path, tmp_path: Path) -> None:
    saine = _jouer(_copie(projet, tmp_path, "saine"), tmp_path)
    _structure_valide(saine)
    statuts = [s["status"] for s in saine["steps"]]
    assert len(statuts) == 3 and set(statuts) == {"passed"}, message(
        en="On the project as it is, the three steps must run and pass: "
        + "; ".join(_etats(saine)),
        fr="Sur le projet tel quel, les trois étapes doivent s'exécuter et réussir : "
        + "; ".join(_etats(saine)),
    )

    secret = _copie(projet, tmp_path, "secret")
    config = secret / "src" / "config.py"
    config.write_text(config.read_text(encoding="utf-8")
                      + 'BACKUP_KEY = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
    vu = [s["status"] for s in _jouer(secret, tmp_path)["steps"]]
    assert vu == ["passed", "passed", "failed"], message(
        en=f"A cloud key added to src/config.py must fail the secrets step, and only it: {vu}.",
        fr=f"Une clé cloud ajoutée à src/config.py doit faire échouer l'étape des secrets, "
        f"et elle seule : {vu}.",
    )

    casse = _copie(projet, tmp_path, "casse")
    (casse / "tests" / "test_injecte.py").write_text(
        "import unittest\n\n\nclass Injecte(unittest.TestCase):\n"
        "    def test_echoue(self) -> None:\n        self.assertEqual(1, 2)\n", encoding="utf-8")
    orders = casse / "src" / "orders.py"
    orders.write_text(orders.read_text(encoding="utf-8") + "# " + "x" * 120 + "\n",
                      encoding="utf-8")
    vu = [s["status"] for s in _jouer(casse, tmp_path)["steps"]]
    assert vu == ["failed", "failed", "passed"], message(
        en="A failing test and a line of 122 characters must fail the style and test steps, "
        f"and every step must still run: {vu}.",
        fr="Un test qui échoue et une ligne de 122 caractères doivent faire échouer les étapes "
        f"de style et de tests, et toutes les étapes doivent s'exécuter : {vu}.",
    )


def test_allowed_tools_approuve_exactement_les_trois_appels(projet: Path, tmp_path: Path) -> None:
    journal = _jouer(_copie(projet, tmp_path, "projet"), tmp_path)
    _structure_valide(journal)
    non_approuvees = [s["command"] for s in journal["steps"] if s["status"] == "not-approved"]
    assert journal["steps"] and not non_approuvees, message(
        en="allowed-tools does not cover these steps: Claude Code would ask before each one. "
        f"{non_approuvees or 'no step found'}",
        fr="allowed-tools ne couvre pas ces étapes : Claude Code demanderait avant chacune. "
        f"{non_approuvees or 'aucune étape trouvée'}",
    )
    banc = _banc()
    trop = [f"{c} ← {banc.approving_rule(journal['allowed_tools'], c)}" for c in SONDES
            if banc.approving_rule(journal["allowed_tools"], c)]
    assert not trop, message(
        en="allowed-tools pre-approves more than the three calls:\n  " + "\n  ".join(trop)
        + "\nName each script by its full path, without a bare Bash or a star on the folder.",
        fr="allowed-tools pré-approuve plus que les trois appels :\n  " + "\n  ".join(trop)
        + "\nNommez chaque script par son chemin complet, sans Bash nu ni étoile sur le "
        "dossier.",
    )


def test_le_journal_correspond_a_la_skill_actuelle(projet: Path, tmp_path: Path) -> None:
    journal = projet / "bench" / "journal.json"
    assert journal.is_file(), message(
        en="bench/journal.json is missing: run the bench on your files "
        "(python3 bench/skill_bench.py, from challenge/work).",
        fr="bench/journal.json est absent : lancez le banc sur vos fichiers "
        "(python3 bench/skill_bench.py, depuis challenge/work).",
    )
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))
        vos = [lu["structure"]] + [(s["command"], s["status"]) for s in lu["steps"]]
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"bench/journal.json is not a journal written by the bench: {erreur}",
            fr=f"bench/journal.json n'est pas un journal écrit par le banc : {erreur}",
        ))
    rejoue = _jouer(_copie(projet, tmp_path, "projet"), tmp_path)
    maintenant = [rejoue["structure"]] + [(s["command"], s["status"]) for s in rejoue["steps"]]
    assert vos == maintenant, message(
        en="bench/journal.json does not match what the bench finds on your current files: "
        f"run it again after your last change.\n  yours: {vos}\n  now:   {maintenant}",
        fr="bench/journal.json ne correspond pas à ce que le banc trouve sur vos fichiers "
        f"actuels : relancez-le après votre dernière modification.\n  le vôtre : {vos}\n"
        f"  maintenant : {maintenant}",
    )
    assert rejoue["structure"] == "valid" and rejoue["steps"] and all(
        s["status"] == "passed" for s in rejoue["steps"]), message(
        en="Your journal is current, but it does not show the three steps passed. The journal "
        "is your evidence: it must show a full run.",
        fr="Votre journal est à jour, mais il ne montre pas les trois étapes réussies. Le "
        "journal est votre preuve : il doit montrer une exécution complète.",
    )
