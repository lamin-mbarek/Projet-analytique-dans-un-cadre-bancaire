"""
Chargeurs bruts des CSV (sans nettoyage) — factorisés pour être réutilisés
par le rapport qualité (04) et l'homogénéisation (05).
On lit tout en str/dtype souple pour pouvoir diagnostiquer les formats.
"""
import pandas as pd

from config import CSV_POSITIONS, CSV_TRANSACTIONS, CSV_INVOICES


def load_positions_raw():
    return pd.read_csv(CSV_POSITIONS, dtype=str, keep_default_na=True)


def load_transactions_raw():
    return pd.read_csv(CSV_TRANSACTIONS, dtype=str, keep_default_na=True)


def load_invoices_raw():
    return pd.read_csv(CSV_INVOICES, dtype=str, keep_default_na=True)
