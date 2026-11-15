#!/usr/bin/env python3
"""Construit la fixture et la solution de vc-reprise-session.

    python3 construire.py <chemin du lab>

1. Un dépôt du portail-achats : 4 commits sur `main` (C1 à C4), puis une
   branche `wip` qui porte le travail non commité de la session interrompue.
   Le tout part dans fixtures/portail-achats.bundle.
2. Le setup du lab est rejoué à l'identique (clone séparé, WIP posé, remote
   retiré), puis la reprise de référence : deux commits X et Y.
3. La solution est l'état final, posable par copie : les fichiers du projet
   et, dans .git-portail-achats/, l'index, refs/heads/main et un pack des
   objets nouveaux.

Dates, auteurs et environnement git sont fixés : les empreintes de C1 à C4 ne
changent pas d'une construction à l'autre.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AGENT = ("Coding agent", "agent@portail-achats.example")
APPRENANT = ("Learner", "learner@portail-achats.example")
GITDIR = ".git-portail-achats"


def env_git(auteur: tuple[str, str], date: str, home: Path) -> dict[str, str]:
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": auteur[0],
        "GIT_AUTHOR_EMAIL": auteur[1],
        "GIT_COMMITTER_NAME": auteur[0],
        "GIT_COMMITTER_EMAIL": auteur[1],
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }


class Depot:
    def __init__(self, travail: Path, home: Path) -> None:
        self.travail = travail
        self.home = home

    def git(self, *args: str, auteur=AGENT, date="2026-11-10T09:00:00+00:00",
            entree: bytes | None = None) -> str:
        res = subprocess.run(
            ["git", *args], cwd=self.travail, env=env_git(auteur, date, self.home),
            input=entree, capture_output=True, check=False,
        )
        if res.returncode != 0:
            sys.exit(f"git {' '.join(args)} : {res.stderr.decode()}")
        return res.stdout.decode().strip()

    def ecrire(self, fichiers: dict[str, str]) -> None:
        for chemin, contenu in fichiers.items():
            cible = self.travail / chemin
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(contenu, encoding="utf-8")

    def commit(self, message: str, date: str, auteur=AGENT) -> str:
        self.git("add", "-A", auteur=auteur, date=date)
        self.git("commit", "-q", "-m", message, auteur=auteur, date=date)
        return self.git("rev-parse", "HEAD")


# --- contenu du projet ----------------------------------------------------------

GITIGNORE = "__pycache__/\n.pytest_cache/\n"

PYTEST_INI = "[pytest]\npythonpath = .\ntestpaths = tests\n"

SPEC = """\
# Specification: order lifecycle (portail-achats)

The coding agent implements `orders.py` from this file, one slice at a time.
Nobody changes this file during a coding session: changing a requirement is a
decision, taken outside the session.

## Requirements

- **R1**: a new order starts in the `draft` status.
- **R2**: only a draft order can be submitted.
- **R3**: a submitted order is either approved, or refused with a reason.
- **R4**: an order can be cancelled as long as it is not approved.

## Acceptance criteria

- AC-1 [R1]: `Order("PO-1", 120.0)` has the status `draft`.
  Test: `tests/test_create.py::test_new_order_is_draft`
- AC-2 [R2]: submitting a draft order gives it the status `submitted`.
  Test: `tests/test_submit.py::test_submit_draft_order`
- AC-3 [R2]: submitting an order that is not a draft raises
  `InvalidTransition` and leaves its status unchanged.
  Test: `tests/test_submit.py::test_submit_twice_is_refused`
- AC-4 [R3]: approving a submitted order gives it the status `approved`;
  approving a draft raises `InvalidTransition` and leaves it `draft`.
  Test: `tests/test_review.py::test_approve_submitted_order`
- AC-5 [R3]: refusing a submitted order with an empty or blank reason raises
  `ValueError` and leaves it `submitted`; with a reason, the order becomes
  `refused` and keeps that reason in `refusal_reason`.
  Test: `tests/test_review.py::test_refuse_requires_reason`
- AC-6 [R4]: cancelling a draft or a submitted order gives it the status
  `cancelled`.
  Test: `tests/test_cancel.py::test_cancel_before_approval`
- AC-7 [R4]: cancelling an approved order raises `InvalidTransition`.
  Test: `tests/test_cancel.py::test_cancel_approved_is_refused`

## Slices

| Slice | Criteria | Files |
|---|---|---|
| S1 | AC-1 | orders.py, tests/test_create.py |
| S2 | AC-2, AC-3 | orders.py, tests/test_submit.py |
| S3 | AC-4, AC-5 | orders.py, tests/test_review.py |
| S4 | AC-6, AC-7 | orders.py, tests/test_cancel.py |
"""


def progress(lignes: dict[str, tuple[str, str]], suivante: str, journal: list[str]) -> str:
    tableau = "\n".join(f"| {ac} | {etat} | {commit} |" for ac, (etat, commit) in lignes.items())
    entrees = "\n".join(journal)
    return f"""\
# Progress: order lifecycle (portail-achats)

The journal of the work on SPEC.md. Each coding session updates it for the
next one. One row per acceptance criterion.

## Criteria

| Criterion | State | Commit |
|---|---|---|
{tableau}

States: `done` (with the short hash of the commit that made the criterion
pass), `in progress`, `to do`.

## Next action

Next action: {suivante}

## Session log

{entrees}
"""


def etats(**kw: tuple[str, str]) -> dict[str, tuple[str, str]]:
    base = {f"AC-{n}": ("to do", "") for n in range(1, 8)}
    for cle, valeur in kw.items():
        base[cle.replace("_", "-")] = valeur
    return base


ENTETE = '''\
"""Order lifecycle of the portail-achats.

Each method implements acceptance criteria of SPEC.md. Statuses: draft,
submitted, approved, refused, cancelled.
"""


class InvalidTransition(Exception):
    """The order cannot move to the requested status from its current one."""


class Order:
'''

INIT_STUB = '''\
    def __init__(self, reference: str, amount: float) -> None:
        raise NotImplementedError("AC-1")
'''
INIT = '''\
    def __init__(self, reference: str, amount: float) -> None:
        self.reference = reference
        self.amount = amount
        self.status = "draft"
        self.refusal_reason: str | None = None
'''
SUBMIT_STUB = '''
    def submit(self) -> None:
        raise NotImplementedError("AC-2, AC-3")
'''
SUBMIT = '''
    def submit(self) -> None:
        if self.status != "draft":
            raise InvalidTransition(f"{self.reference}: cannot submit a {self.status} order")
        self.status = "submitted"
'''
SUBMIT_WIP = '''
    def submit(self) -> None:
        # A refused order can be corrected and sent again.
        if self.status in ("approved", "cancelled"):
            raise InvalidTransition(f"{self.reference}: cannot submit a {self.status} order")
        self.status = "submitted"
'''
APPROVE_STUB = '''
    def approve(self) -> None:
        raise NotImplementedError("AC-4")
'''
APPROVE = '''
    def approve(self) -> None:
        if self.status != "submitted":
            raise InvalidTransition(f"{self.reference}: cannot approve a {self.status} order")
        self.status = "approved"
'''
REFUSE_STUB = '''
    def refuse(self, reason: str) -> None:
        raise NotImplementedError("AC-5")
'''
REFUSE_WIP = '''
    def refuse(self, reason: str) -> None:
        if self.status != "submitted":
            raise InvalidTransition(f"{self.reference}: cannot refuse a {self.status} order")
        if not reason:
            raise ValueError("a refusal needs a reason")
        # TODO AC-5: not finished
        self.status = "refused"
        self.refusal_reason = reason
'''
REFUSE = '''
    def refuse(self, reason: str) -> None:
        if self.status != "submitted":
            raise InvalidTransition(f"{self.reference}: cannot refuse a {self.status} order")
        if not reason or not reason.strip():
            raise ValueError("a refusal needs a reason")
        self.status = "refused"
        self.refusal_reason = reason
'''
CANCEL_STUB = '''
    def cancel(self) -> None:
        raise NotImplementedError("AC-6, AC-7")
'''


def orders(*parties: str) -> str:
    return ENTETE + "".join(parties)


TEST_CREATE = '''\
from orders import Order


def test_new_order_is_draft():
    assert Order("PO-1", 120.0).status == "draft"
'''

TEST_SUBMIT = '''\
import pytest

from orders import InvalidTransition, Order


def test_submit_draft_order():
    order = Order("PO-2", 450.0)
    order.submit()
    assert order.status == "submitted"


def test_submit_twice_is_refused():
    order = Order("PO-3", 450.0)
    order.submit()
    with pytest.raises(InvalidTransition):
        order.submit()
    assert order.status == "submitted"
'''

TEST_SUBMIT_WIP = '''\
import pytest

from orders import InvalidTransition, Order


def test_submit_draft_order():
    order = Order("PO-2", 450.0)
    order.submit()
    assert order.status == "submitted"


def test_submit_twice_is_refused():
    order = Order("PO-3", 450.0)
    order.submit()
    # Sending an order again is allowed now (refused orders can be corrected).
    order.submit()
    assert order.status == "submitted"
'''

TEST_REVIEW_WIP = '''\
import pytest

from orders import InvalidTransition, Order


def submitted(reference: str = "PO-4") -> Order:
    order = Order(reference, 2300.0)
    order.submit()
    return order


def test_approve_submitted_order():
    order = submitted()
    order.approve()
    assert order.status == "approved"
    draft = Order("PO-5", 80.0)
    with pytest.raises(InvalidTransition):
        draft.approve()
    assert draft.status == "draft"


# AC-5: test_refuse_requires_reason, still to write.
'''

TEST_REVIEW = '''\
import pytest

from orders import InvalidTransition, Order


def submitted(reference: str = "PO-4") -> Order:
    order = Order(reference, 2300.0)
    order.submit()
    return order


def test_approve_submitted_order():
    order = submitted()
    order.approve()
    assert order.status == "approved"
    draft = Order("PO-5", 80.0)
    with pytest.raises(InvalidTransition):
        draft.approve()
    assert draft.status == "draft"


@pytest.mark.parametrize("reason", ["", "   ", "\\t\\n"])
def test_refuse_requires_reason(reason):
    order = submitted("PO-6")
    with pytest.raises(ValueError):
        order.refuse(reason)
    assert order.status == "submitted"
    assert order.refusal_reason is None

    order.refuse("Budget exhausted for Q4")
    assert order.status == "refused"
    assert order.refusal_reason == "Budget exhausted for Q4"
'''


def court(sha: str) -> str:
    return sha[:7]


def construire(lab: Path) -> None:
    racine = Path(tempfile.mkdtemp(prefix="construire-reprise-"))
    home = racine / "home"
    home.mkdir()
    source = racine / "source"
    source.mkdir()
    d = Depot(source, home)
    d.git("init", "-q", "-b", "main")

    # C1
    d.ecrire({
        ".gitignore": GITIGNORE,
        "pytest.ini": PYTEST_INI,
        "SPEC.md": SPEC,
        "PROGRESS.md": progress(etats(), "AC-1 (slice S1).", [
            "- 2026-11-10: SPEC.md written and reviewed; skeleton of orders.py.",
        ]),
        "orders.py": orders(INIT_STUB, SUBMIT_STUB, APPROVE_STUB, REFUSE_STUB, CANCEL_STUB),
        "tests/.gitkeep": "",
    })
    c1 = d.commit("chore: skeleton of the order lifecycle, from SPEC.md",
                  "2026-11-10T09:30:00+00:00")
    # C2
    d.ecrire({
        "orders.py": orders(INIT, SUBMIT_STUB, APPROVE_STUB, REFUSE_STUB, CANCEL_STUB),
        "tests/test_create.py": TEST_CREATE,
    })
    (source / "tests/.gitkeep").unlink()
    c2 = d.commit("feat(orders): AC-1, a new order is a draft (S1)",
                  "2026-11-10T10:15:00+00:00")
    # C3
    d.ecrire({
        "orders.py": orders(INIT, SUBMIT, APPROVE_STUB, REFUSE_STUB, CANCEL_STUB),
        "tests/test_submit.py": TEST_SUBMIT,
    })
    c3 = d.commit("feat(orders): AC-2 and AC-3, only a draft can be submitted (S2)",
                  "2026-11-11T14:05:00+00:00")
    # C4
    d.ecrire({"PROGRESS.md": progress(
        etats(AC_1=("done", court(c2)), AC_2=("done", court(c3)), AC_3=("done", court(c3)),
              AC_4=("in progress", ""), AC_5=("in progress", "")),
        "AC-4 (slice S3), then AC-5.",
        [
            "- 2026-11-10: SPEC.md written and reviewed; skeleton of orders.py.",
            f"- 2026-11-11: S1 and S2 done ({court(c2)}, {court(c3)}). S3 started.",
        ],
    )})
    c4 = d.commit("docs(progress): S1 and S2 done, S3 started", "2026-11-11T14:20:00+00:00")

    # WIP, sur une branche à part : le setup le déroule en travail non commité.
    d.git("switch", "-q", "-c", "wip")
    d.ecrire({
        "orders.py": orders(INIT, SUBMIT_WIP, APPROVE, REFUSE_WIP, CANCEL_STUB),
        "tests/test_submit.py": TEST_SUBMIT_WIP,
        "tests/test_review.py": TEST_REVIEW_WIP,
        "PROGRESS.md": progress(
            etats(AC_1=("done", court(c2)), AC_2=("done", court(c3)), AC_3=("done", court(c3)),
                  AC_4=("done", ""), AC_5=("in progress", "")),
            "AC-5 (slice S3).",
            [
                "- 2026-11-10: SPEC.md written and reviewed; skeleton of orders.py.",
                f"- 2026-11-11: S1 and S2 done ({court(c2)}, {court(c3)}). S3 started.",
                "- 2026-11-12: AC-4 done, the whole suite is green. AC-5 started.",
            ],
        ),
    })
    wip = d.commit("wip", "2026-11-12T17:40:00+00:00")
    d.git("switch", "-q", "main")

    fixtures = lab / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    bundle = fixtures / "portail-achats.bundle"
    if bundle.exists():
        bundle.unlink()
    d.git("bundle", "create", "-q", str(bundle), "HEAD", "main", "wip")

    # --- le setup, rejoué à l'identique ------------------------------------------
    work = racine / "work"
    work.mkdir()
    shutil.copy(bundle, work / "portail-achats.bundle")
    w = Depot(work, home)
    w.git("clone", "-q", "--separate-git-dir", str(work / GITDIR),
          str(work / "portail-achats.bundle"), str(work / "portail-achats"))
    p = Depot(work / "portail-achats", home)
    p.git("checkout", "origin/wip", "--", ".")
    p.git("reset", "-q")
    p.git("remote", "remove", "origin")
    (work / "portail-achats.bundle").unlink()
    statut = p.git("status", "--porcelain")
    print("état de départ :\n" + statut)

    # --- la reprise de référence -----------------------------------------------
    p.git("restore", "tests/test_submit.py")
    p.ecrire({
        "orders.py": orders(INIT, SUBMIT, APPROVE, REFUSE, CANCEL_STUB),
        "tests/test_review.py": TEST_REVIEW,
    })
    date_x = "2026-11-13T09:50:00+00:00"
    p.git("add", "orders.py", "tests/test_review.py", auteur=APPRENANT, date=date_x)
    p.git("commit", "-q", "-m",
          "feat(orders): AC-4 and AC-5, approve or refuse with a reason (S3)\n\n"
          "Resumed from the uncommitted work of the previous session: approve() kept,\n"
          "refuse() finished for blank reasons, the change to submit() that broke AC-3\n"
          "removed. The weakened test of AC-3 was discarded.",
          auteur=APPRENANT, date=date_x)
    x = p.git("rev-parse", "HEAD")
    p.ecrire({"PROGRESS.md": progress(
        etats(AC_1=("done", court(c2)), AC_2=("done", court(c3)), AC_3=("done", court(c3)),
              AC_4=("done", court(x)), AC_5=("done", court(x))),
        "AC-6 (slice S4), then AC-7.",
        [
            "- 2026-11-10: SPEC.md written and reviewed; skeleton of orders.py.",
            f"- 2026-11-11: S1 and S2 done ({court(c2)}, {court(c3)}). S3 started.",
            "- 2026-11-12: AC-4 done, the whole suite is green. AC-5 started.",
            "- 2026-11-13: resumed from Git, not from this file. It said AC-4 was done,",
            "  but nothing after the S3 start was committed, and AC-3 failed.",
            "  Uncommitted work found and what became of it:",
            f"  - orders.py: kept and committed in {court(x)}. approve() was right;",
            "    refuse() finished for blank reasons; the change to submit(), outside",
            "    SPEC.md, that broke AC-3, removed.",
            f"  - tests/test_review.py: kept and committed in {court(x)}, with the test",
            "    of AC-5 added.",
            "  - tests/test_submit.py: discarded. It weakened the test of AC-3, a done",
            "    criterion.",
        ],
    )})
    y = p.commit("docs(progress): S3 done, resumption recorded", "2026-11-13T10:00:00+00:00",
                 auteur=APPRENANT)
    print(f"C1 {c1}\nC2 {c2}\nC3 {c3}\nC4 {c4}\nWIP {wip}\nX {x}\nY {y}")
    assert p.git("status", "--porcelain") == ""

    # --- la solution, posable par copie ------------------------------------------
    solution = lab / "solution"
    if solution.exists():
        shutil.rmtree(solution)
    projet = solution / "portail-achats"
    for rel in ("orders.py", "PROGRESS.md", "tests/test_review.py", "tests/test_submit.py"):
        (projet / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / "portail-achats" / rel, projet / rel)
    gd = solution / GITDIR
    (gd / "refs/heads").mkdir(parents=True)
    (gd / "refs/heads/main").write_text(y + "\n", encoding="ascii")
    shutil.copy2(work / GITDIR / "index", gd / "index")
    pack_dir = gd / "objects/pack"
    pack_dir.mkdir(parents=True)
    nom = p.git("pack-objects", "-q", "--revs", str(pack_dir / "pack"),
                entree=f"{y}\n^{c4}\n".encode())
    print(f"pack {nom}")
    shutil.rmtree(racine)


if __name__ == "__main__":
    construire(Path(sys.argv[1]).resolve())
