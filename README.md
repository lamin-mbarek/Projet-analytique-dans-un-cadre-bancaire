# Projet — Intégration des données (CrédiSol SAS)

Projet analytique dans un cadre bancaire réalisé dans le cadre de l'atelier
**« Intégration des données »** (EPSI). L'objectif est de construire une base de
données **homogène** à partir de plusieurs sources hétérogènes, de veiller à la
**qualité de la donnée**, de mener des **analyses SQL** et de réaliser des
**tableaux de bord interactifs**.

> Contexte métier : vous êtes recruté·e au sein de la banque privée **CrédiSol SAS**
> pour fusionner les données de deux branches, remplacer les rapports financiers
> réguliers par des dashboards interactifs, et étudier la facturation des
> *Custodians* (dépositaires) par client et par marché.

---

## 🎯 Objectifs métier

1. **Fusion** des données provenant de deux branches de la banque.
2. **Reporting financier** : remplacer les rapports statiques par des dashboards interactifs.
3. **Facturation** : analyser la facturation des Custodians auprès des clients et par
   marché, pour la détention des instruments financiers (actions, obligations, fonds…).

---

## 📂 Structure du dépôt

```
projet Database/
├── Données/
│   ├── client_accounts.xml            # Comptes clients (source XML)
│   ├── positions_snapshot_monthly_.csv# Instruments détenus (photos mensuelles)
│   ├── transactions_history.csv       # Transactions journalières
│   └── custody_invoices.csv           # Factures des Custodians par instrument
├── Epsi - Sujet principal - Atelier Intégration données.pdf
└── README.md
```

---

## 🗃️ Description des sources de données

### 1. `client_accounts.xml` — Comptes clients (~183 comptes)
Fichier XML décrivant chaque compte client.

| Champ | Description |
|---|---|
| `account_id` | Identifiant du compte (ex. `ACCT00001`) |
| `client_id` | Identifiant du client (ex. `CL00036`) |
| `client_name` | Nom du client |
| `client_segment` | Segment (ex. HNW – *High Net Worth*) |
| `client_country` / `tax_jurisdiction` / `residence_region` | Pays, juridiction fiscale, région |
| `source_branch` / `booking_center` | Branche d'origine, centre de booking |
| `risk_profile` | Profil de risque (Conservative, Balanced…) |
| `primary_custodian` | Dépositaire principal |
| `opened_date` | Date d'ouverture du compte |
| `migration_wave` | Vague de migration (Wave 1…4) |
| `account_status` | Statut (active / inactive) |

### 2. `positions_snapshot_monthly_.csv` — Positions (~13 476 lignes)
Photo mensuelle des instruments détenus par compte.

`snapshot_date, account_id, instrument_id, ticker, isin, instrument_type,
market_code, position_currency, quantity, price_local, fx_to_eur,
market_value_eur, custodian`

### 3. `transactions_history.csv` — Transactions (~13 804 lignes)
Historique des transactions journalières.

`transaction_date, account_id, instrument_id, ticker, isin, transaction_type
(BUY/SELL), quantity, price, position_currency`

### 4. `custody_invoices.csv` — Factures Custodians (~4 032 lignes)
Factures payées aux dépositaires par instrument / marché.

`invoice_id, invoice_period, account_id, market_code, custodian,
invoice_currency, taxable_base_eur, withholding_tax_eur, custody_fee_eur,
market_fee_eur, stamp_duty_eur, vat_eur, total_invoice_eur, invoice_status
(PAID/ISSUED), paid_date, late_payment_flag`

---

## 🧩 Livrables attendus

### II. Modélisation (MCD / MLD / UML)
- Modèle Conceptuel de Données (MCD) puis Modèle Logique (MLD).
- Diagramme UML de la conception optimale.
- Passage aux **1ʳᵉ, 2ᵉ et 3ᵉ formes normales**.

### III. Qualité de la donnée
- Relevé des erreurs de qualité (doublons, valeurs manquantes, incohérences de
  devises/dates, formats hétérogènes…).
- Ajustements nécessaires pour respecter le MCD/MLD.

### IV. Homogénéisation & base de données
- Rédaction d'un **XSD** validant le fichier XML.
- **Mapping** XML → tables (CSV) — étude de faisabilité (outil ETL ou langage adéquat).
- Homogénéisation des différentes sources.
- Alimentation d'une **base de données relationnelle locale**.

### V. Analyses SQL
- Classement des clients par avoirs.
- Client avec le **minimum** d'avoirs.
- Écart en **M€** entre le client le plus riche et le moins doté.
- Clients (les plus dotés) représentant **50 %** du total des avoirs.
- Montant **cumulatif** des transactions.
- Pourcentage d'avancement **mensuel** du nombre de transactions.

### VI. Dashboards interactifs (minimum 3)
- **A. Migration** : suivi de l'avancement, comptes/ marchés à traiter en urgence.
- **B. Financier** (équipe Paiements) : opportunités sur l'évolution des instruments.
- **C. Facturation** (équipe Tax) : facturation par Custodian, clients en retard de
  paiement, réduction des frais.

---

## 🚀 Démarrage rapide

1. **Explorer les données** dans le dossier `Données/`.
2. **Modéliser** le MCD/MLD (ex. outil de modélisation ou papier → normalisation 3NF).
3. **Charger** dans une base relationnelle locale (SQLite / PostgreSQL / MySQL).
   Exemple avec SQLite :
   ```bash
   sqlite3 credisol.db
   # puis .import --csv Données/transactions_history.csv transactions
   ```
4. **Nettoyer / homogénéiser** (Python + pandas, ou un outil ETL type Talend / Power Query).
5. **Analyser** via SQL puis **visualiser** (Power BI, Tableau, ou Streamlit).

### Exemple de chargement Python (pandas)
```python
import pandas as pd, xml.etree.ElementTree as ET

positions = pd.read_csv("Données/positions_snapshot_monthly_.csv")
transactions = pd.read_csv("Données/transactions_history.csv")
invoices = pd.read_csv("Données/custody_invoices.csv")

root = ET.parse("Données/client_accounts.xml").getroot()
accounts = pd.DataFrame([{c.tag: c.text for c in acc} for acc in root])
```

---

## 🛠️ Outils suggérés
- **Modélisation** : Looping, JMerise, draw.io, PowerAMC.
- **ETL / nettoyage** : Python (pandas), Talend, Power Query.
- **Base de données** : SQLite, PostgreSQL ou MySQL.
- **Dashboards** : Power BI, Tableau, Metabase ou Streamlit.

---

## 📝 Notes
- Clé d'intégration commune : **`account_id`** (relie comptes, positions, transactions
  et factures), et **`instrument_id` / `isin`** pour les instruments.
- Attention aux devises : les montants doivent être convertis en EUR (`fx_to_eur`,
  `market_value_eur`) pour les analyses d'avoirs.
- ⚠️ *Consigne du sujet : l'utilisation excessive de solutions IA est pénalisée.*

---

*Module : Intégration des données — EPSI. Banque privée fictive : CrédiSol SAS.*
