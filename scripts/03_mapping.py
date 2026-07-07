"""
03 — Validation XSD + mapping XML -> table plate.

Deux responsabilités, exposées comme fonctions réutilisables par les
scripts suivants :
  validate_xml() : valide client_accounts.xml contre le XSD et log les erreurs.
  xml_to_dataframe() : convertit le XML en DataFrame pandas plat
                       (mêmes noms de colonnes que le cahier des charges).

Lancé directement, le script fait les deux et écrit un CSV de contrôle.
"""
import sys

import pandas as pd
import xmlschema
from lxml import etree

from config import XML_ACCOUNTS, XSD_PATH, ACCOUNT_COLUMNS, BUILD_DIR


def validate_xml(xml_path=XML_ACCOUNTS, xsd_path=XSD_PATH):
    """Valide le XML contre le XSD. Retourne (is_valid, [erreurs])."""
    schema = xmlschema.XMLSchema(str(xsd_path))
    errors = []
    for err in schema.iter_errors(str(xml_path)):
        # position + message court
        path = getattr(err, "path", "?")
        reason = getattr(err, "reason", str(err))
        errors.append(f"{path}: {reason}")
    return (len(errors) == 0), errors


def xml_to_dataframe(xml_path=XML_ACCOUNTS):
    """Convertit chaque <account> en ligne, chaque sous-balise en colonne."""
    root = etree.parse(str(xml_path)).getroot()
    rows = []
    for acc in root.findall("account"):
        row = {child.tag: (child.text or "").strip() for child in acc}
        rows.append(row)
    df = pd.DataFrame(rows)
    # On force l'ordre de colonnes attendu (ajoute les manquantes en NA)
    for col in ACCOUNT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[ACCOUNT_COLUMNS]


def main():
    print("=" * 70)
    print("VALIDATION XSD")
    print("=" * 70)
    ok, errors = validate_xml()
    if ok:
        print("OK — client_accounts.xml est VALIDE au regard du XSD.")
    else:
        print(f"INVALIDE — {len(errors)} erreur(s) :")
        log = BUILD_DIR / "xsd_validation_errors.log"
        log.write_text("\n".join(errors), encoding="utf-8")
        for e in errors[:20]:
            print("  -", e)
        if len(errors) > 20:
            print(f"  ... ({len(errors) - 20} de plus, voir {log})")
        print(f"Log complet : {log}")

    print("\n" + "=" * 70)
    print("MAPPING XML -> TABLE PLATE")
    print("=" * 70)
    df = xml_to_dataframe()
    print(f"DataFrame : {df.shape[0]} lignes x {df.shape[1]} colonnes")
    print(f"Colonnes  : {list(df.columns)}")
    print("\nAperçu :")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(df.head().to_string(index=False))

    out = BUILD_DIR / "accounts_flat.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"\nTable plate écrite : {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
