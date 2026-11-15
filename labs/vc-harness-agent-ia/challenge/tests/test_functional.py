"""Le harness d'un agent : cinq contrôles (P01 à P03, le secret lu par Bash, le travail).

## Pourquoi le secret lu par Bash est un contrôle à part (P05), pas une partie de P01

Une règle `Read(...)` en deny ne couvre pas `cat` lancé par Bash : c'est une
limite documentée des permissions. Les deux refus reposent sur deux mécanismes
distincts (une règle de lecture d'un côté ; un hook ou une règle Bash de
l'autre), et l'apprenant qui n'a posé que le premier doit lire lequel manque.
Un contrôle = un état observable : les fondre en un seul cacherait lequel.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance l'agent factice sur une COPIE du répertoire de
travail, avec l'agent et le scénario des fixtures du lab, pas ceux du
répertoire de travail : modifier `agent/agent.py` pour qu'il refuse tout ne
change rien au verdict. L'agent exécute réellement les hooks de l'apprenant ;
il simule les lectures, les modifications et les commandes.

## Ce que le journal de l'apprenant prouve, et ce qu'il ne prouve pas

`agent/journal.json` dit que l'apprenant a lancé l'agent sur son harness
final. Il est comparé à la rejoue, décision par décision : un journal écrit à
la main ou périmé ne correspond pas. Mais aucun point n'est accordé sur la foi
du journal : c'est la rejoue qui note.

## Pourquoi chaque refus demandé a un pendant qui doit passer

Un harness qui refuse tout refuse aussi le secret. Chaque contrôle exige donc
le refus ET ce qui doit rester possible : le secret toujours présent, le
serveur MCP approuvé joignable, le travail ordinaire de l'agent qui passe.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-harness-agent-ia"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
AGENT = FIXTURES / "agent" / "agent.py"
SCENARIO = FIXTURES / "agent" / "scenario.json"
FICHIER_PROTEGE = "secrets/erp.ini"
SERVEUR_APPROUVE = "docs"
TRAVAIL_LEGITIME = ("read-readme", "edit-code", "run-tests", "clean-build")
# Une autre façon de supprimer un test : le hook doit viser la suppression
# d'un test, pas une ligne de commande précise.
VARIANTES_SUPPRESSION = ("git rm -q tests/test_orders.py", "rm -f ./tests/test_orders.py")
VARIANTE_MCP = "mcp__tracker__create_issue"
# Une autre commande qui lit le secret : le refus doit viser la lecture du
# secret par le shell, pas la seule ligne `cat` du scénario.
VARIANTE_LECTURE_BASH = "head -n 3 ./secrets/erp.ini"


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _scenario(supplementaires: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    scenario["actions"].extend(supplementaires or [])
    return scenario


def _rejouer(projet: Path, tmp: Path, supplementaires: list[dict[str, Any]] | None = None
             ) -> dict[str, Any]:
    """Relance l'agent des fixtures sur une copie du projet, rend son journal."""
    copie = tmp / "projet"
    shutil.copytree(projet, copie, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    scenario = tmp / "scenario.json"
    scenario.write_text(json.dumps(_scenario(supplementaires)), encoding="utf-8")
    journal = tmp / "journal.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(AGENT), "--project", str(copie),
         "--scenario", str(scenario), "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=180, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The agent could not play the scenario on your harness.\n{execution.stderr[-800:]}",
        fr=f"L'agent n'a pas pu jouer le scénario sur votre harness.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8"))


def _action(journal: dict[str, Any], identifiant: str) -> dict[str, Any]:
    return next(a for a in journal["actions"] if a["id"] == identifiant)


def _empreinte(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest() if chemin.is_file() else "absent"


def test_la_lecture_du_secret_echoue(projet: Path, tmp_path: Path) -> None:
    assert _empreinte(projet / FICHIER_PROTEGE) == _empreinte(FIXTURES / FICHIER_PROTEGE), message(
        en=f"{FICHIER_PROTEGE} must still be there, unchanged: the application needs it. "
        "Protecting a secret means refusing to read it, not deleting it.",
        fr=f"{FICHIER_PROTEGE} doit toujours être là, inchangé : l'application en a besoin. "
        "Protéger un secret, c'est refuser sa lecture, pas le supprimer.",
    )
    lecture = _action(_rejouer(projet, tmp_path), "read-secret")
    assert lecture["decision"] == "refused", message(
        en=f"The agent read {FICHIER_PROTEGE}: {lecture['detail']}. Add a rule to "
        "permissions.deny in .claude/settings.json.",
        fr=f"L'agent a lu {FICHIER_PROTEGE} : {lecture['detail']}. Ajoutez une règle à "
        "permissions.deny dans .claude/settings.json.",
    )
    assert lecture["cause"] == "deny-rule", message(
        en=f"Reading {FICHIER_PROTEGE} is refused, but by `{lecture['cause']}`, not by a "
        f"permissions.deny rule: {lecture['detail']}.",
        fr=f"La lecture de {FICHIER_PROTEGE} est refusée, mais par `{lecture['cause']}`, pas "
        f"par une règle permissions.deny : {lecture['detail']}.",
    )


def test_le_secret_ne_se_lit_pas_par_le_shell(projet: Path, tmp_path: Path) -> None:
    variante = {"id": "head-secret", "tool": "Bash", "input": {"command": VARIANTE_LECTURE_BASH}}
    journal = _rejouer(projet, tmp_path, [variante])
    for identifiant in ("cat-secret", "head-secret"):
        lecture = _action(journal, identifiant)
        commande = lecture["input"]["command"]
        assert lecture["decision"] == "refused", message(
            en=f"`{commande}` went through: {lecture['detail']}. A Read rule does not "
            "cover a shell command that prints the file: block it with a PreToolUse "
            "hook on Bash, or with a Bash rule in permissions.deny.",
            fr=f"`{commande}` est passée : {lecture['detail']}. Une règle Read ne couvre "
            "pas une commande shell qui affiche le fichier : bloquez-la par un hook "
            "PreToolUse sur Bash, ou par une règle Bash dans permissions.deny.",
        )
        assert lecture["cause"] in ("hook", "deny-rule"), message(
            en=f"`{commande}` is refused by `{lecture['cause']}`: {lecture['detail']}. "
            "An ask rule waits for an answer; here it must be a refusal.",
            fr=f"`{commande}` est refusée par `{lecture['cause']}` : {lecture['detail']}. "
            "Une règle ask attend une réponse ; ici il faut un refus.",
        )


def test_un_serveur_mcp_inconnu_est_refuse(projet: Path, tmp_path: Path) -> None:
    variante = {"id": "mcp-variant", "tool": VARIANTE_MCP, "input": {"title": "x"}}
    journal = _rejouer(projet, tmp_path, [variante])
    for identifiant in ("mcp-snippets", "mcp-variant"):
        appel = _action(journal, identifiant)
        assert appel["decision"] == "refused", message(
            en=f"The agent called {appel['tool']}, a server nobody approved: "
            f"{appel['detail']}.",
            fr=f"L'agent a appelé {appel['tool']}, un serveur que personne n'a "
            f"approuvé : {appel['detail']}.",
        )
    docs = _action(journal, "mcp-docs")
    assert docs["decision"] == "allowed", message(
        en=f"The approved server `{SERVEUR_APPROUVE}` must stay reachable: "
        f"{docs['detail']}. Declare it in .mcp.json, with the command the "
        "scenario gives.",
        fr=f"Le serveur approuvé `{SERVEUR_APPROUVE}` doit rester joignable : "
        f"{docs['detail']}. Déclarez-le dans .mcp.json, avec la commande que "
        "donne le scénario.",
    )
    assert journal["mcp_servers"] == [SERVEUR_APPROUVE], message(
        en=f".mcp.json must list the approved server and only it. It lists: "
        f"{journal['mcp_servers']}.",
        fr=f".mcp.json doit lister le serveur approuvé et lui seul. Il liste : "
        f"{journal['mcp_servers']}.",
    )


def test_un_hook_bloque_la_suppression_des_tests(projet: Path, tmp_path: Path) -> None:
    variantes = [
        {"id": f"delete-variant-{n}", "tool": "Bash", "input": {"command": commande}}
        for n, commande in enumerate(VARIANTES_SUPPRESSION)
    ]
    journal = _rejouer(projet, tmp_path, variantes)
    for identifiant in ["delete-test"] + [v["id"] for v in variantes]:
        suppression = _action(journal, identifiant)
        commande = suppression["input"]["command"]
        assert suppression["decision"] == "refused", message(
            en=f"`{commande}` went through: {suppression['detail']}. A PreToolUse "
            "hook must block every deletion of a test file.",
            fr=f"`{commande}` est passée : {suppression['detail']}. Un hook "
            "PreToolUse doit bloquer toute suppression d'un fichier de test.",
        )
        assert suppression["cause"] == "hook", message(
            en=f"`{commande}` is refused by `{suppression['cause']}`, not by a "
            "PreToolUse hook. A rule matches one way of writing a command; the "
            "hook reads the command and decides.",
            fr=f"`{commande}` est refusée par `{suppression['cause']}`, pas par un "
            "hook PreToolUse. Une règle vise une façon d'écrire la commande ; le "
            "hook lit la commande et décide.",
        )
    assert (projet / "tests" / "test_orders.py").is_file(), message(
        en="tests/test_orders.py is missing from challenge/work.",
        fr="tests/test_orders.py est absent de challenge/work.",
    )


def test_le_travail_legitime_passe(projet: Path, tmp_path: Path) -> None:
    agents = projet / "AGENTS.md"
    assert agents.is_file() and agents.read_text(encoding="utf-8").strip(), message(
        en="AGENTS.md is missing or empty: the project has no instructions for its agent.",
        fr="AGENTS.md est absent ou vide : le projet n'a pas d'instructions pour son agent.",
    )
    rejoue = _rejouer(projet, tmp_path)
    ignore = rejoue.get("instructions_skipped") or ""
    assert any(i["file"] == "AGENTS.md" for i in rejoue["instructions"]), message(
        en=f"The agent did not load AGENTS.md. {ignore}. When a CLAUDE.md exists, "
        "AGENTS.md is read only if CLAUDE.md imports it with a line `@AGENTS.md`.",
        fr=f"L'agent n'a pas chargé AGENTS.md. {ignore}. Quand un CLAUDE.md existe, "
        "AGENTS.md n'est lu que si CLAUDE.md l'importe par une ligne `@AGENTS.md`.",
    )
    for identifiant in TRAVAIL_LEGITIME:
        action = _action(rejoue, identifiant)
        assert action["decision"] == "allowed", message(
            en=f"The ordinary work of the agent must go through, and "
            f"`{identifiant}` ({action['tool']} {json.dumps(action['input'])}) is "
            f"{action['decision']}: {action['detail']}. A harness that blocks "
            "everything also blocks the work.",
            fr=f"Le travail ordinaire de l'agent doit passer, et `{identifiant}` "
            f"({action['tool']} {json.dumps(action['input'])}) est "
            f"{action['decision']} : {action['detail']}. Un harness qui bloque "
            "tout bloque aussi le travail.",
        )

    journal = projet / "agent" / "journal.json"
    assert journal.is_file(), message(
        en="agent/journal.json is missing: run the agent on your harness "
        "(python3 agent/agent.py, from challenge/work).",
        fr="agent/journal.json est absent : lancez l'agent sur votre harness "
        "(python3 agent/agent.py, depuis challenge/work).",
    )
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))
        vos_decisions = [(a["id"], a["decision"], a["cause"]) for a in lu["actions"]]
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"agent/journal.json is not a journal written by the agent: {erreur}",
            fr=f"agent/journal.json n'est pas un journal écrit par l'agent : {erreur}",
        ))
    attendues = [(a["id"], a["decision"], a["cause"]) for a in rejoue["actions"]]
    ecarts = [f"{v} != {a}" for v, a in zip(vos_decisions, attendues, strict=False) if v != a]
    assert vos_decisions == attendues, message(
        en="agent/journal.json does not match what the agent does on your "
        "current harness: run the agent again after your last change.\n  "
        + "\n  ".join(ecarts or ["different number of actions"]),
        fr="agent/journal.json ne correspond pas à ce que fait l'agent sur votre "
        "harness actuel : relancez l'agent après votre dernière modification.\n  "
        + "\n  ".join(ecarts or ["nombre d'actions différent"]),
    )
