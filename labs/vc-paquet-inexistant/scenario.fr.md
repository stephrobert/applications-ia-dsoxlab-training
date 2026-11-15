# Trois dépendances, dont une inventée

## Situation

Pour ajouter un export CSV au **portail-achats**, l'agent de code a écrit un
`requirements.txt` de trois dépendances. Rien n'est encore installé.

Un modèle de code propose parfois un paquet qui n'existe pas : le nom sonne
juste, alors personne ne vérifie. N'importe qui peut ensuite réserver ce nom
sur un index public et y publier ce qu'il veut. La prochaine installation
le récupère. D'où la règle de l'entreprise : les dépendances viennent du
**registre interne**, et chaque ligne est épinglée sur une version exacte et
sur l'empreinte de l'artefact.

Tout est dans `challenge/work` :

| Fichier | Contenu |
|---|---|
| `requirements.txt` | la proposition de l'agent |
| `registry/` | le registre interne : les artefacts (roues) qu'il sert, et `SHA256SUMS` |
| `review.toml` | votre revue, vide |

Le registre est un répertoire local : rien dans ce lab ne sort sur le
réseau, et tous les paquets qu'il contient sont fictifs. L'agent est
simulé.

## Mission

1. **Vérifiez chaque dépendance proposée dans le registre**, avant toute
   installation.
2. **Corrigez `requirements.txt`** : ne gardez que ce que sert le registre,
   et épinglez chaque ligne sur une version exacte (`==`) et sur
   l'empreinte de son artefact (`--hash=sha256:...`). L'export CSV a
   toujours besoin de sa bibliothèque CSV : épinglez-la sur une version que
   sert le registre.
3. **Consignez chaque refus** dans `review.toml`, un bloc `[[refused]]` par
   dépendance refusée telle que l'agent l'a proposée, avec le nom du paquet
   tel que proposé et une raison.
4. **Installez hors ligne** depuis le registre, pour prouver que la liste
   fonctionne.

## Pistes

- `ls registry/` et `cat registry/SHA256SUMS` montrent ce que sert le
  registre. `sha256sum registry/<fichier>.whl` recalcule une empreinte.
- Une ligne épinglée ressemble à
  `nom==1.0.0 --hash=sha256:<64 caractères hexadécimaux>`.
- L'installation hors ligne, dans un environnement virtuel jetable :

  ```bash
  python3 -m venv /tmp/venv-revue
  /tmp/venv-revue/bin/pip install --no-index --find-links registry \
      --require-hashes -r requirements.txt
  ```

  `--no-index` interdit tout index public. Ne le retirez jamais dans ce
  lab : avec un index public, c'est justement le nom inventé qui
  s'installe.

## Vérification

```bash
dsoxlab check vc-paquet-inexistant
```

Trois contrôles. Ils lisent le registre d'origine (pas votre copie), et
rejouent l'installation hors ligne dans un environnement virtuel neuf.
