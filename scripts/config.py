"""
Configuration commune à tous les scripts du pipeline CrédiSol.

Centralise les chemins pour éviter les surprises (le dossier de données
réel s'appelle « Données/ » et le fichier positions porte un underscore final).
"""
from pathlib import Path

# Racine du projet = dossier parent de scripts/
ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "Données"
BUILD_DIR = ROOT / "build"          # sorties intermédiaires (xsd, csv nettoyés, logs)
BUILD_DIR.mkdir(exist_ok=True)

# Fichiers sources
XML_ACCOUNTS = DATA_DIR / "client_accounts.xml"
CSV_POSITIONS = DATA_DIR / "positions_snapshot_monthly_.csv"
CSV_TRANSACTIONS = DATA_DIR / "transactions_history.csv"
CSV_INVOICES = DATA_DIR / "custody_invoices.csv"

# Sorties
XSD_PATH = BUILD_DIR / "client_accounts.xsd"
SQLITE_DB = ROOT / "credisol.db"

# Ordre des colonnes attendu pour la table plate des comptes
ACCOUNT_COLUMNS = [
    "account_id", "client_id", "client_name", "client_segment",
    "client_country", "tax_jurisdiction", "residence_region",
    "source_branch", "booking_center", "risk_profile",
    "primary_custodian", "opened_date", "migration_wave", "account_status",
]
