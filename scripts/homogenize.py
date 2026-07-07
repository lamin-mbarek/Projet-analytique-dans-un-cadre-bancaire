"""
Homogénéisation des données (étape 6).

Transforme les DataFrames bruts en versions typées et nettoyées, prêtes à
alimenter la base 3NF. Toutes les décisions de nettoyage sont EXPLICITES et
tracées dans le dict `NOTES` (documentation des choix, pas de suppression muette).

Règles appliquées :
  - dates  -> datetime (puis stockées en ISO 'AAAA-MM-JJ') ;
  - montants / quantités -> float / int ;
  - déduplication des comptes (3 lignes strictement identiques) ;
  - late_payment_flag -> entier 0/1 ;
  - valeurs manquantes légitimes (paid_date des factures non payées) -> conservées en NULL.
  - devises : positions/transactions en {EUR,USD,CHF} (devise locale conservée) ;
    positions fournit market_value_eur (déjà converti) ; les transactions n'ont
    pas de taux de change source -> montant conservé en devise locale (documenté).
"""
import importlib

import pandas as pd

from loaders import load_positions_raw, load_transactions_raw, load_invoices_raw

mapping = importlib.import_module("03_mapping")

NOTES = []


def _note(msg):
    NOTES.append(msg)


def _to_date(series):
    return pd.to_datetime(series, format="%Y-%m-%d", errors="coerce").dt.date


def homogenize_accounts():
    df = mapping.xml_to_dataframe()
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed = before - len(df)
    if removed:
        _note(f"accounts : {removed} ligne(s) strictement dupliquée(s) supprimée(s) "
              f"(account_id réapparaissant à l'identique) -> {len(df)} comptes uniques.")
    df["opened_date"] = _to_date(df["opened_date"])
    return df


def homogenize_positions():
    df = load_positions_raw().copy()
    df["snapshot_date"] = _to_date(df["snapshot_date"])
    for c in ["quantity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ["price_local", "fx_to_eur", "market_value_eur"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    _note("positions : dates->date, quantité->entier, prix/fx/valeur->float. "
          "market_value_eur déjà en EUR (conversion source conservée).")
    return df


def homogenize_transactions():
    df = load_transactions_raw().copy()
    df["transaction_date"] = _to_date(df["transaction_date"])
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").astype("Int64")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype(float)
    _note("transactions : dates->date, quantité->entier, price->float. "
          "Aucun taux de change fourni -> price conservé en devise locale "
          "(position_currency) sans conversion EUR.")
    return df


def homogenize_invoices():
    df = load_invoices_raw().copy()
    df["invoice_period"] = _to_date(df["invoice_period"])
    df["paid_date"] = _to_date(df["paid_date"])  # NaT -> NULL conservé
    money = ["taxable_base_eur", "withholding_tax_eur", "custody_fee_eur",
             "market_fee_eur", "stamp_duty_eur", "vat_eur", "total_invoice_eur"]
    for c in money:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df["late_payment_flag"] = pd.to_numeric(df["late_payment_flag"],
                                            errors="coerce").astype("Int64")
    n_null_paid = int(df["paid_date"].isna().sum())
    _note(f"invoices : montants->float, flag->entier. {n_null_paid} paid_date "
          f"manquantes CONSERVÉES en NULL (factures ISSUED/OVERDUE non encore payées).")
    return df


def homogenize_all():
    NOTES.clear()
    data = {
        "accounts": homogenize_accounts(),
        "positions": homogenize_positions(),
        "transactions": homogenize_transactions(),
        "invoices": homogenize_invoices(),
    }
    return data, list(NOTES)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    data, notes = homogenize_all()
    print("=== HOMOGÉNÉISATION — décisions documentées ===")
    for n in notes:
        print(" -", n)
    print("\n=== Formes / dtypes ===")
    for name, df in data.items():
        print(f"\n{name}: {df.shape}")
        print(df.dtypes.to_string())
