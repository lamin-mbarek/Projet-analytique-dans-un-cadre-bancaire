"""
02 — Génération d'un XSD strict pour client_accounts.xml.

Le schéma est dérivé des DONNÉES RÉELLES (pas de valeurs inventées) :
  - un champ présent sur tous les comptes -> minOccurs=1 (obligatoire) ;
  - un champ à faible cardinalité catégorielle -> xs:enumeration ;
  - opened_date -> xs:date ;
  - les identifiants -> xs:string avec un pattern observé ;
  - l'ordre des balises est imposé via <xs:sequence>.
"""
import sys
from collections import defaultdict

from lxml import etree

from config import XML_ACCOUNTS, XSD_PATH

# Champs que l'on veut traiter comme énumérations catégorielles
# (faible cardinalité + valeurs stables). Les identifiants et le texte
# libre (client_name) en sont volontairement exclus.
ENUM_FIELDS = {
    "client_segment", "client_country", "tax_jurisdiction",
    "residence_region", "source_branch", "booking_center",
    "risk_profile", "primary_custodian", "migration_wave", "account_status",
}
# Champs identifiants -> pattern
ID_PATTERNS = {
    "account_id": r"ACCT\d{5}",
    "client_id": r"CL\d{5}",
}
DATE_FIELDS = {"opened_date"}


def collect():
    root = etree.parse(str(XML_ACCOUNTS)).getroot()
    accounts = root.findall("account")
    n = len(accounts)

    order = []
    present = defaultdict(int)
    values = defaultdict(set)
    for acc in accounts:
        for child in acc:
            if child.tag not in order:
                order.append(child.tag)
            present[child.tag] += 1
            txt = (child.text or "").strip()
            if txt:
                values[child.tag].add(txt)
    return n, order, present, values


def build_xsd(n, order, present, values):
    XS = "http://www.w3.org/2001/XMLSchema"
    nsmap = {"xs": XS}
    schema = etree.Element(f"{{{XS}}}schema", nsmap=nsmap)
    schema.set("elementFormDefault", "qualified")

    # Elément racine <accounts> contenant 1..* <account>
    root_el = etree.SubElement(schema, f"{{{XS}}}element", name="accounts")
    ct = etree.SubElement(root_el, f"{{{XS}}}complexType")
    seq = etree.SubElement(ct, f"{{{XS}}}sequence")
    acc_el = etree.SubElement(seq, f"{{{XS}}}element", name="account",
                              type="accountType", minOccurs="1",
                              maxOccurs="unbounded")

    # Type <accountType>
    acc_type = etree.SubElement(schema, f"{{{XS}}}complexType", name="accountType")
    acc_seq = etree.SubElement(acc_type, f"{{{XS}}}sequence")

    for tag in order:
        required = present[tag] == n
        el = etree.SubElement(acc_seq, f"{{{XS}}}element", name=tag)
        el.set("minOccurs", "1" if required else "0")
        el.set("maxOccurs", "1")

        if tag in DATE_FIELDS:
            el.set("type", "xs:date")
        elif tag in ID_PATTERNS:
            _add_restriction(el, XS, base="xs:string",
                             pattern=ID_PATTERNS[tag])
        elif tag in ENUM_FIELDS:
            _add_restriction(el, XS, base="xs:string",
                             enums=sorted(values[tag]))
        else:
            # texte libre non vide (ex: client_name)
            _add_restriction(el, XS, base="xs:string", min_len=1)

    return schema


def _add_restriction(element, XS, base, enums=None, pattern=None, min_len=None):
    st = etree.SubElement(element, f"{{{XS}}}simpleType")
    rst = etree.SubElement(st, f"{{{XS}}}restriction", base=base)
    if enums:
        for v in enums:
            etree.SubElement(rst, f"{{{XS}}}enumeration", value=v)
    if pattern:
        etree.SubElement(rst, f"{{{XS}}}pattern", value=pattern)
    if min_len is not None:
        etree.SubElement(rst, f"{{{XS}}}minLength", value=str(min_len))


def main():
    n, order, present, values = collect()
    schema = build_xsd(n, order, present, values)
    xml_bytes = etree.tostring(schema, pretty_print=True,
                               xml_declaration=True, encoding="UTF-8")
    XSD_PATH.write_bytes(xml_bytes)

    print(f"XSD généré : {XSD_PATH}")
    print(f"  - {len(order)} champs, tous obligatoires "
          f"(présents sur {n}/{n} comptes)")
    print(f"  - énumérations : {', '.join(sorted(ENUM_FIELDS))}")
    print(f"  - date typée   : {', '.join(DATE_FIELDS)}")
    print(f"  - patterns     : {', '.join(ID_PATTERNS)}")
    sys.stdout.write("\n--- Aperçu du XSD ---\n")
    sys.stdout.write(xml_bytes.decode("utf-8"))


if __name__ == "__main__":
    main()
