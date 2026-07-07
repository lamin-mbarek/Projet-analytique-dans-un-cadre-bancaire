"""
Orchestrateur : exécute tout le pipeline dans l'ordre.
 
    python run_all.py 

Enchaîne : inspection XML -> génération XSD -> validation + mapping ->
rapport qualité -> création base + chargement + vérifications.
"""
import runpy
import sys

STEPS = [
    "01_inspect_xml.py",
    "02_generate_xsd.py",
    "03_mapping.py",
    "04_quality_report.py",
    "05_load_db.py",
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for step in STEPS:
        print("\n" + "#" * 70)
        print(f"# {step}")
        print("#" * 70)
        runpy.run_path(step, run_name="__main__")
    print("\nPipeline terminé. Base : credisol.db")


if __name__ == "__main__":
    main()
