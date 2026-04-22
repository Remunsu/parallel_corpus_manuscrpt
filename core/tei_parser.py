from typing import Dict, List, Optional
from lxml import etree

from core.models import Manuscript, Token
from core.normalizer import normalize_graph, normalize_phon, abbreviation_skeleton


NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _collect_text(node) -> str:
    parts = []
    if node.text:
        parts.append(node.text)
    for child in node:
        if etree.QName(child).localname == "lb":
            continue
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).replace("\n", "").strip()


def _parse_morph(w_node) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for f_node in w_node.xpath(".//tei:fs/tei:f", namespaces=NS):
        name = f_node.get("name")
        if not name:
            continue
        values = []
        for sym in f_node.xpath("./tei:symbol", namespaces=NS):
            val = sym.get("value")
            if val:
                values.append(val)
        if values:
            result.setdefault(name, []).extend(values)
    return result


def _extract_title(root) -> str:
    titles = root.xpath(
        "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title/text()",
        namespaces=NS
    )
    return titles[0].strip() if titles else "Без названия"


def parse_tei_file(file_path: str, manuscript_id: str) -> Manuscript:
    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    tree = etree.parse(file_path, parser)
    root = tree.getroot()

    manuscript = Manuscript(
        manuscript_id=manuscript_id,
        name=_extract_title(root),
        file_path=file_path,
        tokens=[]
    )

    current_sheet: Optional[str] = None
    current_page: Optional[str] = None
    pending_lb = False
    position = 0

    body_nodes = root.xpath("//tei:text/tei:body", namespaces=NS)
    if not body_nodes:
        return manuscript

    body = body_nodes[0]

    for node in body.iter():
        tag = etree.QName(node).localname

        if tag == "milestone" and node.get("unit") == "sheet":
            current_sheet = node.get("n")

        elif tag == "pb":
            current_page = node.get("n")

        elif tag == "lb":
            pending_lb = True

        elif tag == "w":
            surface = _collect_text(node)
            if not surface:
                continue

            xml_id = node.get("{http://www.w3.org/XML/1998/namespace}id", "")
            lemma = node.get("lemma", "")

            token = Token(
                token_id=f"{manuscript_id}:{position}",
                xml_id=xml_id,
                surface=surface,
                lemma=lemma,
                norm_graph=normalize_graph(surface),
                norm_phon=normalize_phon(surface),
                abbr_skeleton=abbreviation_skeleton(surface),
                morph=_parse_morph(node),
                sheet=current_sheet,
                page=current_page,
                position=position,
                line_break_before=pending_lb
            )
            manuscript.tokens.append(token)
            position += 1
            pending_lb = False

    return manuscript