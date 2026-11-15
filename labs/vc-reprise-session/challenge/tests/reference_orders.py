"""Les tests de référence des critères AC-1 à AC-7, joués contre `orders.py`.

Ce fichier n'est PAS collecté par `dsoxlab check` (il ne commence pas par
`test_`) : test_functional.py le copie dans un instantané d'un commit du
dépôt de l'apprenant et le lance là, un critère à la fois (`-k test_ac4`).
Il dit si le code d'un commit respecte un critère, indépendamment des tests
que l'apprenant a écrits, qu'il pourrait avoir affaiblis.
"""

import pytest
from orders import InvalidTransition, Order


def soumise(reference: str = "PO-90") -> Order:
    commande = Order(reference, 1500.0)
    commande.submit()
    return commande


def test_ac1_une_commande_neuve_est_un_brouillon() -> None:
    assert Order("PO-91", 10.0).status == "draft"


def test_ac2_soumettre_un_brouillon() -> None:
    commande = Order("PO-92", 10.0)
    commande.submit()
    assert commande.status == "submitted"


@pytest.mark.parametrize("etat", ["submitted", "approved", "refused", "cancelled"])
def test_ac3_seul_un_brouillon_se_soumet(etat: str) -> None:
    commande = Order("PO-93", 10.0)
    commande.status = etat
    with pytest.raises(InvalidTransition):
        commande.submit()
    assert commande.status == etat


def test_ac4_approuver_une_commande_soumise() -> None:
    commande = soumise()
    commande.approve()
    assert commande.status == "approved"
    brouillon = Order("PO-94", 10.0)
    with pytest.raises(InvalidTransition):
        brouillon.approve()
    assert brouillon.status == "draft"


@pytest.mark.parametrize("motif", ["", " ", "\t", "  \n "])
def test_ac5_un_refus_exige_un_motif(motif: str) -> None:
    commande = soumise()
    with pytest.raises(ValueError):
        commande.refuse(motif)
    assert commande.status == "submitted"
    commande.refuse("Supplier not referenced")
    assert commande.status == "refused"
    assert commande.refusal_reason == "Supplier not referenced"


@pytest.mark.parametrize("soumettre", [False, True])
def test_ac6_annuler_avant_approbation(soumettre: bool) -> None:
    commande = Order("PO-95", 10.0)
    if soumettre:
        commande.submit()
    commande.cancel()
    assert commande.status == "cancelled"


def test_ac7_une_commande_approuvee_ne_s_annule_pas() -> None:
    commande = soumise()
    commande.approve()
    with pytest.raises(InvalidTransition):
        commande.cancel()
    assert commande.status == "approved"
