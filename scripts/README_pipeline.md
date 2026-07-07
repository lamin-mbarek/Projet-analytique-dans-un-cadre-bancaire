# Pipeline d'intégration des données — CrédiSol SAS

Chaîne Python (pandas + lxml + xmlschema) qui transforme les 4 fichiers sources
en une base **SQLite normalisée (3NF)** `credisol.db`, avec contrôle qualité,
validation XSD et vérifications d'intégrité.

## Installation

```bash
pip install -r requirements.txt
```

## Exécution

Tout le pipeline en une commande :

```bash
python run_all.py
```

…ou étape par étape (les scripts s'exécutent depuis le dossier `scripts/`) :

| Script | Étape(s) du sujet | Rôle |
|---|---|---|
| `01_inspect_xml.py` | 1 | Inspecte la structure réelle du XML (balises, imbrication, champs optionnels, cardinalités / candidats enum) |
| `02_generate_xsd.py` | 2 | Génère `build/client_accounts.xsd` **à partir des données réelles** (dates, enums, patterns d'ID, obligatoires) |
| `03_mapping.py` | 3, 4 | Valide le XML contre le XSD (log des erreurs) puis mappe le XML vers une table plate pandas |
| `04_quality_report.py` | 5 | Rapport qualité par fichier : doublons, nulls, formats, valeurs aberrantes, cohérence des identifiants inter-fichiers |
| `05_load_db.py` | 6, 7, 8, 9 | Homogénéise, crée le schéma 3NF, charge dans l'ordre des dépendances, puis vérifie (COUNT + FK orphelines) |

Modules partagés : `config.py` (chemins), `loaders.py` (lecture CSV brute),
`homogenize.py` (nettoyage typé et documenté).

Sorties : dossier `build/` (XSD, table plate, rapport qualité, logs) et
`credisol.db` à la racine du projet.

## Principaux constats qualité (données réelles)

- **BLOQUANT — 3 comptes strictement dupliqués** (`ACCT00019`, `ACCT00137`,
  `ACCT00164`) : `account_id` n'a que 180 valeurs distinctes pour 183 lignes.
  → déduplication (180 comptes uniques conservés).
- **INFO — 772 `paid_date` manquantes** : factures `ISSUED`/`OVERDUE` non encore
  payées → conservées en `NULL` (pas de suppression).
- **INFO — `vat_eur = 0`** sur 672 factures : TVA nulle légitime.
- **INFO — statut `OVERDUE`** présent en plus de `PAID`/`ISSUED`.
- Aucun account_id orphelin, aucune date non ISO, aucune quantité/prix
  négatif, `instrument_id` ↔ `isin`/`ticker` cohérents (1:1).

## Schéma 3NF (`credisol.db`)

Chaque table possède une **PK technique auto-incrémentée** *et* conserve
l'**identifiant métier source en colonne UNIQUE** (traçabilité vers les fichiers).

```
Client(client_pk, client_id*, nom, segment, pays, juridiction, région)
Custodian(custodian_pk, custodian_name*)
Market(market_pk, market_code*)
Account(account_pk, account_id*, →Client, branche, booking, risque, →Custodian, opened_date, wave, statut)
Instrument(instrument_pk, instrument_id*, ticker, isin*, type, →Market)
Invoice(invoice_pk, invoice_id*, →Account, →Market, →Custodian, période, montants…, statut, paid_date, flag)
Transactions(transaction_pk, →Account, →Instrument, date, type, quantité, prix, devise)
Positions(position_pk, snapshot_date, →Account, →Instrument, →Custodian, devise, quantité, prix_local, fx, valeur_eur)

(*) = identifiant métier d'origine, contrainte UNIQUE
```

Ordre de chargement respectant les FK :
`Client, Custodian, Market → Account, Instrument → Invoice, Transactions, Positions`.

## Résultat des vérifications

| Table | Lignes |
|---|---|
| Client | 89 |
| Custodian | 5 |
| Market | 5 |
| Account | 180 |
| Instrument | 12 |
| Invoice | 4 032 |
| Transactions | 13 804 |
| Positions | 13 476 |

`0` FK orpheline sur les 11 relations, `PRAGMA foreign_key_check` sans violation.
