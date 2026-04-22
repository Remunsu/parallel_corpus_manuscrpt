from lxml import etree

NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def E(tag, **attrs):
    return etree.Element(f"{{{NS}}}{tag}", **attrs)


def _set_text(el, text):
    el.text = text or ""
    return el


def _witness_ref(ms_id: str) -> str:
    return f"#{ms_id}"


def _row_xml_id(idx: int) -> str:
    return f"app_{idx}"


def _token_xml_ref(token) -> str:
    if token is None or not getattr(token, "xml_id", None):
        return ""
    return token.xml_id


def _build_reading(ms_id, token, variant_type=None, is_main=False):
    attrs = {"wit": _witness_ref(ms_id)}

    if not is_main and variant_type:
        attrs["type"] = variant_type

    rdg = E("rdg", **attrs)

    token_xml_id = _token_xml_ref(token)
    if token_xml_id:
        rdg.set("n", token_xml_id)

    if token is None:
        gap = E("gap", reason="alignment-gap")
        rdg.append(gap)
        return rdg

    rdg.text = token.surface or ""
    return rdg


def build_alignment_tei(
    project_name,
    main_manuscript_id,
    manuscript_order,
    manuscript_titles,
    combined_rows,
):
    tei = E("TEI", nsmap={None: NS})

    tei_header = E("teiHeader")

    file_desc = E("fileDesc")
    title_stmt = E("titleStmt")
    title = _set_text(E("title"), f"Параллельный корпус: {project_name}")
    title_stmt.append(title)

    publication_stmt = E("publicationStmt")
    publication_stmt.append(_set_text(E("p"), "Экспорт выравнивания параллельного корпуса."))

    source_desc = E("sourceDesc")
    source_desc.append(_set_text(E("p"), "Автоматически созданный TEI-документ выравнивания."))

    file_desc.extend([title_stmt, publication_stmt, source_desc])
    tei_header.append(file_desc)

    profile_desc = E("profileDesc")
    list_wit = E("listWit")

    for ms_id in manuscript_order:
        wit = E("witness", **{f"{{{XML_NS}}}id": ms_id})
        wit.text = manuscript_titles.get(ms_id, ms_id)
        list_wit.append(wit)

    profile_desc.append(list_wit)
    tei_header.append(profile_desc)

    encoding_desc = E("encodingDesc")
    editorial_decl = E("editorialDecl")
    editorial_decl.append(
        _set_text(
            E("p"),
            "Каждый элемент app соответствует одной строке выравнивания; "
            "внутри rdg перечислены чтения по свидетелям в порядке manuscript_order. "
            "Пропуск в выравнивании передаётся через gap reason='alignment-gap'."
        )
    )
    encoding_desc.append(editorial_decl)
    tei_header.append(encoding_desc)

    text = E("text")
    body = E("body")
    div = E("div", type="alignment", subtype="parallel-corpus")

    head = _set_text(E("head"), f"Выравнивание: {project_name}")
    div.append(head)

    main_id = manuscript_order[0]

    for idx, crow in enumerate(combined_rows, start=1):
        app = E("app", **{f"{{{XML_NS}}}id": _row_xml_id(idx)})

        main_token = crow.tokens_by_ms.get(main_id)
        app.append(_build_reading(main_id, main_token, is_main=True))

        for ms_id in manuscript_order[1:]:
            token = crow.tokens_by_ms.get(ms_id)
            variant = crow.variants_by_ms.get(ms_id)

            if token is None and main_token is None:
                continue

            app.append(_build_reading(ms_id, token, variant_type=variant, is_main=False))

        div.append(app)

    body.append(div)
    text.append(body)
    tei.extend([tei_header, text])
    return tei


def write_alignment_tei(
    output_path,
    project_name,
    main_manuscript_id,
    manuscript_order,
    manuscript_titles,
    combined_rows,
):
    tei = build_alignment_tei(
        project_name=project_name,
        main_manuscript_id=main_manuscript_id,
        manuscript_order=manuscript_order,
        manuscript_titles=manuscript_titles,
        combined_rows=combined_rows,
    )

    tree = etree.ElementTree(tei)
    tree.write(
        output_path,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )