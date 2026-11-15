"""Un hook qui réussit, bloque et plante : cinq contrôles rejoués sur le banc.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance le banc de hooks DES FIXTURES du lab, avec les
événements des fixtures, sur les réglages et les hooks du répertoire de
travail. Modifier `banc/banc_hooks.py` ou `banc/evenements/` dans le
répertoire de travail ne change rien au verdict. Le banc exécute réellement
les hooks de l'apprenant ; il simule l'outil appelé et la décision de Claude
Code d'après le code de sortie et la sortie du hook.

## Pourquoi chaque contrôle ajoute ses propres variantes

Les événements des fixtures sont connus de l'apprenant. Chaque contrôle en
ajoute d'autres (une autre façon de supprimer les tests, un autre défaut de
style, un autre test rouge, un autre outil sur le fichier protégé) : un hook
écrit pour la seule ligne du scénario ne passe pas.

## Pourquoi chaque refus a un pendant qui doit passer

Un hook qui sort toujours en 2 bloque aussi ce qui est légitime. Chaque
contrôle exige donc le refus ET le cas ordinaire sans erreur de hook : les
commandes ordinaires passent, un fichier propre ne déclenche aucun retour,
des tests verts laissent Claude s'arrêter, le fichier de développement reste
modifiable.

## Ce que le journal prouve, et ce qu'il ne prouve pas

`banc/journal.json` dit que l'apprenant a rejoué le banc sur ses hooks
finaux : son empreinte et ses issues sont comparées à la rejoue. Aucun point
n'est accordé sur la foi du journal : c'est la rejoue qui note.
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
LAB_ID = "cc-hook-qui-echoue"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BANC = FIXTURES / "banc" / "banc_hooks.py"
EVENEMENTS = FIXTURES / "banc" / "evenements"
FACTURE = (FIXTURES / "facture.py").read_text(encoding="utf-8")


def _bash(commande: str) -> dict[str, Any]:
    return {"event": {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                      "tool_input": {"command": commande}}}


VARIANTES_SUPPRESSION = {
    "90-pre-variante-git-rm": _bash("git rm -r -q tests"),
    "91-pre-variante-rm-fichier": _bash("rm -f ./tests/test_facture.py"),
}
VARIANTE_LEGITIME = {"92-pre-variante-legitime": _bash("rm -rf dist/ && python3 -m unittest -q")}
VARIANTE_STYLE = {
    "93-post-variante-espaces": {"event": {
        "hook_event_name": "PostToolUse", "tool_name": "Write",
        "tool_input": {"file_path": "taux.py", "content": 'RATE = 0.2   \n'},
        "tool_response": {"filePath": "taux.py", "type": "create"},
    }},
}
VARIANTE_STOP = {
    "95-stop-variante": {
        "files": {"facture.py": FACTURE.replace(
            '        raise ValueError("quantity must be positive")\n', '        pass\n')},
        "event": {"hook_event_name": "Stop", "stop_hook_active": False,
                  "last_assistant_message": "Done.", "background_tasks": [],
                  "session_crons": []},
    },
}
VARIANTES_PRODUCTION = {
    "96-pre-write-production": {"event": {
        "hook_event_name": "PreToolUse", "tool_name": "Write",
        "tool_input": {"file_path": "config/production.toml", "content": "[database]\n"},
    }},
}
VARIANTE_DEVELOPPEMENT = {
    "97-pre-edit-developpement": {"event": {
        "hook_event_name": "PreToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": "config/developpement.toml",
                       "old_string": "pool_size = 2", "new_string": "pool_size = 4"},
    }},
}


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    assert VARIANTE_STOP["95-stop-variante"]["files"]["facture.py"] != FACTURE
    return WORKDIR


def _rejouer(projet: Path, tmp: Path, supplementaires: dict[str, Any] | None = None
             ) -> dict[str, Any]:
    """Relance le banc des fixtures sur les hooks du projet, rend son journal."""
    evenements = tmp / "evenements"
    shutil.copytree(EVENEMENTS, evenements)
    for nom, scene in (supplementaires or {}).items():
        (evenements / f"{nom}.json").write_text(json.dumps(scene), encoding="utf-8")
    journal = tmp / "journal.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(BANC), "--project", str(projet),
         "--events", str(evenements), "--journal", str(journal)],
        cwd=projet, capture_output=True, text=True, timeout=600, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The hook bench could not read your settings.\n{execution.stderr[-800:]}",
        fr=f"Le banc de hooks n'a pas pu lire vos réglages.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8"))


def _evenement(journal: dict[str, Any], identifiant: str) -> dict[str, Any]:
    return next(e for e in journal["events"] if e["id"] == identifiant)


def _resume(entree: dict[str, Any]) -> str:
    hooks = "; ".join(f"exit {h['exit_code']} ({h['status']})" for h in entree["hooks"])
    return f"{entree['outcome']}, via {entree['via']}, hooks: {hooks or 'none ran'}"


def _sans_erreur_de_hook(entree: dict[str, Any]) -> None:
    assert not entree["user_sees"], message(
        en=f"`{entree['id']}` must run without a hook error, and a hook failed "
        f"without blocking: {entree['user_sees'][-1][-300:]}",
        fr=f"`{entree['id']}` doit passer sans erreur de hook, et un hook a échoué "
        f"sans bloquer : {entree['user_sees'][-1][-300:]}",
    )


def test_le_code_2_bloque_la_suppression_des_tests(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, {**VARIANTES_SUPPRESSION, **VARIANTE_LEGITIME})
    for identifiant in ["02-pre-bash-supprimer-tests", *VARIANTES_SUPPRESSION]:
        entree = _evenement(journal, identifiant)
        commande = entree["input"]["command"]
        assert entree["outcome"] == "blocked", message(
            en=f"`{commande}` was not blocked ({_resume(entree)}). Only exit code 2 "
            "blocks a PreToolUse call: exit code 1 is a non-blocking error, and the "
            "command goes on.",
            fr=f"`{commande}` n'a pas été bloquée ({_resume(entree)}). Seul le code de "
            "sortie 2 bloque un appel PreToolUse : le code 1 est une erreur non "
            "bloquante, et la commande passe.",
        )
        assert entree["via"] == "exit-2", message(
            en=f"`{commande}` is blocked by {entree['via']}, not by exit code 2. "
            "This hook must block with exit code 2.",
            fr=f"`{commande}` est bloquée par {entree['via']}, pas par le code de "
            "sortie 2. Ce hook doit bloquer par le code 2.",
        )
        assert entree["claude_sees"], message(
            en=f"`{commande}` is blocked, but Claude receives no reason: on exit code 2, "
            "Claude reads stderr, and the hook wrote nothing there.",
            fr=f"`{commande}` est bloquée, mais Claude ne reçoit aucune raison : en code 2, "
            "Claude lit stderr, et le hook n'y a rien écrit.",
        )
    for identifiant in ["01-pre-bash-tests-unitaires", "03-pre-bash-nettoyer-build",
                        *VARIANTE_LEGITIME]:
        entree = _evenement(journal, identifiant)
        assert entree["outcome"] == "proceeds", message(
            en=f"`{entree['input']['command']}` is ordinary work and must go on "
            f"({_resume(entree)}). A hook that always exits 2 also blocks the work.",
            fr=f"`{entree['input']['command']}` est du travail ordinaire et doit "
            f"passer ({_resume(entree)}). Un hook qui sort toujours en 2 bloque aussi "
            "le travail.",
        )
        _sans_erreur_de_hook(entree)


def test_post_tool_use_renvoie_le_rapport_a_claude(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, VARIANTE_STYLE)
    attendus = {"07-post-write-ligne-longue": ("export_csv.py", "E501"),
                "93-post-variante-espaces": ("taux.py", "W291")}
    for identifiant, (fichier, regle) in attendus.items():
        entree = _evenement(journal, identifiant)
        vu = entree["claude_sees"] or ""
        assert entree["outcome"] == "feedback", message(
            en=f"After writing {fichier}, Claude hears nothing ({_resume(entree)}). On "
            "PostToolUse, only exit code 2 shows something to Claude: its stderr.",
            fr=f"Après l'écriture de {fichier}, Claude n'entend rien ({_resume(entree)}). "
            "Sur PostToolUse, seul le code de sortie 2 montre quelque chose à Claude : "
            "son stderr.",
        )
        assert fichier in vu and regle in vu, message(
            en=f"After writing {fichier}, Claude receives `{vu[:200]}`, not the "
            f"{regle} finding of the checker. The checker prints on stdout, and Claude "
            "reads stderr: send stdout to stderr.",
            fr=f"Après l'écriture de {fichier}, Claude reçoit `{vu[:200]}`, pas le "
            f"constat {regle} du vérificateur. Le vérificateur écrit sur stdout, et "
            "Claude lit stderr : renvoyez stdout vers stderr.",
        )
    propre = _evenement(journal, "06-post-write-propre")
    assert propre["outcome"] == "no-feedback", message(
        en=f"After a clean file, Claude must hear nothing ({_resume(propre)}), and it "
        f"receives: {(propre['claude_sees'] or '')[:200]}",
        fr=f"Après un fichier propre, Claude ne doit rien entendre ({_resume(propre)}), "
        f"et il reçoit : {(propre['claude_sees'] or '')[:200]}",
    )
    _sans_erreur_de_hook(propre)


def test_stop_relance_claude_quand_les_tests_echouent(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, VARIANTE_STOP)
    attendus = {"09-stop-tests-rouges": "test_total_ttc",
                "95-stop-variante": "test_negative_quantity"}
    for identifiant, test_rouge in attendus.items():
        entree = _evenement(journal, identifiant)
        vu = entree["claude_sees"] or ""
        assert entree["outcome"] == "continues", message(
            en=f"`{test_rouge}` fails and Claude stops anyway ({_resume(entree)}). On "
            "Stop, exit code 1 lets Claude stop; exit code 2 sends it back to work.",
            fr=f"`{test_rouge}` échoue et Claude s'arrête quand même ({_resume(entree)}). "
            "Sur Stop, le code 1 laisse Claude s'arrêter ; le code 2 le renvoie au "
            "travail.",
        )
        assert test_rouge in vu, message(
            en=f"Claude goes on, but what it receives does not name the failing test "
            f"`{test_rouge}`: `{vu[:200]}`. It must read the test report.",
            fr=f"Claude continue, mais ce qu'il reçoit ne nomme pas le test en échec "
            f"`{test_rouge}` : `{vu[:200]}`. Il doit lire le rapport des tests.",
        )
    verts = _evenement(journal, "08-stop-tests-verts")
    assert verts["outcome"] == "stops", message(
        en=f"The tests pass, and Claude is not allowed to stop ({_resume(verts)}). A "
        "Stop hook that always exits 2 never lets the turn end.",
        fr=f"Les tests passent, et Claude n'a pas le droit de s'arrêter "
        f"({_resume(verts)}). Un hook Stop qui sort toujours en 2 ne laisse jamais le "
        "tour se finir.",
    )
    _sans_erreur_de_hook(verts)


def test_une_decision_json_refuse_en_code_0(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, {**VARIANTES_PRODUCTION, **VARIANTE_DEVELOPPEMENT})
    for identifiant in ["05-pre-edit-production", *VARIANTES_PRODUCTION]:
        entree = _evenement(journal, identifiant)
        outil = entree["tool"]
        assert entree["outcome"] == "blocked", message(
            en=f"{outil} on config/production.toml was not refused ({_resume(entree)}). "
            "The decision goes under hookSpecificOutput, with hookEventName, and "
            "the hook must match Edit and Write.",
            fr=f"{outil} sur config/production.toml n'a pas été refusé "
            f"({_resume(entree)}). La décision se place sous hookSpecificOutput, avec "
            "hookEventName, et le hook doit viser Edit et Write.",
        )
        assert entree["via"] == "permissionDecision", message(
            en=f"{outil} on config/production.toml is refused by {entree['via']}, not "
            "by a JSON permissionDecision. This hook must exit 0 and print the "
            "decision on stdout.",
            fr=f"{outil} sur config/production.toml est refusé par {entree['via']}, pas "
            "par une permissionDecision JSON. Ce hook doit sortir en 0 et écrire la "
            "décision sur stdout.",
        )
        assert entree["claude_sees"], message(
            en=f"{outil} on config/production.toml is refused without a reason: set "
            "permissionDecisionReason, it is what Claude reads.",
            fr=f"{outil} sur config/production.toml est refusé sans raison : "
            "renseignez permissionDecisionReason, c'est ce que Claude lit.",
        )
    for identifiant in ["04-pre-edit-facture", *VARIANTE_DEVELOPPEMENT]:
        entree = _evenement(journal, identifiant)
        assert entree["outcome"] == "proceeds", message(
            en=f"Editing {entree['input']['file_path']} is ordinary work and must go "
            f"on ({_resume(entree)}).",
            fr=f"Modifier {entree['input']['file_path']} est du travail ordinaire et "
            f"doit passer ({_resume(entree)}).",
        )
        _sans_erreur_de_hook(entree)


def test_le_journal_correspond_aux_hooks_actuels(projet: Path, tmp_path: Path) -> None:
    journal = projet / "banc" / "journal.json"
    assert journal.is_file(), message(
        en="banc/journal.json is missing: run the bench on your hooks "
        "(python3 banc/banc_hooks.py, from challenge/work).",
        fr="banc/journal.json est absent : lancez le banc sur vos hooks "
        "(python3 banc/banc_hooks.py, depuis challenge/work).",
    )
    rejoue = _rejouer(projet, tmp_path)
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))
        vos_issues = [(e["id"], e["outcome"], e["via"]) for e in lu["events"]]
        empreinte = lu["fingerprint"]
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"banc/journal.json is not a journal written by the bench: {erreur}",
            fr=f"banc/journal.json n'est pas un journal écrit par le banc : {erreur}",
        ))
    attendues = [(e["id"], e["outcome"], e["via"]) for e in rejoue["events"]]
    ecarts = [f"{v} != {a}" for v, a in zip(vos_issues, attendues, strict=False) if v != a]
    assert empreinte == rejoue["fingerprint"] and vos_issues == attendues, message(
        en="banc/journal.json does not match your current hooks: run the bench again "
        "after your last change.\n  "
        + "\n  ".join(ecarts or ["settings.json or a hook changed since"]),
        fr="banc/journal.json ne correspond pas à vos hooks actuels : relancez le banc "
        "après votre dernière modification.\n  "
        + "\n  ".join(ecarts or ["settings.json ou un hook a changé depuis"]),
    )
