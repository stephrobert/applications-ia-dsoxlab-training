"""Un serveur MCP non approuvé dans .mcp.json : trois contrôles.

## Ce que ces tests rejouent eux-mêmes

Chaque contrôle relance le banc des fixtures (`bench/mcp_bench.py`) sur une
COPIE du répertoire de travail, avec la liste d'outils des fixtures : modifier
le banc ou `bench/tools.json` dans le répertoire de travail ne change rien au
verdict. Le banc ne lance aucun serveur ; il lit `.mcp.json` et
`.claude/settings.json` comme Claude Code pour cette partie seulement.

## Pourquoi « refusé » et « conservés » sont deux contrôles

P01 (refusé) rejoue le banc après avoir REMIS la déclaration de `quick-share`
dans `.mcp.json` : c'est le cas d'une prochaine contribution qui la rajoute.
Seule une règle `permissions.deny` qui couvre tout le serveur tient encore ;
retirer la ligne de `.mcp.json` ne protège que jusqu'au prochain merge.

P02 (conservés) rejoue le banc sur le projet tel quel : les deux serveurs
approuvés sont chargés avec leur déclaration d'origine, leurs outils
autorisés le restent, et `quick-share` n'est pas chargé. Un harness qui
refuse tout (`mcp__*`, ou `.mcp.json` supprimé) échoue ici et pas en P01 :
l'apprenant lit lequel des deux gestes manque.

## Ce que le journal de l'apprenant prouve, et ce qu'il ne prouve pas

`bench/journal.json` dit que l'apprenant a lancé le banc sur son harness
final et y a VU le refus. Il est comparé à la rejoue, serveur par serveur : un
journal écrit à la main ou périmé ne correspond pas. P03 exige en plus que la
rejoue montre `quick-share` refusé par une règle deny (refusé s'il est
déclaré, « not-declared » sinon) : un journal à jour d'un projet où le serveur
a seulement disparu de `.mcp.json` ne montre aucun refus. Aucun point n'est
accordé sur la foi du journal : c'est la rejoue qui note.
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
LAB_ID = "cc-serveur-mcp-non-approuve"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BANC = FIXTURES / "bench" / "mcp_bench.py"
OUTILS = FIXTURES / "bench" / "tools.json"
NON_APPROUVE = "quick-share"
APPROUVES = ("docs", "tracker")
# Les outils que les réglages d'origine autorisent : un serveur approuvé
# « conservé » doit les garder autorisés.
OUTILS_AUTORISES = (
    "mcp__docs__search",
    "mcp__docs__get_page",
    "mcp__tracker__list_issues",
    "mcp__tracker__get_issue",
)


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


def _declarations_d_origine() -> dict[str, Any]:
    return json.loads((FIXTURES / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]


def _rejouer(projet: Path, tmp: Path, remettre_le_serveur: bool = False) -> dict[str, Any]:
    """Relance le banc des fixtures sur une copie du projet, rend son journal."""
    copie = tmp / "projet"
    shutil.copytree(projet, copie, symlinks=True,
                    ignore=shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache"))
    if remettre_le_serveur:
        chemin = copie / ".mcp.json"
        try:
            contenu = json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else {}
        except ValueError:
            contenu = None
        assert isinstance(contenu, dict), message(
            en=".mcp.json is not a valid JSON object.",
            fr=".mcp.json n'est pas un objet JSON valide.",
        )
        serveurs = contenu.setdefault("mcpServers", {})
        assert isinstance(serveurs, dict), message(
            en=".mcp.json: `mcpServers` must be an object.",
            fr=".mcp.json : `mcpServers` doit être un objet.",
        )
        serveurs[NON_APPROUVE] = _declarations_d_origine()[NON_APPROUVE]
        chemin.write_text(json.dumps(contenu), encoding="utf-8")
    journal = tmp / "journal.json"
    execution = subprocess.run(  # noqa: S603
        [sys.executable, str(BANC), "--project", str(copie),
         "--tools", str(OUTILS), "--journal", str(journal)],
        cwd=copie, capture_output=True, text=True, timeout=60, check=False,
    )
    assert execution.returncode == 0 and journal.is_file(), message(
        en=f"The bench could not read your files.\n{execution.stderr[-800:]}",
        fr=f"Le banc n'a pas pu lire vos fichiers.\n{execution.stderr[-800:]}",
    )
    return json.loads(journal.read_text(encoding="utf-8"))


def _serveur(journal: dict[str, Any], nom: str) -> dict[str, Any] | None:
    return next((s for s in journal["servers"] if s["name"] == nom), None)


def _regles_ignorees(journal: dict[str, Any]) -> str:
    regles = journal.get("ignored_rules") or []
    if not regles:
        return ""
    lignes = ", ".join(f"`{r['rule']}` ({r['reason']})" for r in regles)
    return f" Ignored rules / règles ignorées: {lignes}."


def test_le_serveur_non_approuve_est_refuse(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path, remettre_le_serveur=True)
    serveur = _serveur(journal, NON_APPROUVE)
    assert serveur is not None and serveur["status"] == "refused", message(
        en=f"A contribution that declares `{NON_APPROUVE}` again in .mcp.json gets it "
        f"loaded: {serveur['detail'] if serveur else 'not in the journal'}. Removing it from "
        ".mcp.json only lasts until the next merge: refuse the whole server with a rule "
        "in permissions.deny of .claude/settings.json." + _regles_ignorees(journal),
        fr=f"Une contribution qui redéclare `{NON_APPROUVE}` dans .mcp.json le fait "
        f"charger : {serveur['detail'] if serveur else 'absent du journal'}. Le retirer de "
        ".mcp.json ne tient que jusqu'au prochain merge : refusez le serveur entier par "
        "une règle dans permissions.deny de .claude/settings.json." + _regles_ignorees(journal),
    )


def test_les_serveurs_approuves_sont_conserves(projet: Path, tmp_path: Path) -> None:
    journal = _rejouer(projet, tmp_path)
    origine = _declarations_d_origine()
    for nom in APPROUVES:
        serveur = _serveur(journal, nom)
        assert serveur is not None and serveur["status"] == "loaded", message(
            en=f"The approved server `{nom}` is no longer loaded: "
            f"{serveur['detail'] if serveur else 'it is not declared in .mcp.json'}. "
            "Refusing one server must not cost the team the others.",
            fr=f"Le serveur approuvé `{nom}` n'est plus chargé : "
            f"{serveur['detail'] if serveur else 'absent de .mcp.json'}. "
            "Refuser un serveur ne doit pas priver l'équipe des autres.",
        )
        assert serveur["definition"] == origine[nom], message(
            en=f"The declaration of `{nom}` in .mcp.json changed: "
            f"{json.dumps(serveur['definition'])} instead of {json.dumps(origine[nom])}.",
            fr=f"La déclaration de `{nom}` dans .mcp.json a changé : "
            f"{json.dumps(serveur['definition'])} au lieu de {json.dumps(origine[nom])}.",
        )
    decisions = {o["tool"]: o for s in journal["servers"] for o in s.get("tools", [])}
    for outil in OUTILS_AUTORISES:
        decision = decisions.get(outil, {}).get("decision")
        assert decision == "allowed", message(
            en=f"`{outil}` was allowed and is now `{decision}`. Keep the permissions of "
            "the approved servers as they were.",
            fr=f"`{outil}` était autorisé et vaut maintenant `{decision}`. Gardez les "
            "permissions des serveurs approuvés telles qu'elles étaient.",
        )
    intrus = _serveur(journal, NON_APPROUVE)
    assert intrus is None or intrus["status"] != "loaded", message(
        en=f"The approved servers are there, but `{NON_APPROUVE}` is loaded with them: "
        f"{intrus['detail'] if intrus else ''}. Compare .mcp.json with docs/mcp-servers.md."
        + _regles_ignorees(journal),
        fr=f"Les serveurs approuvés sont là, mais `{NON_APPROUVE}` est chargé avec eux : "
        f"{intrus['detail'] if intrus else ''}. Comparez .mcp.json à docs/mcp-servers.md."
        + _regles_ignorees(journal),
    )


def test_le_journal_correspond_au_harness_actuel(projet: Path, tmp_path: Path) -> None:
    journal = projet / "bench" / "journal.json"
    assert journal.is_file(), message(
        en="bench/journal.json is missing: run the bench on your files "
        "(python3 bench/mcp_bench.py, from challenge/work).",
        fr="bench/journal.json est absent : lancez le banc sur vos fichiers "
        "(python3 bench/mcp_bench.py, depuis challenge/work).",
    )
    try:
        lu = json.loads(journal.read_text(encoding="utf-8"))
        vos_decisions = sorted((s["name"], s["status"], s["cause"]) for s in lu["servers"])
    except (ValueError, KeyError, TypeError) as erreur:
        pytest.fail(message(
            en=f"bench/journal.json is not a journal written by the bench: {erreur}",
            fr=f"bench/journal.json n'est pas un journal écrit par le banc : {erreur}",
        ))
    rejoue = _rejouer(projet, tmp_path)
    attendues = sorted((s["name"], s["status"], s["cause"]) for s in rejoue["servers"])
    assert vos_decisions == attendues, message(
        en="bench/journal.json does not match what the bench decides on your current "
        "files: run it again after your last change.\n  yours: "
        f"{vos_decisions}\n  now:   {attendues}",
        fr="bench/journal.json ne correspond pas à ce que décide le banc sur vos "
        "fichiers actuels : relancez-le après votre dernière modification.\n  le vôtre : "
        f"{vos_decisions}\n  maintenant : {attendues}",
    )
    serveur = _serveur(rejoue, NON_APPROUVE)
    etat = f"{serveur['status']}: {serveur['detail']}" if serveur else "absent"
    assert serveur is not None and serveur["cause"] == "deny-rule", message(
        en=f"Your journal is current, but it does not show `{NON_APPROUVE}` refused by a "
        f"deny rule ({etat}). The journal is your evidence: it must show the refusal.",
        fr=f"Votre journal est à jour, mais il ne montre pas `{NON_APPROUVE}` refusé par "
        f"une règle deny ({etat}). Le journal est votre preuve : il doit montrer le refus.",
    )
