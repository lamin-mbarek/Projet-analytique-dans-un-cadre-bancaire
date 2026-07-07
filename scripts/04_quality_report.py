"""
04 — Rapport de qualité des données (comptes XML + 3 CSV).

Contrôles réalisés par fichier :
  - doublons (lignes entières + clés métier),
  - valeurs manquantes / nulles,
  - incohérences de format (dates non ISO, devises inattendues),
  - valeurs aberrantes (quantités / prix / montants négatifs, nuls, NaN),
  - cohérence référentielle des identifiants entre fichiers.

Chaque anomalie est classée : BLOQUANTE (à corriger avant chargement) ou
INFO (légitime mais à documenter). Un résumé final est affiché.
"""
import sys
import importlib

import pandas as pd

from config import ACCOUNT_COLUMNS, BUILD_DIR
from loaders import load_positions_raw, load_transactions_raw, load_invoices_raw

# import du mapping XML (module au nom numérique -> import dynamique)
mapping = importlib.import_module("03_mapping")

# Devises attendues par fichier (référentiel métier)
EXPECTED_CURRENCIES = {"USD", "EUR", "CHF"}

findings = []  # (fichier, niveau, message)


def add(fichier, niveau, message):
    findings.append((fichier, niveau, message))
    tag = "BLOQUANT" if niveau == "BLOCK" else "INFO"
    print(f"  [{tag:8}] {message}")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def check_duplicates(name, df, key_cols):
    full = df.duplicated().sum()
    if full:
        add(name, "BLOCK", f"{full} ligne(s) entièrement dupliquée(s)")
    else:
        print(f"  [OK      ] aucune ligne entièrement dupliquée")
    if key_cols:
        kd = df.duplicated(subset=key_cols).sum()
        if kd:
            dups = (df[df.duplicated(subset=key_cols, keep=False)]
                    [key_cols].drop_duplicates())
            ech = dups.head(3).to_dict("records")
            add(name, "BLOCK",
                f"{kd} doublon(s) sur clé métier {key_cols} — ex: {ech}")
        else:
            print(f"  [OK      ] clé métier {key_cols} unique")


def check_nulls(name, df, expected_optional=()):
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        print("  [OK      ] aucune valeur manquante")
        return
    for col, cnt in nulls.items():
        if col in expected_optional:
            add(name, "INFO",
                f"{col}: {cnt} valeur(s) manquante(s) — optionnel légitime")
        else:
            add(name, "BLOCK", f"{col}: {cnt} valeur(s) manquante(s) inattendue(s)")


def check_dates(name, df, date_cols):
    for c in date_cols:
        if c not in df:
            continue
        s = df[c].dropna().astype(str)
        bad = s[~s.str.match(r"^\d{4}-\d{2}-\d{2}$")]
        if len(bad):
            add(name, "BLOCK",
                f"{c}: {len(bad)} date(s) non ISO (AAAA-MM-JJ) — ex {list(bad.unique())[:3]}")
        else:
            print(f"  [OK      ] {c}: format date ISO homogène")


def check_currencies(name, df, cur_cols, allowed):
    for c in cur_cols:
        if c not in df:
            continue
        vals = set(df[c].dropna().unique())
        unexpected = vals - allowed
        if unexpected:
            add(name, "INFO",
                f"{c}: devise(s) hors référentiel {allowed} -> {unexpected}")
        else:
            print(f"  [OK      ] {c}: devises dans {sorted(vals)}")


def check_numeric(name, df, cols):
    for c in cols:
        if c not in df:
            continue
        v = num(df[c])
        neg, zero, nan = int((v < 0).sum()), int((v == 0).sum()), int(v.isna().sum())
        if neg:
            add(name, "BLOCK", f"{c}: {neg} valeur(s) négative(s)")
        if zero:
            add(name, "INFO", f"{c}: {zero} valeur(s) nulle(s) (=0)")
        if nan:
            add(name, "BLOCK", f"{c}: {nan} valeur(s) non numérique(s)/NaN")
        if not (neg or zero or nan):
            print(f"  [OK      ] {c}: numérique, positif, sans trou")


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    accounts = mapping.xml_to_dataframe()
    positions = load_positions_raw()
    transactions = load_transactions_raw()
    invoices = load_invoices_raw()

    # ---- ACCOUNTS ----
    section("COMPTES (client_accounts.xml)")
    check_duplicates("accounts", accounts, ["account_id"])
    check_nulls("accounts", accounts)
    check_dates("accounts", accounts, ["opened_date"])

    # ---- POSITIONS ----
    section("POSITIONS (positions_snapshot_monthly_.csv)")
    check_duplicates("positions", positions,
                     ["snapshot_date", "account_id", "instrument_id"])
    check_nulls("positions", positions)
    check_dates("positions", positions, ["snapshot_date"])
    check_currencies("positions", positions, ["position_currency"], EXPECTED_CURRENCIES)
    check_numeric("positions", positions,
                  ["quantity", "price_local", "fx_to_eur", "market_value_eur"])

    # ---- TRANSACTIONS ----
    section("TRANSACTIONS (transactions_history.csv)")
    check_duplicates("transactions", transactions, [])  # pas de clé naturelle unique
    check_nulls("transactions", transactions)
    check_dates("transactions", transactions, ["transaction_date"])
    check_currencies("transactions", transactions, ["position_currency"], EXPECTED_CURRENCIES)
    check_numeric("transactions", transactions, ["quantity", "price"])
    bad_type = set(transactions["transaction_type"].dropna().unique()) - {"BUY", "SELL"}
    if bad_type:
        add("transactions", "BLOCK", f"transaction_type inattendu: {bad_type}")
    else:
        print("  [OK      ] transaction_type dans {BUY, SELL}")

    # ---- INVOICES ----
    section("FACTURES (custody_invoices.csv)")
    check_duplicates("invoices", invoices, ["invoice_id"])
    check_nulls("invoices", invoices, expected_optional=["paid_date"])
    check_dates("invoices", invoices, ["invoice_period", "paid_date"])
    check_currencies("invoices", invoices, ["invoice_currency"], EXPECTED_CURRENCIES)
    check_numeric("invoices", invoices,
                  ["taxable_base_eur", "custody_fee_eur", "market_fee_eur",
                   "vat_eur", "total_invoice_eur"])
    status = set(invoices["invoice_status"].dropna().unique())
    add("invoices", "INFO", f"invoice_status observés: {sorted(status)}")
    # cohérence statut / paid_date
    paid_no_date = ((invoices.invoice_status == "PAID") & invoices.paid_date.isna()).sum()
    if paid_no_date:
        add("invoices", "BLOCK", f"{paid_no_date} facture(s) PAID sans paid_date")
    else:
        print("  [OK      ] toute facture PAID possède une paid_date")

    # ---- COHÉRENCE INTER-FICHIERS ----
    section("COHÉRENCE RÉFÉRENTIELLE (identifiants entre fichiers)")
    acc_ids = set(accounts.account_id.dropna())
    for name, df in [("positions", positions), ("transactions", transactions),
                     ("invoices", invoices)]:
        orphans = set(df.account_id.dropna()) - acc_ids
        if orphans:
            add(name, "BLOCK",
                f"{len(orphans)} account_id présent(s) dans {name} mais absent(s) "
                f"de accounts -> ex {list(orphans)[:5]}")
        else:
            print(f"  [OK      ] tous les account_id de {name} existent dans accounts")

    # cohérence instrument (isin/ticker stables par instrument_id)
    for name, df in [("positions", positions), ("transactions", transactions)]:
        multi_isin = df.groupby("instrument_id").isin.nunique()
        bad = multi_isin[multi_isin > 1]
        if len(bad):
            add(name, "BLOCK",
                f"{len(bad)} instrument_id avec plusieurs ISIN -> {list(bad.index)[:5]}")
        else:
            print(f"  [OK      ] {name}: 1 ISIN unique par instrument_id")

    # ---- RÉSUMÉ ----
    section("RÉSUMÉ")
    blocks = [f for f in findings if f[1] == "BLOCK"]
    infos = [f for f in findings if f[1] == "INFO"]
    print(f"Anomalies BLOQUANTES : {len(blocks)}")
    for fichier, _, msg in blocks:
        print(f"   - [{fichier}] {msg}")
    print(f"\nPoints INFO (légitimes / à documenter) : {len(infos)}")
    for fichier, _, msg in infos:
        print(f"   - [{fichier}] {msg}")

    # export
    rep = pd.DataFrame(findings, columns=["fichier", "niveau", "message"])
    out = BUILD_DIR / "quality_report.csv"
    rep.to_csv(out, index=False, encoding="utf-8")
    print(f"\nRapport exporté : {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
