## 1-Installer les dépendances
pip install -r requirements.txt

 
## 2-Générer la base de données
python etl\etl_credisol.py

## 3-Lancer les analyses SQL (résultats dans out.txt)
sqlite3 etl\credisol.db ".read analyse.sql" > out.txt

## 4-Lancer les dashboards
streamlit run dashboards\app.py
