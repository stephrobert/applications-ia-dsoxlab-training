"""Shared code of the platform tools: a YAML subset reader, a JSON Schema
subset validator and the class computation.

Standard library only (Python 3.11 or later), so that the lab needs no
dependency. Both readers REFUSE what they do not understand instead of
guessing: a construct outside the subset, or a schema keyword this validator
does not implement, stops the tool with an error.

YAML subset: block mappings, block sequences (`- item`, `- key: value`),
scalars (plain, 'single' or "double" quoted, integers, true/false, null),
flow lists of scalars (`[a, b]`), `[]` and `{}`, and `#` comments. Dates stay
strings. Anchors, tags and multi-line scalars (`|`, `>`) are refused.
"""

from __future__ import annotations

import json
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

PLATEFORME = Path(__file__).resolve().parent
WORK = PLATEFORME.parent
CLASSES = ("C1", "C2", "C3", "C4")


class Illisible(Exception):
    """A file the tool cannot read without guessing."""


# --- YAML subset -----------------------------------------------------------

_CLE = re.compile(r"^[A-Za-z0-9_.-]+$")
_ENTIER = re.compile(r"^[-+]?[0-9]+$")


def _sans_commentaire(ligne: str) -> str:
    guillemet = ""
    for i, c in enumerate(ligne):
        if guillemet:
            if c == guillemet:
                guillemet = ""
        elif c in "'\"" and (i == 0 or ligne[i - 1] in " \t[,"):
            guillemet = c
        elif c == "#" and (i == 0 or ligne[i - 1] in " \t"):
            return ligne[:i].rstrip()
    return ligne.rstrip()


def _decouper(texte: str) -> list[str]:
    morceaux, courant, guillemet = [], "", ""
    for c in texte:
        if guillemet:
            courant += c
            if c == guillemet:
                guillemet = ""
        elif c in "'\"":
            guillemet = c
            courant += c
        elif c == ",":
            morceaux.append(courant.strip())
            courant = ""
        else:
            courant += c
    if courant.strip():
        morceaux.append(courant.strip())
    return morceaux


def _scalaire(brut: str, numero: int) -> Any:
    s = brut.strip()
    if not s:
        return None
    if s[0] == '"':
        try:
            return json.loads(s)
        except json.JSONDecodeError as erreur:
            raise Illisible(f"line {numero}: bad double-quoted string") from erreur
    if s[0] == "'":
        if len(s) < 2 or s[-1] != "'":
            raise Illisible(f"line {numero}: unterminated single-quoted string")
        return s[1:-1].replace("''", "'")
    if s == "[]":
        return []
    if s == "{}":
        return {}
    if s[0] == "[":
        if s[-1] != "]":
            raise Illisible(f"line {numero}: unterminated flow list")
        return [_scalaire(m, numero) for m in _decouper(s[1:-1])]
    if s[0] in "{|>&*!%@`":
        raise Illisible(
            f"line {numero}: `{s[0]}` is outside the YAML subset this tool reads "
            "(write block mappings and lists, one value per line)"
        )
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if s in ("null", "Null", "NULL", "~"):
        return None
    if _ENTIER.match(s):
        return int(s)
    return s


def _cle_valeur(contenu: str, numero: int) -> tuple[str, str] | None:
    if contenu.startswith(("'", '"')):
        fin = contenu.find(contenu[0], 1)
        if fin < 0:
            raise Illisible(f"line {numero}: unterminated quoted key")
        cle, reste = contenu[1:fin], contenu[fin + 1:]
        if reste == ":":
            return cle, ""
        if reste.startswith(": "):
            return cle, reste[2:].strip()
        return None
    if contenu.endswith(":") and ": " not in contenu:
        cle, valeur = contenu[:-1], ""
    elif ": " in contenu:
        cle, valeur = contenu.split(": ", 1)
    else:
        return None
    if not _CLE.match(cle):
        return None
    return cle, valeur.strip()


def lire_yaml(texte: str) -> Any:
    lignes: list[tuple[int, int, str]] = []
    for numero, brute in enumerate(texte.splitlines(), 1):
        ligne = _sans_commentaire(brute)
        if not ligne.strip():
            continue
        if ligne.strip() == "---" and not lignes:
            continue
        espaces = ligne[: len(ligne) - len(ligne.lstrip())]
        if "\t" in espaces:
            raise Illisible(f"line {numero}: tab in indentation")
        lignes.append((numero, len(espaces), ligne.strip()))
    if not lignes:
        return None

    def bloc(i: int, retrait: int) -> tuple[Any, int]:
        contenu = lignes[i][2]
        if contenu == "-" or contenu.startswith("- "):
            return liste(i, retrait)
        if _cle_valeur(contenu, lignes[i][0]) is None:
            if i + 1 < len(lignes) and lignes[i + 1][1] > retrait:
                raise Illisible(f"line {lignes[i][0]}: expected `key: value`")
            return _scalaire(contenu, lignes[i][0]), i + 1
        return table(i, retrait)

    def liste(i: int, retrait: int) -> tuple[list[Any], int]:
        elements: list[Any] = []
        while i < len(lignes) and lignes[i][1] == retrait:
            numero, _, contenu = lignes[i]
            if not (contenu == "-" or contenu.startswith("- ")):
                break
            reste = contenu[1:].strip()
            if not reste:
                if i + 1 >= len(lignes) or lignes[i + 1][1] <= retrait:
                    elements.append(None)
                    i += 1
                    continue
                valeur, i = bloc(i + 1, lignes[i + 1][1])
            elif _cle_valeur(reste, numero) is not None:
                colonne = retrait + len(contenu) - len(reste)
                lignes[i] = (numero, colonne, reste)
                valeur, i = table(i, colonne)
            else:
                valeur, i = _scalaire(reste, numero), i + 1
            elements.append(valeur)
        return elements, i

    def table(i: int, retrait: int) -> tuple[dict[str, Any], int]:
        resultat: dict[str, Any] = {}
        while i < len(lignes):
            numero, colonne, contenu = lignes[i]
            if colonne < retrait:
                break
            if colonne > retrait:
                raise Illisible(f"line {numero}: unexpected indentation")
            if contenu == "-" or contenu.startswith("- "):
                break
            paire = _cle_valeur(contenu, numero)
            if paire is None:
                raise Illisible(f"line {numero}: expected `key: value`")
            cle, valeur = paire
            if cle in resultat:
                raise Illisible(f"line {numero}: key `{cle}` appears twice")
            i += 1
            if valeur:
                resultat[cle] = _scalaire(valeur, numero)
            elif i < len(lignes) and (
                lignes[i][1] > retrait
                or (lignes[i][1] == retrait
                    and (lignes[i][2] == "-" or lignes[i][2].startswith("- ")))
            ):
                resultat[cle], i = bloc(i, lignes[i][1])
            else:
                resultat[cle] = None
        return resultat, i

    valeur, fin = bloc(0, lignes[0][1])
    if fin < len(lignes):
        raise Illisible(f"line {lignes[fin][0]}: inconsistent indentation")
    return valeur


def lire_fichier_yaml(chemin: Path) -> Any:
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as erreur:
        raise Illisible(f"{chemin}: {erreur.strerror}") from erreur
    try:
        return lire_yaml(texte)
    except Illisible as erreur:
        raise Illisible(f"{chemin}: {erreur}") from erreur


# --- JSON Schema subset (draft 2020-12) ------------------------------------

MOTS_CLES = {
    "$schema", "$id", "title", "description", "type", "enum", "const",
    "required", "properties", "additionalProperties", "items", "minItems",
    "minLength", "maxLength", "pattern", "format", "minimum",
    "exclusiveMinimum", "maximum",
}
_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _type_ok(valeur: Any, attendu: str) -> bool:
    if attendu == "integer":
        return isinstance(valeur, int) and not isinstance(valeur, bool)
    if attendu == "number":
        return isinstance(valeur, int | float) and not isinstance(valeur, bool)
    types = {"string": str, "boolean": bool, "object": dict, "array": list}
    if attendu == "null":
        return valeur is None
    if attendu not in types:
        raise Illisible(f"schema: type `{attendu}` is not supported")
    return isinstance(valeur, types[attendu])


def verifier_schema(schema: Any, chemin: str = "#") -> None:
    """Refuse a schema that uses a keyword this validator does not apply."""
    if not isinstance(schema, dict):
        raise Illisible(f"schema {chemin}: not an object")
    inconnus = set(schema) - MOTS_CLES
    if inconnus:
        raise Illisible(
            f"schema {chemin}: keyword(s) {sorted(inconnus)} not supported by this "
            "validator; it would ignore them, so it refuses to validate"
        )
    for nom, sous in schema.get("properties", {}).items():
        verifier_schema(sous, f"{chemin}/properties/{nom}")
    if isinstance(schema.get("items"), dict):
        verifier_schema(schema["items"], f"{chemin}/items")


def valider(valeur: Any, schema: dict[str, Any], chemin: str = "") -> list[str]:
    ici = chemin or "(root)"
    attendu = schema.get("type")
    if attendu is not None and not _type_ok(valeur, attendu):
        return [f"{ici}: expected {attendu}, found {json.dumps(valeur, ensure_ascii=False)}"]
    erreurs: list[str] = []
    if "enum" in schema and valeur not in schema["enum"]:
        erreurs.append(f"{ici}: `{valeur}` is not one of {schema['enum']}")
    if "const" in schema and valeur != schema["const"]:
        erreurs.append(f"{ici}: must be {schema['const']!r}")
    if isinstance(valeur, str):
        if len(valeur) < schema.get("minLength", 0):
            erreurs.append(f"{ici}: empty or too short")
        if "maxLength" in schema and len(valeur) > schema["maxLength"]:
            erreurs.append(f"{ici}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], valeur):
            erreurs.append(f"{ici}: `{valeur}` does not match {schema['pattern']}")
        if schema.get("format") == "date":
            try:
                if not _DATE.match(valeur):
                    raise ValueError
                date.fromisoformat(valeur)
            except ValueError:
                erreurs.append(f"{ici}: `{valeur}` is not a date YYYY-MM-DD")
    if isinstance(valeur, int | float) and not isinstance(valeur, bool):
        if "minimum" in schema and valeur < schema["minimum"]:
            erreurs.append(f"{ici}: must be at least {schema['minimum']}")
        if "exclusiveMinimum" in schema and valeur <= schema["exclusiveMinimum"]:
            erreurs.append(f"{ici}: must be greater than {schema['exclusiveMinimum']}")
        if "maximum" in schema and valeur > schema["maximum"]:
            erreurs.append(f"{ici}: must be at most {schema['maximum']}")
    if isinstance(valeur, dict):
        for cle in schema.get("required", []):
            if cle not in valeur:
                # Same wording as the jsonschema library: `$.path: 'field' is a
                # required property`.
                ou = "$" + (f".{chemin}" if chemin else "")
                erreurs.append(f"{ou}: '{cle}' is a required property")
        proprietes = schema.get("properties", {})
        for cle, sous in valeur.items():
            if cle in proprietes:
                erreurs.extend(valider(sous, proprietes[cle], f"{chemin}.{cle}".lstrip(".")))
            elif schema.get("additionalProperties") is False:
                erreurs.append(f"{chemin}.{cle}".lstrip(".") + ": unknown field")
    if isinstance(valeur, list):
        if len(valeur) < schema.get("minItems", 0):
            erreurs.append(f"{ici}: at least {schema['minItems']} item(s) expected")
        if isinstance(schema.get("items"), dict):
            for i, element in enumerate(valeur):
                erreurs.extend(valider(element, schema["items"], f"{chemin}[{i}]"))
    return erreurs


# --- Policy files -----------------------------------------------------------

def lire_json(chemin: Path) -> Any:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erreur:
        raise Illisible(f"{chemin}: {erreur}") from erreur


def lire_toml(chemin: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise Illisible(f"{chemin}: {erreur}") from erreur


def classe_calculee(fiche: dict[str, Any], grille: dict[str, Any]) -> str | None:
    """The class the grid gives to a contract: the highest criterion wins.

    Returns None when a criterion cannot be read (the schema says why).
    """
    c = grille["criteres"]
    try:
        donnees = max((c["donnees"][d["categorie"]] for d in fiche["donnees"]), default=0)
        flux = max((c["flux_si"][f["mode"]] for f in fiche["flux_si"]), default=0)
        scores = [
            donnees,
            flux,
            c["utilisateurs"][fiche["utilisateurs"]],
            c["criticite_metier"][fiche["criticite_metier"]],
        ]
    except (KeyError, TypeError):
        return None
    return str(grille["classe_par_score"][str(max(scores))])


def rang(classe: object) -> int:
    return CLASSES.index(classe) + 1 if classe in CLASSES else 0


def ajouter_mois(depart: date, mois: int) -> date:
    annee, mois_index = divmod(depart.month - 1 + mois, 12)
    annee += depart.year
    mois_final = mois_index + 1
    jour = depart.day
    while True:
        try:
            return date(annee, mois_final, jour)
        except ValueError:
            jour -= 1
