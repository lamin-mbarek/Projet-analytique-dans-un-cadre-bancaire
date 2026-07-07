"""
01 — Inspection réelle de client_accounts.xml.

Ne suppose rien : parcourt l'arbre pour découvrir
  - la structure / imbrication des balises,
  - texte vs attributs,
  - les champs présents sur chaque <account>,
  - les champs optionnels (manquants ou vides) et leur taux de remplissage,
  - les valeurs distinctes des champs à faible cardinalité (candidats enum).
"""
from collections import Counter, defaultdict

from lxml import etree

from config import XML_ACCOUNTS


def inspect():
    tree = etree.parse(str(XML_ACCOUNTS))
    root = tree.getroot()

    print("=" * 70)
    print("STRUCTURE GLOBALE")
    print("=" * 70)
    print(f"Fichier          : {XML_ACCOUNTS.name}")
    print(f"Balise racine    : <{root.tag}>")
    print(f"Attributs racine : {dict(root.attrib) or 'aucun'}")

    accounts = root.findall("account")
    print(f"Nb <account>     : {len(accounts)}")

    if not accounts:
        print("!! Aucun élément <account> trouvé — structure inattendue.")
        return

    # --- Imbrication : quels enfants directs a un <account> ? ---
    first = accounts[0]
    print("\nExemple de premier <account> (imbrication) :")
    print(etree.tostring(first, pretty_print=True, encoding="unicode").rstrip())

    # --- Analyse champ par champ sur TOUS les comptes ---
    n = len(accounts)
    present = Counter()          # champ -> nb de comptes où la balise existe
    non_empty = Counter()        # champ -> nb de comptes où la balise a du texte
    has_children = Counter()     # champ -> nb de fois où il contient des sous-balises
    has_attrib = Counter()       # champ -> nb de fois où il porte des attributs
    distinct_values = defaultdict(set)
    field_order = []

    for acc in accounts:
        seen = set()
        for child in acc:
            tag = child.tag
            if tag not in field_order:
                field_order.append(tag)
            seen.add(tag)
            present[tag] += 1
            text = (child.text or "").strip()
            if text:
                non_empty[tag] += 1
                distinct_values[tag].add(text)
            if len(child):
                has_children[tag] += 1
            if child.attrib:
                has_attrib[tag] += 1

    print("\n" + "=" * 70)
    print("CHAMPS DÉTECTÉS (dans l'ordre d'apparition)")
    print("=" * 70)
    header = f"{'champ':<22}{'présent':>9}{'rempli':>9}{'% rempli':>10}  {'nature'}"
    print(header)
    print("-" * len(header))
    for tag in field_order:
        p, ne = present[tag], non_empty[tag]
        pct = 100 * ne / n
        if has_children[tag]:
            nature = "sous-éléments"
        elif has_attrib[tag]:
            nature = "texte + attributs"
        else:
            nature = "texte simple"
        flag = "  <-- OPTIONNEL/VIDE" if ne < n else ""
        print(f"{tag:<22}{p:>9}{ne:>9}{pct:>9.1f}%  {nature}{flag}")

    # --- Champs candidats à un enum (faible cardinalité) ---
    print("\n" + "=" * 70)
    print("VALEURS DISTINCTES (champs à faible cardinalité — candidats ENUM)")
    print("=" * 70)
    for tag in field_order:
        vals = distinct_values[tag]
        if 0 < len(vals) <= 15:
            print(f"\n{tag}  ({len(vals)} valeurs) :")
            for v in sorted(vals):
                print(f"    - {v}")

    # --- Champs à forte cardinalité (identifiants, texte libre) ---
    print("\n" + "=" * 70)
    print("CHAMPS À FORTE CARDINALITÉ (identifiants / texte libre)")
    print("=" * 70)
    for tag in field_order:
        vals = distinct_values[tag]
        if len(vals) > 15:
            ech = list(sorted(vals))[:3]
            print(f"{tag:<22} {len(vals):>5} valeurs distinctes   ex: {ech}")


if __name__ == "__main__":
    inspect()
