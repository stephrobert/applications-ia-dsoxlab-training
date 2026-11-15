# Vérifier les dépendances qu'un agent propose avant de les installer

Lab de niveau 1 de la formation **Sécuriser et gouverner les applications
générées par IA**, parcours « Vibe coder avec méthode ». Un agent de code
propose trois dépendances pour le portail-achats : l'une est légitime et
épinglée, une autre n'est pas épinglée, et la troisième n'existe pas. Vous
les vérifiez dans un registre interne local, refusez ce qui ne peut pas être
accepté tel quel, et livrez une liste épinglée par empreinte qui s'installe
hors ligne.

| | |
|---|---|
| Cible | votre poste : Python 3.11 ou plus avec `venv` et pip. Ni réseau, ni service d'IA, ni clé d'API |
| Durée | environ 30 minutes |
| Leçon associée | [Vibe coding](https://www.stephane-robert.info/docs/developper/vibe-coding/) |
| Précédent | `vc-boucle-methode` |

```bash
dsoxlab run vc-paquet-inexistant
cd labs/vc-paquet-inexistant/challenge/work
cat requirements.txt registry/SHA256SUMS
dsoxlab check vc-paquet-inexistant
```

Tous les paquets du registre sont fictifs, et le registre est un répertoire
local : aucun vrai paquet, malveillant ou non, n'est jamais récupéré.

## Ce que vous saurez faire

- Vérifier qu'une dépendance existe dans un registre de confiance avant de
  l'installer.
- Épingler une dépendance sur une version exacte et sur l'empreinte de son
  artefact.
- Installer hors ligne avec `--no-index --require-hashes`.
- Consigner un refus qui nomme le paquet et la raison.
