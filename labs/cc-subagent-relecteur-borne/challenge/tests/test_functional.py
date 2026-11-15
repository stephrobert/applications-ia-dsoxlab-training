"""Un subagent relecteur qui hérite de tous les outils : quatre contrôles.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance le banc des fixtures (`bench/agent_bench.py`) sur une
COPIE du répertoire de travail, avec la liste d'outils de session et la liste
d'appels des fixtures : modifier le banc, `bench/session.json` ou
`bench/review.json` dans le répertoire de travail ne change rien au verdict.
Le banc ne lance aucun agent ; il lit `.claude/agents/*.md` comme Claude Code
pour cette partie seulement.

## Pourquoi quatre contrôles

P01 (frontmatter) exige un champ `tools` explicite sur le relecteur, sans
rien changer d'autre : ni son nom, ni sa description, ni son modèle, ni ses
instructions, ni le subagent `correcteur`. Une liste noire
(`disallowedTools`) seule laisse le relecteur hériter de tout ce que la
session gagnera plus tard : elle échoue ici.

P02 (aucune écriture) rejoue les appels de l'incident PLUS des appels que
l'apprenant ne voit pas dans `bench/review.json` : une commande composée qui
commence par `git diff`, un `git checkout --`, un `sed -i`... Un
`Bash(git *)` passe les appels de l'incident à moitié et tombe ici.

P03 (revue possible) rejoue les lectures dont une revue a besoin, sous
plusieurs formes (`git diff --stat`, `git log -p`), sur un relecteur dont les
outils sont listés : un relecteur qui hérite de tout lit, mais ne prouve rien,
et ce contrôle ne passe donc pas avant le travail. Un relecteur réduit à
`Read` ne fait plus de revue : il échoue ici et pas en P02, et l'apprenant lit
lequel des deux gestes manque.

P04 (journal) compare `bench/journal.json` à la rejoue : il prouve que
l'apprenant a lancé le banc sur son fichier final et y a vu les refus. Aucun
point n'est accordé sur la foi du journal : c'est la rejoue qui note.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "cc-subagent-relecteur-borne"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BANC = FIXTURES / "bench" / "agent_bench.py"
SESSION = FIXTURES / "bench" / "session.json"
APPELS = FIXTURES / "bench" / "review.json"
AGENTS = Path(".claude") / "agents"

# Appels d'écriture absents de bench/review.json : l'apprenant ne peut pas
# régler son fichier sur la seule liste qu'il voit.
ECRITURES_CACHEES = [
    {"id": "x1", "tool": "Bash", "input": "git diff main...HEAD && git push"},
    {"id": "x2", "tool": "Bash", "input": "git checkout -- src/orders.py"},
    {"id": "x3", "tool": "Bash", "input": "git reset --hard HEAD~1"},
    {"id": "x4", "tool": "Bash", "input": "sed -i s/0.01/0.1/ src/orders.py"},
    {"id": "x5", "tool": "Bash", "input": "git log --oneline -1; rm -rf src"},
    {"id": "x6", "tool": "Bash", "input": "git stash"},
    {"id": "x7", "tool": "NotebookEdit", "input": "notebooks/prices.ipynb"},
    {"id": "x8", "tool": "Bash", "input": "git status | tee docs/review.md"},
]
# Lectures dont une revue a besoin, sous d'autres formes que dans review.json.
LECTURES_CACHEES = [
    {"id": "y1", "tool": "Bash", "input": "git diff --stat main...HEAD"},
    {"id": "y2", "tool": "Bash", "input": "git log -p -1"},
]


def _banc() -> ModuleType:
    spec = importlib.util.spec_from_file_location("agent_bench_fixtures", BANC)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _appels(fichier: Path, en_plus: list[dict[str, str]]) -> list[dict[str, str]]:
    return json.loads(fichier.read_text(encoding="utf-8"))["calls"] + en_plus


def _rejouer(projet: Path, tmp: Path, en_plus: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Relance le banc des fixtures sur une copie du projet, rend son journal."""
    copie = tmp / "projet"
    shutil.copytree(projet, copie, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    appels = tmp / "appels.json"
    appels.write_text(json.dumps({"calls": _appels(APPELS, en_plus or [])}), encoding="utf-8")
    journal = tmp / "journal.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(BANC), "--project", str(copie), "--session", str(SESSION),
         "--calls", str(appels), "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=60, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The bench could not read your subagent files.\n{execution.stderr[-800:]}",
        fr=f"Le banc n'a pas pu lire vos fichiers de subagent.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8"))


def _inconnus(journal: dict[str, Any]) -> str:
    inconnus = journal.get("unknown_tools") or []
    if not inconnus:
        return ""
    return f" Unknown tools, they grant nothing / outils inconnus, ils n'accordent rien: {', '.join(inconnus)}."


def _autorises(journal: dict[str, Any], prefixes: tuple[str, ...]) -> list[str]:
    return [f"{c['id']} {c['tool']} {c['input']} ({c['reason']})" for c in journal["calls"]
            if c["id"].startswith(prefixes) and c["decision"] == "allowed"]


def test_les_outils_du_relecteur_sont_explicites(projet: Path) -> None:
    banc = _banc()
    try:
        agent = banc.find_agent(projet, "relecteur")
        origine = banc.read_frontmatter(FIXTURES / AGENTS / "relecteur.md")
    except banc.BenchError as erreur:
        pytest.fail(message(
            en=f"The relecteur subagent cannot be read: {erreur}",
            fr=f"Le subagent relecteur est illisible : {erreur}",
        ))
    champs, corps = agent["fields"], agent["body"]
    outils = banc.as_list(champs.get("tools"))
    assert "tools" in champs and outils, message(
        en="The frontmatter of the relecteur subagent has no `tools` list: it inherits every "
        "tool of the session, including those added later. List the tools it needs. "
        "`disallowedTools` alone is a deny list and does not change that.",
        fr="Le frontmatter du subagent relecteur n'a pas de liste `tools` : il hérite de "
        "tous les outils de la session, y compris ceux qui arriveront plus tard. Listez les "
        "outils dont il a besoin. `disallowedTools` seul est une liste noire et n'y change rien.",
    )
    for cle in ("name", "description", "model"):
        assert champs.get(cle) == origine[0].get(cle), message(
            en=f"`{cle}` of the relecteur changed: {champs.get(cle)!r} instead of "
            f"{origine[0].get(cle)!r}. Only its tools are to change.",
            fr=f"`{cle}` du relecteur a changé : {champs.get(cle)!r} au lieu de "
            f"{origine[0].get(cle)!r}. Seuls ses outils doivent changer.",
        )
    assert corps.strip() == origine[1].strip(), message(
        en="The instructions of the relecteur (the text after the frontmatter) changed. "
        "Keep them: the barrier is the tools field, not the prompt.",
        fr="Les instructions du relecteur (le texte après le frontmatter) ont changé. "
        "Gardez-les : la barrière, c'est le champ tools, pas le prompt.",
    )
    correcteur = projet / AGENTS / "correcteur.md"
    attendu = (FIXTURES / AGENTS / "correcteur.md").read_text(encoding="utf-8")
    assert correcteur.is_file() and correcteur.read_text(encoding="utf-8").strip() == attendu.strip(), message(
        en="The correcteur subagent changed or disappeared. It applies fixes on request and "
        "keeps its tools: only the relecteur is concerned.",
        fr="Le subagent correcteur a changé ou disparu. Il applique les corrections sur "
        "demande et garde ses outils : seul le relecteur est concerné.",
    )


def test_le_relecteur_n_a_aucun_outil_d_ecriture(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, ECRITURES_CACHEES)
    passes = _autorises(journal, ("w", "x"))
    assert not passes, message(
        en="The relecteur can still write. These calls would reach a tool:\n  "
        + "\n  ".join(passes) + "\nKeep only what reads. A Bash pattern too wide (`Bash`, "
        "`Bash(git *)`) lets writing commands through." + _inconnus(journal),
        fr="Le relecteur peut encore écrire. Ces appels atteindraient un outil :\n  "
        + "\n  ".join(passes) + "\nNe gardez que ce qui lit. Un motif Bash trop large "
        "(`Bash`, `Bash(git *)`) laisse passer des commandes qui écrivent." + _inconnus(journal),
    )


def test_le_relecteur_peut_encore_faire_une_revue(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, LECTURES_CACHEES)
    assert journal["tools_field"] == "explicit", message(
        en="The relecteur still inherits every tool of the session: it can read, but it "
        "can also write. This check measures the reads of a reviewer whose tools are listed.",
        fr="Le relecteur hérite encore de tous les outils de la session : il peut lire, "
        "mais aussi écrire. Ce contrôle mesure les lectures d'un relecteur dont les outils "
        "sont listés.",
    )
    bloques =[f"{c['id']} {c['tool']} {c['input']} ({c['reason']})" for c in journal["calls"]
               if c["id"].startswith(("r", "y")) and c["decision"] != "allowed"]
    assert not bloques, message(
        en="The relecteur can no longer do its review. These reads are refused:\n  "
        + "\n  ".join(bloques) + "\nA review reads the code, searches it, reads the git "
        "status, history and diff (in several forms), and the tracker issue."
        + _inconnus(journal),
        fr="Le relecteur ne peut plus faire sa revue. Ces lectures sont refusées :\n  "
        + "\n  ".join(bloques) + "\nUne revue lit le code, y cherche, lit l'état, "
        "l'historique et le diff git (sous plusieurs formes), et le ticket du tracker."
        + _inconnus(journal),
    )


def test_le_journal_correspond_au_relecteur_actuel(projet: Path, tmp_path: Path) -> None:
    journal = projet / "bench" / "journal.json"
    assert journal.is_file(), message(
        en="bench/journal.json is missing: run the bench on your files "
        "(python3 bench/agent_bench.py, from challenge/work).",
        fr="bench/journal.json est absent : lancez le banc sur vos fichiers "
        "(python3 bench/agent_bench.py, depuis challenge/work).",
    )
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))
        vos_decisions = [lu["tools_field"]] + [(c["id"], c["decision"]) for c in lu["calls"]]
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"bench/journal.json is not a journal written by the bench: {erreur}",
            fr=f"bench/journal.json n'est pas un journal écrit par le banc : {erreur}",
        ))
    rejoue = _rejouer(projet, tmp_path)
    attendues = [rejoue["tools_field"]] + [(c["id"], c["decision"]) for c in rejoue["calls"]]
    assert vos_decisions == attendues, message(
        en="bench/journal.json does not match what the bench decides on your current "
        "files: run it again after your last change.\n  yours: "
        f"{vos_decisions}\n  now:   {attendues}",
        fr="bench/journal.json ne correspond pas à ce que décide le banc sur vos "
        "fichiers actuels : relancez-le après votre dernière modification.\n  le vôtre : "
        f"{vos_decisions}\n  maintenant : {attendues}",
    )
    passes = _autorises(rejoue, ("w",))
    assert rejoue["tools_field"] == "explicit" and not passes, message(
        en="Your journal is current, but it does not show the writes of the incident "
        f"refused ({', '.join(passes) or 'tools inherited'}). The journal is your evidence: "
        "it must show the refusals.",
        fr="Votre journal est à jour, mais il ne montre pas les écritures de l'incident "
        f"refusées ({', '.join(passes) or 'outils hérités'}). Le journal est votre preuve : "
        "il doit montrer les refus.",
    )
