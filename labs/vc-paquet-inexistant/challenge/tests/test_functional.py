"""Le paquet inexistant : trois contrôles, un par point du cadrage.

## Le registre de référence est celui de fixtures/, jamais celui du workdir

L'apprenant peut tout modifier dans `challenge/work`, y compris y déposer une
fausse roue au nom du paquet inventé. Les contrôles lisent donc le registre
INTACT de `fixtures/registry/` : c'est lui qui dit ce qui existe et quelles
empreintes sont justes.

## Ce que les tests rejouent

L'installation elle-même : un environnement virtuel neuf, puis
`pip install --no-index --find-links <registre> --require-hashes -r
requirements.txt`. Rien ne sort sur le réseau (`--no-index`, et une
configuration pip neutralisée). Un `requirements.txt` qui installe ici
s'installe chez l'apprenant ; l'inverse aussi.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

from conftest import exiger_workdir, message, workdir_lab

WORKDIR = workdir_lab(__file__)
LAB_ID = "vc-paquet-inexistant"
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
REGISTRE = FIXTURES / "registry"

PAQUET_INVENTE = "portail-erp-sdk"
PAQUET_NON_EPINGLE = "portail-csvkit"
PAQUET_LEGITIME = ("portail-money", "1.2.0")

_LIGNE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")


def _normaliser(nom: str) -> str:
    """Le nom d'un projet selon la PEP 503 : minuscules, `-_.` confondus."""
    return re.sub(r"[-_.]+", "-", nom).lower()


def _registre() -> dict[tuple[str, str], str]:
    """{(projet, version): empreinte sha256} des roues du registre intact."""
    contenu: dict[tuple[str, str], str] = {}
    for roue in REGISTRE.glob("*.whl"):
        projet, version = roue.name.split("-")[:2]
        contenu[(_normaliser(projet), version)] = hashlib.sha256(roue.read_bytes()).hexdigest()
    return contenu


def _exigences(texte: str) -> list[dict[str, Any]]:
    """Les lignes d'un requirements.txt, continuations jointes, commentaires retirés."""
    logique = re.sub(r"\\\n", " ", texte)
    exigences = []
    for brute in logique.splitlines():
        ligne = brute.split(" #")[0].strip()
        if not ligne or ligne.startswith("#"):
            continue
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", ligne)
        sans_options = re.sub(r"--hash=\S+", "", ligne).strip()
        trouve = _LIGNE.match(sans_options)
        if not trouve:
            exigences.append({"brut": brute, "nom": None})
            continue
        nom, reste = trouve.groups()
        epingle = re.fullmatch(r"==\s*([A-Za-z0-9.]+)", reste.replace(" ", ""))
        exigences.append({
            "brut": brute.strip(),
            "nom": _normaliser(nom.split("[")[0]),
            "version": epingle.group(1) if epingle else None,
            "hashes": hashes,
        })
    return exigences


@pytest.fixture(scope="module")
def projet() -> Path:
    exiger_workdir(WORKDIR, LAB_ID)
    return WORKDIR


@pytest.fixture(scope="module")
def exigences(projet: Path) -> list[dict[str, Any]]:
    chemin = projet / "requirements.txt"
    assert chemin.is_file(), message(
        en="requirements.txt is missing from challenge/work.",
        fr="requirements.txt est absent de challenge/work.",
    )
    return _exigences(chemin.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def refus(projet: Path) -> dict[str, str]:
    """{paquet normalisé: raison} des blocs [[refused]] de review.toml."""
    chemin = projet / "review.toml"
    assert chemin.is_file(), message(
        en="review.toml is missing from challenge/work.",
        fr="review.toml est absent de challenge/work.",
    )
    try:
        contenu = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        pytest.fail(message(
            en=f"review.toml is not valid TOML: {erreur}",
            fr=f"review.toml n'est pas un TOML valide : {erreur}",
        ))
    blocs = contenu.get("refused", [])
    return {
        _normaliser(str(b.get("package", ""))): str(b.get("reason", "")).strip()
        for b in (blocs if isinstance(blocs, list) else [])
        if isinstance(b, dict)
    }


@pytest.fixture(scope="module")
def installation(projet: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """Rejoue l'installation hors ligne dans un environnement virtuel neuf."""
    racine = tmp_path_factory.mktemp("venv")
    venv = racine / "v"
    creation = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "venv", str(venv)],
        capture_output=True, text=True, timeout=180, check=False,
    )
    if creation.returncode != 0:
        pytest.fail(message(
            en=f"Could not create a virtual environment to replay the install "
            f"(this is the test bench, not your work):\n{creation.stderr[-600:]}",
            fr=f"Impossible de créer un environnement virtuel pour rejouer "
            f"l'installation (c'est le banc, pas votre travail) :\n{creation.stderr[-600:]}",
        ))
    python = venv / "bin" / "python"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PIP_", "PYTHON"))}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX="1",
               PIP_DISABLE_PIP_VERSION_CHECK="1")
    pip = subprocess.run(  # noqa: S603
        [str(python), "-m", "pip", "install", "--no-index", "--find-links", str(REGISTRE),
         "--require-hashes", "-r", str(projet / "requirements.txt")],
        capture_output=True, text=True, timeout=300, check=False, env=env, cwd=racine,
    )
    versions = subprocess.run(  # noqa: S603
        [str(python), "-m", "pip", "list", "--format=freeze"],
        capture_output=True, text=True, timeout=120, check=False, env=env, cwd=racine,
    )
    installes = {}
    for ligne in versions.stdout.splitlines():
        if "==" in ligne:
            nom, version = ligne.split("==", 1)
            installes[_normaliser(nom)] = version
    return {"code": pip.returncode, "sortie": (pip.stdout + pip.stderr)[-1200:],
            "installes": installes}


def test_le_paquet_inexistant_est_detecte_avant_installation(
    exigences: list[dict[str, Any]], refus: dict[str, str]
) -> None:
    registre = {nom for nom, _ in _registre()}
    assert PAQUET_INVENTE not in registre  # le banc lui-même : le registre est intact

    for exigence in exigences:
        assert exigence["nom"] is None or exigence["nom"] in registre, message(
            en=f"requirements.txt still lists `{exigence['brut']}`: the internal "
            "registry serves no package of that name.",
            fr=f"requirements.txt contient encore `{exigence['brut']}` : le registre "
            "interne ne sert aucun paquet de ce nom.",
        )
    assert PAQUET_INVENTE in refus and len(refus[PAQUET_INVENTE]) >= 10, message(
        en="review.toml must record the refusal of each dependency the registry "
        "does not serve, with a reason (a [[refused]] block: package, reason).",
        fr="review.toml doit consigner le refus de chaque dépendance que le "
        "registre ne sert pas, avec une raison (un bloc [[refused]] : package, "
        "reason).",
    )
    faux = sorted(nom for nom in refus if nom in registre and nom != PAQUET_NON_EPINGLE)
    assert not faux, message(
        en=f"review.toml refuses {faux}, which the registry does serve.",
        fr=f"review.toml refuse {faux}, que le registre sert bel et bien.",
    )


def test_une_dependance_non_epinglee_est_refusee(
    exigences: list[dict[str, Any]], refus: dict[str, str]
) -> None:
    registre = _registre()
    for exigence in exigences:
        assert exigence["nom"] and exigence["version"] and exigence["hashes"], message(
            en=f"`{exigence['brut']}` is not pinned: every line needs an exact "
            "version (==) and the hash of the artifact (--hash=sha256:...).",
            fr=f"`{exigence['brut']}` n'est pas épinglée : chaque ligne demande une "
            "version exacte (==) et l'empreinte de l'artefact (--hash=sha256:...).",
        )
    assert PAQUET_NON_EPINGLE in refus and len(refus[PAQUET_NON_EPINGLE]) >= 10, message(
        en="review.toml must record, with a reason, the refusal of each dependency "
        "as the agent proposed it unpinned.",
        fr="review.toml doit consigner, avec une raison, le refus de chaque "
        "dépendance telle que l'agent l'a proposée sans épinglage.",
    )
    lignes = [e for e in exigences if e["nom"] == PAQUET_NON_EPINGLE]
    assert lignes, message(
        en=f"{PAQUET_NON_EPINGLE} is gone from requirements.txt: the feature needs "
        "it. Refusing a dependency as proposed means pinning it, not dropping it.",
        fr=f"{PAQUET_NON_EPINGLE} a disparu de requirements.txt : la fonction en a "
        "besoin. Refuser une dépendance telle que proposée, c'est l'épingler, pas "
        "la retirer.",
    )
    ligne = lignes[0]
    cle = (PAQUET_NON_EPINGLE, ligne["version"])
    assert cle in registre, message(
        en=f"{PAQUET_NON_EPINGLE}=={ligne['version']} does not exist in the internal "
        "registry. Pin a version it serves.",
        fr=f"{PAQUET_NON_EPINGLE}=={ligne['version']} n'existe pas dans le registre "
        "interne. Épinglez une version qu'il sert.",
    )
    assert registre[cle] in ligne["hashes"], message(
        en=f"The hash given for {PAQUET_NON_EPINGLE}=={ligne['version']} is not the "
        "one of the registry's artifact, or is missing.",
        fr=f"L'empreinte donnée pour {PAQUET_NON_EPINGLE}=={ligne['version']} n'est "
        "pas celle de l'artefact du registre, ou manque.",
    )


def test_une_dependance_legitime_et_epinglee_passe(
    exigences: list[dict[str, Any]], refus: dict[str, str], installation: dict[str, Any]
) -> None:
    nom, version = PAQUET_LEGITIME
    assert nom not in refus, message(
        en=f"review.toml refuses {nom}, which is legitimate and already pinned.",
        fr=f"review.toml refuse {nom}, qui est légitime et déjà épinglé.",
    )
    lignes = [e for e in exigences if e["nom"] == nom]
    assert lignes and lignes[0]["version"] == version, message(
        en=f"requirements.txt must keep {nom}=={version}, the version the agent "
        "proposed and the registry serves.",
        fr=f"requirements.txt doit garder {nom}=={version}, la version proposée par "
        "l'agent et servie par le registre.",
    )
    assert _registre()[(nom, version)] in lignes[0]["hashes"], message(
        en=f"The hash given for {nom}=={version} is not the one of the registry's "
        "artifact, or is missing.",
        fr=f"L'empreinte donnée pour {nom}=={version} n'est pas celle de "
        "l'artefact du registre, ou manque.",
    )
    assert installation["code"] == 0, message(
        en="The offline install from the internal registry fails (pip install "
        "--no-index --find-links registry --require-hashes -r requirements.txt):\n"
        + installation["sortie"],
        fr="L'installation hors ligne depuis le registre interne échoue (pip "
        "install --no-index --find-links registry --require-hashes -r "
        "requirements.txt) :\n" + installation["sortie"],
    )
    assert installation["installes"].get(nom) == version, message(
        en=f"After the install, {nom} {version} is not in the environment: "
        f"{installation['installes']}",
        fr=f"Après l'installation, {nom} {version} n'est pas dans l'environnement : "
        f"{installation['installes']}",
    )
