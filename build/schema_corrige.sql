-- =====================================================================
--  CrédiSol SAS — Schéma corrigé (basé sur ton modèle Looping)
--  Corrections : types (DECIMAL/DATE/VARCHAR), market_code en texte,
--  fautes de frappe, longueurs, + identifiants métier UNIQUE (traçabilité).
--
--  Types donnés en SQL standard / SQLite. Équivalences Looping/Access :
--     COUNTER  -> INTEGER ... AUTOINCREMENT (SQLite) / AUTO_INCREMENT (MySQL)
--     LOGICAL  -> INTEGER (0/1)  [SQLite n'a pas de type booléen]
--     DECIMAL(18,x) = NUMERIC pour les calculs financiers
-- =====================================================================

-- ============== DIMENSIONS DE RÉFÉRENCE ==============
CREATE TABLE Client(
   id_client          INTEGER PRIMARY KEY AUTOINCREMENT,
   client_id          VARCHAR(10) NOT NULL UNIQUE,   -- identifiant métier (CL00036)
   client_name        VARCHAR(50) NOT NULL,
   client_segment     VARCHAR(30) NOT NULL,
   client_country     VARCHAR(30) NOT NULL,
   tax_jurisdiction   VARCHAR(30) NOT NULL,           -- (corrigé: juridiction)
   residence_region   VARCHAR(30) NOT NULL
);

CREATE TABLE Custodian(
   id_custodian       INTEGER PRIMARY KEY AUTOINCREMENT,
   custodian_name     VARCHAR(50) NOT NULL UNIQUE     -- 31 car. max -> VARCHAR(50)
);

CREATE TABLE Market(
   market_code        VARCHAR(10) PRIMARY KEY         -- XAMS, XETR... (corrigé: était INT)
);

-- ============== ENTITÉS ==============
CREATE TABLE Account(
   id_account         INTEGER PRIMARY KEY AUTOINCREMENT,
   account_id         VARCHAR(12) NOT NULL UNIQUE,    -- identifiant métier (ACCT00001)
   source_branch      VARCHAR(50) NOT NULL,
   booking_center     VARCHAR(50) NOT NULL,
   risk_profile       VARCHAR(50) NOT NULL,
   opened_date        DATE NOT NULL,                  -- (corrigé: était VARCHAR)
   migration_wave     VARCHAR(50) NOT NULL,
   account_status     VARCHAR(50) NOT NULL,
   id_custodian       INTEGER NOT NULL,
   id_client          INTEGER NOT NULL,
   FOREIGN KEY(id_custodian) REFERENCES Custodian(id_custodian),
   FOREIGN KEY(id_client)    REFERENCES Client(id_client)
);

CREATE TABLE Instrument(
   id_instrument      INTEGER PRIMARY KEY AUTOINCREMENT,
   instrument_id      VARCHAR(12) NOT NULL UNIQUE,    -- identifiant métier (INS001)
   ticker             VARCHAR(50) NOT NULL,
   isin               VARCHAR(12) NOT NULL UNIQUE,    -- ISIN = clé naturelle
   instrument_type    VARCHAR(50) NOT NULL,
   native_currency    VARCHAR(3)  NOT NULL,           -- (corrigé: mative->native ; devise 1:1 avec l'instrument)
   market_code        VARCHAR(10) NOT NULL,           -- (corrigé: INT->VARCHAR)
   FOREIGN KEY(market_code) REFERENCES Market(market_code)
);

CREATE TABLE Invoice(
   id_invoice          INTEGER PRIMARY KEY AUTOINCREMENT,
   invoice_id          VARCHAR(12) NOT NULL UNIQUE,   -- identifiant métier (INV0000001)
   invoice_period      DATE NOT NULL,                 -- (corrigé: était VARCHAR)
   invoice_currency    VARCHAR(3)  NOT NULL,
   taxable_base_eur    DECIMAL(18,4),                 -- (corrigé: VARCHAR->DECIMAL)
   withholding_tax_eur DECIMAL(18,4),                 -- (corrigé: tex->tax)
   custody_fee_eur     DECIMAL(18,4),
   market_fee_eur      DECIMAL(18,4),
   stamp_duty_eur      DECIMAL(18,4),
   vat_eur             DECIMAL(18,4),
   total_invoice_eur   DECIMAL(18,4),
   invoice_status      VARCHAR(20) NOT NULL,          -- PAID / ISSUED / OVERDUE
   paid_date           DATE,                          -- NULL si non payée (légitime)
   late_payment_flag   INTEGER,                       -- (corrigé: payement->payment ; 0/1)
   id_account          INTEGER NOT NULL,
   market_code         VARCHAR(10) NOT NULL,          -- (corrigé: INT->VARCHAR)
   FOREIGN KEY(id_account)  REFERENCES Account(id_account),
   FOREIGN KEY(market_code) REFERENCES Market(market_code)
);

CREATE TABLE Transaction_(                             -- underscore : "Transaction" est un mot réservé SQL
   id_transaction     INTEGER PRIMARY KEY AUTOINCREMENT,
   transaction_date   DATE NOT NULL,
   transaction_type   VARCHAR(10) NOT NULL,           -- BUY / SELL
   quantity           INTEGER NOT NULL,               -- (corrigé: VARCHAR->INTEGER)
   price              DECIMAL(18,6) NOT NULL,          -- (corrigé: VARCHAR->DECIMAL)
   id_instrument      INTEGER NOT NULL,
   id_account         INTEGER NOT NULL,
   FOREIGN KEY(id_instrument) REFERENCES Instrument(id_instrument),
   FOREIGN KEY(id_account)    REFERENCES Account(id_account)
);

CREATE TABLE Position_(
   id_position        INTEGER PRIMARY KEY AUTOINCREMENT,
   snapshot_date      DATE NOT NULL,                  -- (corrigé: était VARCHAR)
   quantity           INTEGER NOT NULL,               -- (corrigé: VARCHAR->INTEGER)
   price_local        DECIMAL(18,6) NOT NULL,          -- (corrigé: VARCHAR->DECIMAL)
   fx_to_eur          DECIMAL(18,6) NOT NULL,          -- (corrigé: VARCHAR->DECIMAL)
   market_value_eur   DECIMAL(18,4) NOT NULL,          -- (corrigé: marlet->market ; VARCHAR->DECIMAL)
   id_instrument      INTEGER NOT NULL,
   id_account         INTEGER NOT NULL,
   FOREIGN KEY(id_instrument) REFERENCES Instrument(id_instrument),
   FOREIGN KEY(id_account)    REFERENCES Account(id_account)
);
