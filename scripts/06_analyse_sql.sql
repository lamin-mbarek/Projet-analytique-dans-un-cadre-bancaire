-- =====================================================================
--  CrédiSol SAS — Analyses SQL (partie V du sujet)
--  Base : credisol.db (SQLite)
--
--  Définition métier des « avoirs » d'un client :
--    somme des market_value_eur de ses positions au DERNIER snapshot
--    mensuel disponible (sinon on additionnerait 12 photos du même avoir).
--  Un client pouvant détenir plusieurs comptes, on agrège au niveau client.
-- =====================================================================


-- ---------------------------------------------------------------------
-- a. Classement des clients par avoirs (RANK décroissant)
-- ---------------------------------------------------------------------
WITH avoirs_client AS (
    SELECT cl.client_id,
           cl.client_name,
           SUM(p.market_value_eur) AS avoirs_eur
    FROM Positions p
    JOIN Account a  ON a.account_pk = p.account_pk
    JOIN Client  cl ON cl.client_pk = a.client_pk
    WHERE p.snapshot_date = (SELECT MAX(snapshot_date) FROM Positions)
    GROUP BY cl.client_pk
)
SELECT RANK() OVER (ORDER BY avoirs_eur DESC) AS rang,
       client_id,
       client_name,
       ROUND(avoirs_eur, 2) AS avoirs_eur
FROM avoirs_client
ORDER BY rang;


-- ---------------------------------------------------------------------
-- b. Client avec le MINIMUM d'avoirs
-- ---------------------------------------------------------------------
WITH avoirs_client AS (
    SELECT cl.client_id, cl.client_name, SUM(p.market_value_eur) AS avoirs_eur
    FROM Positions p
    JOIN Account a  ON a.account_pk = p.account_pk
    JOIN Client  cl ON cl.client_pk = a.client_pk
    WHERE p.snapshot_date = (SELECT MAX(snapshot_date) FROM Positions)
    GROUP BY cl.client_pk
)
SELECT client_id, client_name, ROUND(avoirs_eur, 2) AS avoirs_eur
FROM avoirs_client
ORDER BY avoirs_eur ASC
LIMIT 1;


-- ---------------------------------------------------------------------
-- c. Différence en M€ entre le client le plus riche et le moins doté
-- ---------------------------------------------------------------------
WITH avoirs_client AS (
    SELECT cl.client_pk, SUM(p.market_value_eur) AS avoirs_eur
    FROM Positions p
    JOIN Account a  ON a.account_pk = p.account_pk
    JOIN Client  cl ON cl.client_pk = a.client_pk
    WHERE p.snapshot_date = (SELECT MAX(snapshot_date) FROM Positions)
    GROUP BY cl.client_pk
)
SELECT ROUND(MAX(avoirs_eur), 2)                       AS avoir_max_eur,
       ROUND(MIN(avoirs_eur), 2)                       AS avoir_min_eur,
       ROUND((MAX(avoirs_eur) - MIN(avoirs_eur)) / 1e6, 4) AS difference_meur
FROM avoirs_client;


-- ---------------------------------------------------------------------
-- d. Clients les plus dotés représentant 50% du total des avoirs
--    (cumul décroissant jusqu'à atteindre 50% — analyse de Pareto)
-- ---------------------------------------------------------------------
WITH avoirs_client AS (
    SELECT cl.client_id, cl.client_name, SUM(p.market_value_eur) AS avoirs_eur
    FROM Positions p
    JOIN Account a  ON a.account_pk = p.account_pk
    JOIN Client  cl ON cl.client_pk = a.client_pk
    WHERE p.snapshot_date = (SELECT MAX(snapshot_date) FROM Positions)
    GROUP BY cl.client_pk
),
cumul AS (
    SELECT client_id, client_name, avoirs_eur,
           SUM(avoirs_eur) OVER (ORDER BY avoirs_eur DESC
                                 ROWS UNBOUNDED PRECEDING)      AS cumul_eur,
           SUM(avoirs_eur) OVER ()                              AS total_eur
    FROM avoirs_client
)
SELECT client_id, client_name,
       ROUND(avoirs_eur, 2)                       AS avoirs_eur,
       ROUND(100.0 * cumul_eur / total_eur, 2)    AS pct_cumule
FROM cumul
-- on garde les clients tant que le cumul AVANT eux n'a pas dépassé 50%
WHERE cumul_eur - avoirs_eur < 0.5 * total_eur
ORDER BY avoirs_eur DESC;


-- ---------------------------------------------------------------------
-- e. Montant cumulatif des transactions (running total)
--    « réalisées par moi » : filtrable sur un compte via :ACCOUNT_ID.
--    Montant d'une transaction = quantity * price (en devise locale).
--    NB : les transactions sont en EUR/USD/CHF sans taux de change fourni ;
--    le cumul est donc en devise locale (voir note du rapport qualité).
-- ---------------------------------------------------------------------
SELECT t.transaction_date,
       a.account_id,
       i.ticker,
       t.transaction_type,
       t.quantity,
       t.price,
       t.position_currency,
       ROUND(t.quantity * t.price, 2)                                   AS montant,
       ROUND(SUM(t.quantity * t.price) OVER (ORDER BY t.transaction_date,
                                             t.transaction_pk
                                             ROWS UNBOUNDED PRECEDING), 2) AS montant_cumule
FROM Transactions t
JOIN Account    a ON a.account_pk    = t.account_pk
JOIN Instrument i ON i.instrument_pk = t.instrument_pk
-- WHERE a.account_id = 'ACCT00001'     -- <- décommenter pour « mes » transactions
ORDER BY t.transaction_date, t.transaction_pk;


-- ---------------------------------------------------------------------
-- f. Avancement mensuel : % cumulé du nombre de transactions réalisées
-- ---------------------------------------------------------------------
WITH par_mois AS (
    SELECT strftime('%Y-%m', transaction_date) AS mois,
           COUNT(*)                            AS nb_tx
    FROM Transactions
    GROUP BY mois
)
SELECT mois,
       nb_tx,
       SUM(nb_tx) OVER (ORDER BY mois ROWS UNBOUNDED PRECEDING)      AS nb_tx_cumule,
       (SELECT SUM(nb_tx) FROM par_mois)                            AS nb_tx_total,
       ROUND(100.0 * SUM(nb_tx) OVER (ORDER BY mois ROWS UNBOUNDED PRECEDING)
             / (SELECT SUM(nb_tx) FROM par_mois), 2)                AS pct_avancement
FROM par_mois
ORDER BY mois;
