"""
05 — Création de la base SQLite 3NF, chargement et vérifications.

Étapes 7, 8, 9 du cahier des charges :
  7. Schéma normalisé (3NF) : PK techniques auto-incrémentées + identifiants
     métier d'origine conservés en colonnes UNIQUE (traçabilité vers les sources).
  8. Chargement dans l'ordre des dépendances (dimensions d'abord).
  9. Requêtes de contrôle : COUNT par table + recherche de FK orphelines.

Modèle relationnel :
  Client(1)---(N)Account(1)---(N){Invoice, Transactions, Positions}
  Custodian, Market : dimensions de référence
  Instrument(1)---(N){Transactions, Positions}, Instrument(N)--(1)Market
"""
import sqlite3
import sys

from config import SQLITE_DB
from homogenize import homogenize_all

SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS Positions;
DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Invoice;
DROP TABLE IF EXISTS Instrument;
DROP TABLE IF EXISTS Account;
DROP TABLE IF EXISTS Market;
DROP TABLE IF EXISTS Custodian;
DROP TABLE IF EXISTS Client;

-- ================= DIMENSIONS DE RÉFÉRENCE =================
CREATE TABLE Client (
    client_pk          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id          TEXT NOT NULL UNIQUE,          -- identifiant métier source
    client_name        TEXT NOT NULL,
    client_segment     TEXT NOT NULL,
    client_country     TEXT NOT NULL,
    tax_jurisdiction   TEXT NOT NULL,
    residence_region   TEXT NOT NULL
);

CREATE TABLE Custodian (
    custodian_pk       INTEGER PRIMARY KEY AUTOINCREMENT,
    custodian_name     TEXT NOT NULL UNIQUE
);

CREATE TABLE Market (
    market_pk          INTEGER PRIMARY KEY AUTOINCREMENT,
    market_code        TEXT NOT NULL UNIQUE
);

-- ================= ENTITÉS =================
CREATE TABLE Account (
    account_pk         INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id         TEXT NOT NULL UNIQUE,          -- identifiant métier source
    client_pk          INTEGER NOT NULL,
    source_branch      TEXT NOT NULL,
    booking_center     TEXT NOT NULL,
    risk_profile       TEXT NOT NULL,
    custodian_pk       INTEGER NOT NULL,              -- custodian principal
    opened_date        TEXT NOT NULL,
    migration_wave     TEXT NOT NULL,
    account_status     TEXT NOT NULL,
    FOREIGN KEY (client_pk)    REFERENCES Client(client_pk),
    FOREIGN KEY (custodian_pk) REFERENCES Custodian(custodian_pk)
);

CREATE TABLE Instrument (
    instrument_pk      INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id      TEXT NOT NULL UNIQUE,          -- identifiant métier source
    ticker             TEXT NOT NULL,
    isin               TEXT NOT NULL UNIQUE,
    instrument_type    TEXT NOT NULL,
    market_pk          INTEGER NOT NULL,
    FOREIGN KEY (market_pk) REFERENCES Market(market_pk)
);

CREATE TABLE Invoice (
    invoice_pk          INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id          TEXT NOT NULL UNIQUE,         -- identifiant métier source
    account_pk          INTEGER NOT NULL,
    market_pk           INTEGER NOT NULL,
    custodian_pk        INTEGER NOT NULL,
    invoice_period      TEXT NOT NULL,
    invoice_currency    TEXT NOT NULL,
    taxable_base_eur    REAL,
    withholding_tax_eur REAL,
    custody_fee_eur     REAL,
    market_fee_eur      REAL,
    stamp_duty_eur      REAL,
    vat_eur             REAL,
    total_invoice_eur   REAL,
    invoice_status      TEXT NOT NULL,
    paid_date           TEXT,                          -- NULL si non payée
    late_payment_flag   INTEGER,
    FOREIGN KEY (account_pk)   REFERENCES Account(account_pk),
    FOREIGN KEY (market_pk)    REFERENCES Market(market_pk),
    FOREIGN KEY (custodian_pk) REFERENCES Custodian(custodian_pk)
);

CREATE TABLE Transactions (
    transaction_pk      INTEGER PRIMARY KEY AUTOINCREMENT,
    account_pk          INTEGER NOT NULL,
    instrument_pk       INTEGER NOT NULL,
    transaction_date    TEXT NOT NULL,
    transaction_type    TEXT NOT NULL,
    quantity            INTEGER NOT NULL,
    price               REAL NOT NULL,
    position_currency   TEXT NOT NULL,
    FOREIGN KEY (account_pk)    REFERENCES Account(account_pk),
    FOREIGN KEY (instrument_pk) REFERENCES Instrument(instrument_pk)
);

CREATE TABLE Positions (
    position_pk         INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date       TEXT NOT NULL,
    account_pk          INTEGER NOT NULL,
    instrument_pk       INTEGER NOT NULL,
    custodian_pk        INTEGER NOT NULL,
    position_currency   TEXT NOT NULL,
    quantity            INTEGER NOT NULL,
    price_local         REAL NOT NULL,
    fx_to_eur           REAL NOT NULL,
    market_value_eur    REAL NOT NULL,
    FOREIGN KEY (account_pk)    REFERENCES Account(account_pk),
    FOREIGN KEY (instrument_pk) REFERENCES Instrument(instrument_pk),
    FOREIGN KEY (custodian_pk)  REFERENCES Custodian(custodian_pk)
);
"""


def d(v):
    """Normalise une valeur (NA/NaT -> None) pour sqlite3."""
    import pandas as pd
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if hasattr(v, "isoformat"):          # date/datetime
        return v.isoformat()
    if hasattr(v, "item"):               # scalaire numpy (int64/float64) -> type Python natif
        return v.item()                  # sinon sqlite stocke un BLOB au lieu d'un entier
    return v


def build_dimensions(conn, data):
    """Insère Client, Custodian, Market et renvoie les maps id_métier -> pk."""
    acc = data["accounts"]
    pos = data["positions"]
    inv = data["invoices"]
    cur = conn.cursor()

    # --- Client (dédupliqué sur client_id, attributs FD-cohérents) ---
    clients = (acc[["client_id", "client_name", "client_segment", "client_country",
                    "tax_jurisdiction", "residence_region"]]
               .drop_duplicates("client_id").sort_values("client_id"))
    cur.executemany(
        "INSERT INTO Client(client_id,client_name,client_segment,client_country,"
        "tax_jurisdiction,residence_region) VALUES (?,?,?,?,?,?)",
        [tuple(d(x) for x in r) for r in clients.itertuples(index=False)])

    # --- Custodian (union de toutes les sources) ---
    custodians = sorted(set(acc.primary_custodian) | set(pos.custodian) | set(inv.custodian))
    cur.executemany("INSERT INTO Custodian(custodian_name) VALUES (?)",
                    [(c,) for c in custodians])

    # --- Market (union positions + invoices) ---
    markets = sorted(set(pos.market_code) | set(inv.market_code))
    cur.executemany("INSERT INTO Market(market_code) VALUES (?)",
                    [(m,) for m in markets])
    conn.commit()

    client_map = dict(cur.execute("SELECT client_id, client_pk FROM Client").fetchall())
    cust_map = dict(cur.execute("SELECT custodian_name, custodian_pk FROM Custodian").fetchall())
    market_map = dict(cur.execute("SELECT market_code, market_pk FROM Market").fetchall())
    return client_map, cust_map, market_map


def build_entities(conn, data, client_map, cust_map, market_map):
    acc, pos, tx, inv = (data["accounts"], data["positions"],
                         data["transactions"], data["invoices"])
    cur = conn.cursor()

    # --- Account ---
    cur.executemany(
        "INSERT INTO Account(account_id,client_pk,source_branch,booking_center,"
        "risk_profile,custodian_pk,opened_date,migration_wave,account_status) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [(r.account_id, client_map[r.client_id], r.source_branch, r.booking_center,
          r.risk_profile, cust_map[r.primary_custodian], d(r.opened_date),
          r.migration_wave, r.account_status) for r in acc.itertuples(index=False)])

    # --- Instrument (dimension construite depuis les positions : isin/ticker/type/market
    #     1:1 par instrument_id, vérifié en amont) ---
    instr = (pos[["instrument_id", "ticker", "isin", "instrument_type", "market_code"]]
             .drop_duplicates("instrument_id").sort_values("instrument_id"))
    cur.executemany(
        "INSERT INTO Instrument(instrument_id,ticker,isin,instrument_type,market_pk) "
        "VALUES (?,?,?,?,?)",
        [(r.instrument_id, r.ticker, r.isin, r.instrument_type, market_map[r.market_code])
         for r in instr.itertuples(index=False)])
    conn.commit()

    account_map = dict(cur.execute("SELECT account_id, account_pk FROM Account").fetchall())
    instr_map = dict(cur.execute("SELECT instrument_id, instrument_pk FROM Instrument").fetchall())

    # --- Invoice ---
    cur.executemany(
        "INSERT INTO Invoice(invoice_id,account_pk,market_pk,custodian_pk,invoice_period,"
        "invoice_currency,taxable_base_eur,withholding_tax_eur,custody_fee_eur,market_fee_eur,"
        "stamp_duty_eur,vat_eur,total_invoice_eur,invoice_status,paid_date,late_payment_flag) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(r.invoice_id, account_map[r.account_id], market_map[r.market_code],
          cust_map[r.custodian], d(r.invoice_period), r.invoice_currency,
          d(r.taxable_base_eur), d(r.withholding_tax_eur), d(r.custody_fee_eur),
          d(r.market_fee_eur), d(r.stamp_duty_eur), d(r.vat_eur), d(r.total_invoice_eur),
          r.invoice_status, d(r.paid_date), d(r.late_payment_flag))
         for r in inv.itertuples(index=False)])

    # --- Transactions ---
    cur.executemany(
        "INSERT INTO Transactions(account_pk,instrument_pk,transaction_date,"
        "transaction_type,quantity,price,position_currency) VALUES (?,?,?,?,?,?,?)",
        [(account_map[r.account_id], instr_map[r.instrument_id], d(r.transaction_date),
          r.transaction_type, d(r.quantity), d(r.price), r.position_currency)
         for r in tx.itertuples(index=False)])

    # --- Positions ---
    cur.executemany(
        "INSERT INTO Positions(snapshot_date,account_pk,instrument_pk,custodian_pk,"
        "position_currency,quantity,price_local,fx_to_eur,market_value_eur) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [(d(r.snapshot_date), account_map[r.account_id], instr_map[r.instrument_id],
          cust_map[r.custodian], r.position_currency, d(r.quantity), d(r.price_local),
          d(r.fx_to_eur), d(r.market_value_eur)) for r in pos.itertuples(index=False)])
    conn.commit()


def verify(conn):
    cur = conn.cursor()
    print("\n" + "=" * 70)
    print("VÉRIFICATIONS (étape 9)")
    print("=" * 70)

    print("\n-- COUNT par table --")
    tables = ["Client", "Custodian", "Market", "Account", "Instrument",
              "Invoice", "Transactions", "Positions"]
    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<14} : {n:>7}")

    print("\n-- FK orphelines (doit être 0 partout) --")
    checks = [
        ("Account.client_pk -> Client",
         "SELECT COUNT(*) FROM Account a LEFT JOIN Client c ON a.client_pk=c.client_pk WHERE c.client_pk IS NULL"),
        ("Account.custodian_pk -> Custodian",
         "SELECT COUNT(*) FROM Account a LEFT JOIN Custodian c ON a.custodian_pk=c.custodian_pk WHERE c.custodian_pk IS NULL"),
        ("Instrument.market_pk -> Market",
         "SELECT COUNT(*) FROM Instrument i LEFT JOIN Market m ON i.market_pk=m.market_pk WHERE m.market_pk IS NULL"),
        ("Invoice.account_pk -> Account",
         "SELECT COUNT(*) FROM Invoice v LEFT JOIN Account a ON v.account_pk=a.account_pk WHERE a.account_pk IS NULL"),
        ("Invoice.market_pk -> Market",
         "SELECT COUNT(*) FROM Invoice v LEFT JOIN Market m ON v.market_pk=m.market_pk WHERE m.market_pk IS NULL"),
        ("Invoice.custodian_pk -> Custodian",
         "SELECT COUNT(*) FROM Invoice v LEFT JOIN Custodian c ON v.custodian_pk=c.custodian_pk WHERE c.custodian_pk IS NULL"),
        ("Transactions.account_pk -> Account",
         "SELECT COUNT(*) FROM Transactions t LEFT JOIN Account a ON t.account_pk=a.account_pk WHERE a.account_pk IS NULL"),
        ("Transactions.instrument_pk -> Instrument",
         "SELECT COUNT(*) FROM Transactions t LEFT JOIN Instrument i ON t.instrument_pk=i.instrument_pk WHERE i.instrument_pk IS NULL"),
        ("Positions.account_pk -> Account",
         "SELECT COUNT(*) FROM Positions p LEFT JOIN Account a ON p.account_pk=a.account_pk WHERE a.account_pk IS NULL"),
        ("Positions.instrument_pk -> Instrument",
         "SELECT COUNT(*) FROM Positions p LEFT JOIN Instrument i ON p.instrument_pk=i.instrument_pk WHERE i.instrument_pk IS NULL"),
        ("Positions.custodian_pk -> Custodian",
         "SELECT COUNT(*) FROM Positions p LEFT JOIN Custodian c ON p.custodian_pk=c.custodian_pk WHERE c.custodian_pk IS NULL"),
    ]
    all_ok = True
    for label, q in checks:
        n = cur.execute(q).fetchone()[0]
        flag = "OK" if n == 0 else "!! ORPHELINES"
        if n:
            all_ok = False
        print(f"  [{flag:>13}] {label:<40} : {n}")

    # PRAGMA integrité FK global
    fk = cur.execute("PRAGMA foreign_key_check").fetchall()
    print(f"\n  PRAGMA foreign_key_check : {'aucune violation' if not fk else fk}")
    print("\n" + ("TOUTES LES VERIFICATIONS PASSENT [OK]" if all_ok and not fk
                  else "DES PROBLEMES SUBSISTENT [KO]"))


def main():
    data, notes = homogenize_all()
    print("=== Décisions d'homogénéisation appliquées ===")
    for n in notes:
        print(" -", n)

    if SQLITE_DB.exists():
        SQLITE_DB.unlink()
    conn = sqlite3.connect(SQLITE_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    print(f"\nSchéma 3NF créé dans {SQLITE_DB}")

    client_map, cust_map, market_map = build_dimensions(conn, data)
    print(f"Dimensions chargées : {len(client_map)} clients, "
          f"{len(cust_map)} custodians, {len(market_map)} marchés.")
    build_entities(conn, data, client_map, cust_map, market_map)
    print("Entités chargées : Account, Instrument, Invoice, Transactions, Positions.")

    verify(conn)
    conn.close()
    print(f"\nBase prête : {SQLITE_DB}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
