"""Reprendre une session interrompue : quatre contrôles, un par point du cadrage.

## Le point de départ

`setup.yaml` déroule `fixtures/portail-achats.bundle` dans
`challenge/work/portail-achats` : quatre commits sur `main` (C1 à C4, le
dernier ouvre la tranche S3, critères AC-4 et AC-5) et, en travail non
commité, ce que la session interrompue a laissé : `orders.py` modifié, un
test d'un critère FAIT affaibli (`tests/test_submit.py`), un fichier de tests
neuf (`tests/test_review.py`) et un PROGRESS.md qui dit AC-4 « done » alors
que rien n'est commité et qu'AC-3 ne passe plus.

## Ce que ces tests rejouent eux-mêmes

La référence ne vient jamais du dépôt de l'apprenant : chaque contrôle
reclone le bundle des fixtures, et y lit C4, la branche du travail non
commité et le contenu attendu de SPEC.md et des tests faits. Le jugement du
code ne vient pas non plus de ses tests : `reference_orders.py`, copié dans
un instantané d'un commit (`git archive`), dit si ce commit respecte chaque
critère. Les tests de l'apprenant sont joués avec un `pytest.ini` à nous et
sans aucun `conftest.py` : rien dans le dépôt ne peut en désélectionner un.

## Pourquoi des mutants

« Le test d'AC-5 passe » ne dit pas qu'il vérifie AC-5. P01 rejoue le test
que SPEC.md cite pour chaque critère contre des versions cassées de
`orders.py` (`mutants/`), une par manière de manquer le critère : chacune
doit le faire échouer. Pour AC-1 à AC-3, c'est ce qui dit que les tests
faits « restent tueurs » ; pour AC-4 et AC-5, que la tranche est finie pour
de bon et pas seulement verte.

## Pourquoi le dernier commit, et pas le répertoire de travail

Une tranche n'est terminée que commitée : c'est ce que la session suivante
retrouvera. P01 et P04 jugent donc des instantanés de commits, P02 et P03
regardent en plus le répertoire de travail.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-reprise-session"
ICI = Path(__file__).resolve().parent
FIXTURES = ICI.parents[1] / "fixtures"
BUNDLE = FIXTURES / "portail-achats.bundle"
REFERENCE = ICI / "reference_orders.py"
MUTANTS = ICI / "mutants"
PROJET = WORKDIR / "portail-achats"

# Les tests que SPEC.md cite pour chaque critère. SPEC.md ne doit pas bouger
# (P03) : ces noms sont donc fixes.
CITES = {
    "AC-1": "tests/test_create.py::test_new_order_is_draft",
    "AC-2": "tests/test_submit.py::test_submit_draft_order",
    "AC-3": "tests/test_submit.py::test_submit_twice_is_refused",
    "AC-4": "tests/test_review.py::test_approve_submitted_order",
    "AC-5": "tests/test_review.py::test_refuse_requires_reason",
}
FAITS = ("AC-1", "AC-2", "AC-3")
EN_COURS = ("AC-4", "AC-5")
INTOUCHABLES = ("SPEC.md", "tests/test_create.py", "tests/test_submit.py")
JOURNAL = "PROGRESS.md"

# Ce que chaque mutant casse, dit avec les mots de SPEC.md.
MUTATIONS = {
    "mutant_ac1_statut.py": ("a new order that does not start as `draft`",
                             "une commande neuve qui ne démarre pas en `draft`"),
    "mutant_ac2_statut.py": ("a submitted order that does not become `submitted`",
                             "une commande soumise qui ne passe pas en `submitted`"),
    "mutant_ac3_resoumission.py": ("an order that can be submitted again",
                                   "une commande qu'on peut soumettre à nouveau"),
    "mutant_ac4_brouillon.py": ("a draft that can be approved",
                                "un brouillon qu'on peut approuver"),
    "mutant_ac4_statut.py": ("an approval that does not change the status",
                             "une approbation qui ne change pas le statut"),
    "mutant_ac5_sans_motif.py": ("a refusal accepted without any reason",
                                 "un refus accepté sans aucun motif"),
    "mutant_ac5_blanc.py": ("a refusal accepted with a blank reason (spaces only)",
                            "un refus accepté avec un motif blanc (des espaces seulement)"),
    "mutant_ac5_statut.py": ("a refusal without reason that still changes the status",
                             "un refus sans motif qui change quand même le statut"),
    "mutant_ac5_motif.py": ("a refusal that does not keep its reason",
                            "un refus qui ne garde pas son motif"),
}

PYTEST_INI = "[pytest]\npythonpath = .\ntestpaths = tests\n"

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

GARDE = re.compile(
    r"kept|keep|committed|gard[ée]e?s?|conserv[ée]e?s?|commit[ée]e?s?|int[ée]gr[ée]e?s?",
    re.IGNORECASE,
)
ECARTE = re.compile(
    r"discarded|dropped|reverted|restored|[ée]cart[ée]e?s?|abandonn[ée]e?s?|jet[ée]e?s?"
    r"|annul[ée]e?s?|restaur[ée]e?s?",
    re.IGNORECASE,
)
ETATS = {
    "done": "done", "fait": "done", "faite": "done",
    "in progress": "in progress", "en cours": "in progress",
    "to do": "to do", "todo": "to do", "à faire": "to do", "a faire": "to do",
}


# --- outils -------------------------------------------------------------------


def _env() -> dict[str, str]:
    """L'environnement de l'apprenant, sans ce qu'un hook git ou pytest y aurait posé."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("GIT_", "PYTEST_"))} | {"PYTHONDONTWRITEBYTECODE": "1"}


def _git(*args: str, depot: Path = PROJET, binaire: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(depot), *args],  # noqa: S607
        capture_output=True, text=not binaire, env=_env(), timeout=60, check=False,
    )


def _court(sha: str) -> str:
    return sha[:7]


@dataclass
class Reference:
    """Le bundle des fixtures recloné : la vérité du point de départ."""

    depot: Path
    c4: str
    wip: str
    criteres: list[str]
    fichiers_wip: list[str]

    def contenu(self, rev: str, chemin: str) -> bytes:
        res = _git("cat-file", "blob", f"{rev}:{chemin}", depot=self.depot, binaire=True)
        assert res.returncode == 0, f"{rev}:{chemin} introuvable dans le bundle"
        return res.stdout


@dataclass
class Juge:
    """Joue pytest dans des instantanés de commits, et garde ce qu'il a vu."""

    tmp: Path
    greffon: Path
    references: dict[str, dict[str, bool]] = field(default_factory=dict)
    compteur: int = 0

    def instantane(self, rev: str) -> Path:
        self.compteur += 1
        cible = self.tmp / f"instantane-{self.compteur}"
        archive = _git("archive", "--format=tar", rev, binaire=True)
        assert archive.returncode == 0, f"git archive {rev}: {archive.stderr!r}"
        cible.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(cible, filter="data")
        (cible / "pytest.ini").write_text(PYTEST_INI, encoding="utf-8")
        for nom in ("conftest.py", "pyproject.toml", "tox.ini", "setup.cfg"):
            (cible / nom).unlink(missing_ok=True)
        return cible

    def pytest(self, repertoire: Path, *args: str) -> tuple[dict[str, str], str]:
        fichier = repertoire / ".dsoxlab-etats.json"
        env = _env() | {"PYTHONPATH": str(self.greffon), "DSOXLAB_ETATS": str(fichier)}
        execution = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--noconftest",
             "-c", "pytest.ini", "-p", "etats_dsoxlab", *args],
            cwd=repertoire, env=env, capture_output=True, text=True, timeout=120, check=False,
        )
        etats: dict[str, str] = {}
        if fichier.is_file():
            etats = json.loads(fichier.read_text(encoding="utf-8"))
            fichier.unlink()
        return etats, (execution.stdout + execution.stderr)[-1200:]

    def reference(self, rev: str) -> dict[str, bool]:
        """Pour chaque critère AC-n, le code de `rev` le respecte-t-il ?"""
        sha = _git("rev-parse", "--verify", f"{rev}^{{commit}}").stdout.strip()
        if sha not in self.references:
            instantane = self.instantane(sha)
            shutil.copy(REFERENCE, instantane / "_reference_dsoxlab.py")
            etats, _ = self.pytest(instantane, "_reference_dsoxlab.py")
            verdicts: dict[str, bool] = {}
            for n in range(1, 8):
                cas = [e for nid, e in etats.items() if f"::test_ac{n}_" in nid]
                verdicts[f"AC-{n}"] = bool(cas) and all(e == "passed" for e in cas)
            self.references[sha] = verdicts
        return self.references[sha]


def _etat(etats: dict[str, str], noeud: str) -> str:
    """L'état d'un test cité ; un test paramétré réussit si tous ses cas réussissent."""
    cas = [e for n, e in etats.items() if n == noeud or n.startswith(noeud + "[")]
    if not cas:
        return "absent"
    if any(e in ("failed", "error") for e in cas):
        return "failed"
    return "passed" if all(e == "passed" for e in cas) else "skipped"


def _decisions(texte: str, fichiers: list[str]) -> dict[str, str]:
    """La décision consignée pour chaque fichier non commité : kept ou discarded."""
    decisions: dict[str, str] = {}
    for ligne in texte.splitlines():
        m = re.match(r"^\s*[-*+]\s*`?([^`\s:]+)`?\s*:\s*(.+)$", ligne)
        if not m:
            continue
        chemin = m.group(1).removeprefix("./").removeprefix("portail-achats/")
        if chemin not in fichiers:
            continue
        reste = m.group(2)
        garde, ecarte = GARDE.search(reste), ECARTE.search(reste)
        if garde and (not ecarte or garde.start() < ecarte.start()):
            decisions[chemin] = "kept"
        elif ecarte:
            decisions[chemin] = "discarded"
    return decisions


def _tableau(texte: str) -> dict[str, list[tuple[str, str]]]:
    lignes: dict[str, list[tuple[str, str]]] = {}
    for m in re.finditer(r"^\|\s*(AC-\d+)\s*\|([^|\n]*)\|([^|\n]*)\|", texte, re.MULTILINE):
        etat = m.group(2).strip().strip("`*").strip().lower()
        lignes.setdefault(m.group(1), []).append((etat, m.group(3).strip().strip("`")))
    return lignes


@pytest.fixture(scope="module")
def reference(tmp_path_factory: pytest.TempPathFactory) -> Reference:
    depot = tmp_path_factory.mktemp("reference") / "portail-achats.git"
    res = subprocess.run(  # noqa: S603
        ["git", "clone", "--quiet", "--bare", str(BUNDLE), str(depot)],  # noqa: S607
        capture_output=True, text=True, env=_env(), timeout=60, check=False,
    )
    assert res.returncode == 0, f"bundle illisible : {res.stderr}"
    c4 = _git("rev-parse", "main", depot=depot).stdout.strip()
    wip = _git("rev-parse", "wip", depot=depot).stdout.strip()
    spec = _git("cat-file", "blob", f"{c4}:SPEC.md", depot=depot).stdout
    criteres = sorted(set(re.findall(r"^- (AC-\d+) \[", spec, re.MULTILINE)),
                      key=lambda ac: int(ac[3:]))
    fichiers = [f for f in _git("diff", "--name-only", c4, wip, depot=depot).stdout.split()
                if f != JOURNAL]
    return Reference(depot, c4, wip, criteres, fichiers)


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    assert _git("rev-parse", "--verify", "-q", "HEAD").returncode == 0, message(
        en="challenge/work/portail-achats is no longer a Git repository with commits. "
        f"Start again from the interrupted state: `dsoxlab reset {LAB_ID}`.",
        fr="challenge/work/portail-achats n'est plus un dépôt Git avec des commits. "
        f"Repartez de l'état interrompu : `dsoxlab reset {LAB_ID}`.",
    )
    return PROJET


@pytest.fixture(scope="module")
def juge(tmp_path_factory: pytest.TempPathFactory) -> Juge:
    greffon = tmp_path_factory.mktemp("greffon")
    (greffon / "etats_dsoxlab.py").write_text(GREFFON, encoding="utf-8")
    return Juge(tmp_path_factory.mktemp("instantanes"), greffon)


# --- P01 ----------------------------------------------------------------------


def test_la_tranche_interrompue_est_terminee_sans_regression(
    projet: Path, juge: Juge, reference: Reference
) -> None:
    head = _git("rev-parse", "HEAD").stdout.strip()
    instantane = juge.instantane(head)
    etats, sortie = juge.pytest(instantane)
    rouges = [message(en=f"{ac} `{noeud}`: {_etat(etats, noeud)}",
                      fr=f"{ac} `{noeud}` : {_etat(etats, noeud)}")
              for ac, noeud in CITES.items() if _etat(etats, noeud) != "passed"]
    assert not rouges, message(
        en=f"In the last commit ({_court(head)}), the test SPEC.md cites for each criterion "
        "of slices S1 to S3 must exist and pass. A slice is finished when it is "
        "committed: that is what the next session finds.\n  " + "\n  ".join(rouges)
        + f"\n--- pytest on the last commit:\n{sortie}",
        fr=f"Dans le dernier commit ({_court(head)}), le test que SPEC.md cite pour chaque "
        "critère des tranches S1 à S3 doit exister et réussir. Une tranche est terminée "
        "quand elle est commitée : c'est ce que la session suivante retrouve.\n  "
        + "\n  ".join(rouges) + f"\n--- pytest sur le dernier commit :\n{sortie}",
    )

    verdicts = juge.reference(head)
    manques = [ac for ac in (*FAITS, *EN_COURS) if not verdicts[ac]]
    assert not manques, message(
        en=f"Your tests pass, but the code of the last commit ({_court(head)}) does not meet "
        f"{', '.join(manques)} as SPEC.md words it. Read each of these criteria again, "
        "line by line, and run the whole suite, not only the tests of the slice.",
        fr=f"Vos tests passent, mais le code du dernier commit ({_court(head)}) ne respecte "
        f"pas {', '.join(manques)} tel que SPEC.md le formule. Relisez chacun de ces "
        "critères, ligne à ligne, et lancez toute la suite, pas seulement les tests de la "
        "tranche.",
    )

    survivants = []
    for mutant in sorted(MUTANTS.glob("mutant_ac*.py")):
        ac = "AC-" + mutant.name.split("_")[1].removeprefix("ac")
        copie = juge.tmp / f"{mutant.stem}-{juge.compteur}"
        shutil.copytree(instantane, copie)
        shutil.copy(mutant, copie / "orders.py")
        etats_mutant, _ = juge.pytest(copie, CITES[ac])
        if _etat(etats_mutant, CITES[ac]) != "failed":
            en, fr = MUTATIONS[mutant.name]
            survivants.append(message(en=f"{ac}: {en}", fr=f"{ac} : {fr}"))
    assert not survivants, message(
        en="The test SPEC.md cites for a criterion still passes on a version of orders.py "
        "that breaks it. Such a test is green without checking the criterion:\n  - "
        + "\n  - ".join(survivants),
        fr="Le test que SPEC.md cite pour un critère réussit encore sur une version "
        "d'orders.py qui le casse. Un tel test est vert sans vérifier le critère :\n  - "
        + "\n  - ".join(survivants),
    )


# --- P02 ----------------------------------------------------------------------


def test_la_reprise_part_de_l_etat_reel_de_git(projet: Path, reference: Reference) -> None:
    defauts: list[str] = []
    c4 = reference.c4
    if _git("symbolic-ref", "-q", "HEAD").returncode != 0:
        defauts.append(message(
            en="HEAD is detached: commit on a branch, the one the next session will find.",
            fr="HEAD est détaché : commitez sur une branche, celle que la session suivante "
            "retrouvera.",
        ))
    if _git("merge-base", "--is-ancestor", c4, "HEAD").returncode != 0:
        defauts.append(message(
            en=f"The commit {_court(c4)} (\"docs(progress): S1 and S2 done, S3 started\") is no "
            "longer in the history of HEAD: the existing history was rewritten (amend, reset, "
            "rebase). Commits that exist are kept; the resumption adds new ones on top.",
            fr=f"Le commit {_court(c4)} (« docs(progress): S1 and S2 done, S3 started ») n'est "
            "plus dans l'historique de HEAD : l'historique existant a été réécrit (amend, "
            "reset, rebase). Les commits existants se gardent ; la reprise en ajoute "
            "par-dessus.",
        ))
    elif _git("rev-parse", "HEAD").stdout.strip() == c4:
        defauts.append(message(
            en=f"HEAD is still {_court(c4)}, the last commit of the interrupted session: "
            "nothing of the resumption is committed.",
            fr=f"HEAD est encore {_court(c4)}, le dernier commit de la session interrompue : "
            "rien de la reprise n'est commité.",
        ))

    statut = _git("status", "--porcelain", "--untracked-files=all").stdout.rstrip()
    if statut:
        defauts.append(message(
            en="Uncommitted work remains (git status):\n    " + statut.replace("\n", "\n    ")
            + "\n  Each piece is either committed or discarded; nothing is left lying "
            "around for the next session.",
            fr="Du travail non commité reste (git status) :\n    "
            + statut.replace("\n", "\n    ")
            + "\n  Chaque morceau est soit commité, soit écarté ; rien ne traîne pour la "
            "session suivante.",
        ))

    journal = projet / JOURNAL
    texte = journal.read_text(encoding="utf-8") if journal.is_file() else ""
    decisions = _decisions(texte, reference.fichiers_wip)
    absents = [f for f in reference.fichiers_wip if f not in decisions]
    if absents:
        defauts.append(message(
            en=f"PROGRESS.md does not say what became of the uncommitted work found at the "
            f"start: {', '.join(absents)}. Write one line per file, `- <file>: kept ...` or "
            "`- <file>: discarded ...`, with the reason.",
            fr=f"PROGRESS.md ne dit pas ce qu'est devenu le travail non commité trouvé au "
            f"départ : {', '.join(absents)}. Écrivez une ligne par fichier, `- <fichier> : "
            "gardé ...` ou `- <fichier> : écarté ...`, avec la raison.",
        ))
    for fichier, decision in sorted(decisions.items()):
        if decision == "kept":
            touches = _git("log", "--format=%h", f"{c4}..HEAD", "--", fichier).stdout.split()
            if not touches:
                defauts.append(message(
                    en=f"PROGRESS.md says {fichier} was kept, but no commit since "
                    f"{_court(c4)} contains it.",
                    fr=f"PROGRESS.md dit {fichier} gardé, mais aucun commit depuis "
                    f"{_court(c4)} ne le contient.",
                ))
        else:
            dans_head = _git("cat-file", "blob", f"HEAD:{fichier}", binaire=True)
            if dans_head.returncode == 0 and dans_head.stdout == reference.contenu(
                    reference.wip, fichier):
                defauts.append(message(
                    en=f"PROGRESS.md says {fichier} was discarded, but the last commit holds "
                    "exactly the uncommitted version found at the start.",
                    fr=f"PROGRESS.md dit {fichier} écarté, mais le dernier commit contient "
                    "exactement la version non commitée trouvée au départ.",
                ))

    assert not defauts, "\n  ".join([
        message(en="The resumption does not start from the real state of Git:",
                fr="La reprise ne part pas de l'état réel de Git :"),
        *defauts,
    ])


# --- P03 ----------------------------------------------------------------------


def test_la_specification_et_les_tests_faits_sont_inchanges(
    projet: Path, reference: Reference
) -> None:
    attendu = {
        chemin: hashlib.sha256(reference.contenu(reference.c4, chemin)).hexdigest()
        for chemin in INTOUCHABLES
    }
    ecarts: list[str] = []
    for chemin, empreinte in attendu.items():
        fichier = projet / chemin
        actuelle = hashlib.sha256(fichier.read_bytes()).hexdigest() if fichier.is_file() else None
        if actuelle != empreinte:
            ecarts.append(message(en=f"{chemin}, in the working directory",
                                  fr=f"{chemin}, dans le répertoire de travail"))
    for commit in _git("rev-list", f"{reference.c4}..HEAD").stdout.split():
        for chemin, empreinte in attendu.items():
            blob = _git("cat-file", "blob", f"{commit}:{chemin}", binaire=True)
            actuelle = hashlib.sha256(blob.stdout).hexdigest() if blob.returncode == 0 else None
            if actuelle != empreinte:
                ecarts.append(message(en=f"{chemin}, in commit {_court(commit)}",
                                      fr=f"{chemin}, dans le commit {_court(commit)}"))
    assert not ecarts, message(
        en="SPEC.md and the tests of the criteria already done (AC-1 to AC-3) must stay "
        f"identical to commit {_court(reference.c4)} (SHA-256), in the working directory "
        "and in every commit of the resumption. These differ:\n  - " + "\n  - ".join(ecarts)
        + "\n  A test of a done criterion that fails says the code regressed: the fix "
        "goes in the code, never in the test.",
        fr="SPEC.md et les tests des critères déjà faits (AC-1 à AC-3) doivent rester "
        f"identiques au commit {_court(reference.c4)} (SHA-256), dans le répertoire de "
        "travail et dans chaque commit de la reprise. Ceux-ci diffèrent :\n  - "
        + "\n  - ".join(ecarts)
        + "\n  Un test d'un critère fait qui échoue dit que le code a régressé : la "
        "correction va dans le code, jamais dans le test.",
    )


# --- P04 ----------------------------------------------------------------------


def test_progress_est_a_jour_pour_la_session_suivante(
    projet: Path, juge: Juge, reference: Reference
) -> None:
    journal = projet / JOURNAL
    assert journal.is_file(), message(en="PROGRESS.md is missing.",
                                      fr="PROGRESS.md est absent.")
    texte = journal.read_text(encoding="utf-8")
    lignes = _tableau(texte)
    reel = juge.reference("HEAD")
    defauts: list[str] = []
    faits: set[str] = set()

    for ac in reference.criteres:
        if len(lignes.get(ac, [])) != 1:
            defauts.append(message(
                en=f"{ac}: {len(lignes.get(ac, []))} row(s) in the table, one expected",
                fr=f"{ac} : {len(lignes.get(ac, []))} ligne(s) dans le tableau, une attendue",
            ))
            continue
        brut, commit = lignes[ac][0]
        etat = ETATS.get(brut)
        if etat is None:
            defauts.append(message(
                en=f"{ac}: state `{brut}` unknown (done, in progress, to do)",
                fr=f"{ac} : état `{brut}` inconnu (done, in progress, to do)",
            ))
            continue
        if etat == "done":
            faits.add(ac)
        if (etat == "done") != reel[ac]:
            defauts.append(message(
                en=f"{ac} is `{brut}`, but the code of the last commit "
                f"{'meets' if reel[ac] else 'does not meet'} it",
                fr=f"{ac} est `{brut}`, mais le code du dernier commit "
                f"{'le respecte' if reel[ac] else 'ne le respecte pas'}",
            ))
            continue
        if etat != "done":
            continue
        sha = _git("rev-parse", "--verify", "-q", f"{commit}^{{commit}}").stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit) or not sha or _git(
                "merge-base", "--is-ancestor", sha, "HEAD").returncode != 0:
            defauts.append(message(
                en=f"{ac} is done, but `{commit}` is not a commit of the history of HEAD",
                fr=f"{ac} est fait, mais `{commit}` n'est pas un commit de l'historique de HEAD",
            ))
            continue
        parent = _git("rev-parse", "--verify", "-q", f"{sha}^").stdout.strip()
        if not juge.reference(sha)[ac] or (parent and juge.reference(parent)[ac]):
            defauts.append(message(
                en=f"{ac}: {commit} is not the commit that made it pass (cite the first commit "
                "in which it holds)",
                fr=f"{ac} : {commit} n'est pas le commit qui l'a fait passer (citez le premier "
                "commit où il tient)",
            ))

    prochaine = re.search(r"^\W*(?:next action|prochaine action)\W*:(.*)$", texte,
                          re.IGNORECASE | re.MULTILINE)
    cites = re.findall(r"AC-\d+", prochaine.group(1)) if prochaine else []
    if not cites:
        defauts.append(message(
            en="No line `Next action: AC-n ...` naming a criterion",
            fr="Aucune ligne `Next action: AC-n ...` (ou `Prochaine action :`) qui nomme un "
            "critère",
        ))
    elif any(ac not in reference.criteres for ac in cites) or all(ac in faits for ac in cites):
        defauts.append(message(
            en=f"The next action names {', '.join(cites)}: it must name a criterion of SPEC.md "
            "that is not done yet",
            fr=f"La prochaine action nomme {', '.join(cites)} : elle doit nommer un critère de "
            "SPEC.md qui n'est pas encore fait",
        ))

    assert not defauts, "\n  ".join([
        message(en="PROGRESS.md does not tell the next session the truth:",
                fr="PROGRESS.md ne dit pas la vérité à la session suivante :"),
        *defauts,
    ])
