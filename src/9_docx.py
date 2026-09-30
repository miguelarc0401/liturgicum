"""Fase 6b - Maquetacion del leccionario en Word (.docx).

Monta el mismo contenido que 8_render.py, pero como libro: el texto latino
compuesto con la tipografia y el ritmo de un leccionario impreso.

Hay dos perfiles de pagina, que cambian caja, columnas y cuerpo de letra:

  carta   21.59 x 27.94 cm  ·  dos columnas  ·  texto de 10 pt
  media   13.97 x 21.59 cm  ·  una columna   ·  texto de 9.5 pt

Los dos van con margenes simetricos (interior mas ancho que exterior), asi
que salen bien impresos a doble cara; y con folios al corte: el numero de
pagina cae siempre en el borde exterior.

Tipografia: Constantia para el texto (sus cifras elzevirianas dejan pasar
los versiculos volados sin hacer ruido), Palatino Linotype para los titulos,
y Cambria solo para ℟ y ✠, que son los unicos glifos que las otras dos no
traen. El texto se parte con guiones usando el silabeo espanol, que es el
que mas se acerca al latino; por eso los parrafos van marcados como espanol
y con la revision ortografica desactivada, para que Word no los subraye.

Para leerlo en pantalla lleva dos formas de navegar:
  * un INDICE al principio en el que cada dia es un hipervinculo interno y
    lleva ademas su numero de pagina real (campo PAGEREF), que sirve igual
    en pantalla que en papel;
  * tiempos, subgrupos y celebraciones van con estilos de titulo, asi que el
    Panel de navegacion de Word y los marcadores del PDF salen solos.

Cada perfil escribe en su carpeta:  out/carta/  y  out/media/

Uso:  python src/9_docx.py [--leccionario I] [--celebracion "Adviento"]
                           [--separados | --anual] [--perfil carta|media|ambos]
"""

import argparse
import importlib.util
import itertools
import json
import os
import re
from types import SimpleNamespace

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT,
                            WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

# como se nombra el texto latino en las portadas
TEXTO_FUENTE = {
    "clementina": "Biblia Sacra juxta Vulgatam Clementinam",
    "nova": "Nova Vulgata · Bibliorum Sacrorum editio",
}
FUENTE_TEXTO = TEXTO_FUENTE["clementina"]      # lo cambia main() si procede

# tinta: negro suave para el texto, rojo de rubrica, gris para lo auxiliar
NEGRO = RGBColor(0x1A, 0x1A, 0x1A)
ROJO = RGBColor(0x9B, 0x1C, 0x1C)
GRIS = RGBColor(0x6B, 0x66, 0x60)
FILETE = "C9C0B4"                       # color de los hilos, en hexadecimal

TEXTO = "Constantia"
TITULO_F = "Palatino Linotype"
SIMBOLO = "Cambria"                     # la unica de las tres con ℟ y ✠

CABECERA_LECT = {
    "I": "Leccionario I · Ciclo A",
    "II": "Leccionario II · Ciclo B",
    "III": "Leccionario III · Ciclo C",
    "IV": "Leccionario IV · Ferias del Tiempo Ordinario",
    "V": "Leccionario V · Propio y Común de los Santos",
    "VI": "Leccionario VI · Diversas necesidades y votivas",
    "VII": "Leccionario VII · Ferias de los tiempos fuertes",
    "VIII": "Leccionario VIII · Misas rituales y de difuntos",
    "IX": "Leccionario IX · Misas con niños",
}

PERFILES = {
    "carta": SimpleNamespace(
        clave="carta", etiqueta="tamaño carta",
        ancho=21.59, alto=27.94,
        interior=2.1, exterior=1.6, sup=1.9, inf=1.7,
        columnas=2, sep_col=0.75, col_indice=2,
        texto=10.0, interlinea=1.06,
        obra=30, tiempo=16, grupo=12, celebracion=12.5, bloque=10,
        rubrica=8.5, formula=9.5, cita=9, versiculo=6.5, antifona=9.5,
        indice=8.6, indice_seccion=10.5, cabecera=8, nota=7.5,
        sangria=0.42,
    ),
    "media": SimpleNamespace(
        clave="media", etiqueta="media carta",
        ancho=13.97, alto=21.59,
        interior=1.8, exterior=1.4, sup=1.5, inf=1.35,
        columnas=1, sep_col=0.0, col_indice=1,
        texto=10.0, interlinea=1.10,
        obra=21, tiempo=13.5, grupo=11.5, celebracion=12, bloque=10,
        rubrica=8.5, formula=9.5, cita=9, versiculo=6.5, antifona=9.5,
        indice=8.8, indice_seccion=10.5, cabecera=8, nota=7.5,
        sangria=0.35,
    ),
}

EST = PERFILES["carta"]                 # perfil en curso; lo fija setup()
_bm_id = itertools.count(1)


def medidas(pf):
    """Anchos derivados de la caja, en centimetros."""
    pf.ancho_texto = pf.ancho - pf.interior - pf.exterior
    pf.ancho_col = ((pf.ancho_texto - (pf.columnas - 1) * pf.sep_col)
                    / pf.columnas)
    pf.ancho_col_indice = ((pf.ancho_texto - (pf.col_indice - 1) * pf.sep_col)
                           / pf.col_indice)
    return pf


def load_render():
    spec = importlib.util.spec_from_file_location(
        "r8", os.path.join(ROOT, "src", "8_render.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# piezas de OOXML que python-docx no expone
# --------------------------------------------------------------------------
def _rpr(run):
    return run._element.get_or_add_rPr()


def _prop(padre, tag, val=None):
    e = OxmlElement(tag)
    if val is not None:
        e.set(qn("w:val"), str(val))
    padre.append(e)
    return e


def marcador(par, nombre):
    """Envuelve el parrafo en un bookmark de Word con ese nombre."""
    bid = str(next(_bm_id))
    ini = OxmlElement("w:bookmarkStart")
    ini.set(qn("w:id"), bid)
    ini.set(qn("w:name"), nombre)
    fin = OxmlElement("w:bookmarkEnd")
    fin.set(qn("w:id"), bid)
    # el bookmark va detras de w:pPr, que tiene que seguir siendo el primero
    pPr = par._p.find(qn("w:pPr"))
    if pPr is None:
        par._p.insert(0, ini)
    else:
        pPr.addnext(ini)
    par._p.append(fin)
    return par


def _fld(par, tipo):
    r = OxmlElement("w:r")
    f = OxmlElement("w:fldChar")
    f.set(qn("w:fldCharType"), tipo)
    r.append(f)
    par._p.append(r)


def campo(par, instr, cache="1", **kw):
    """Campo de Word (PAGE, PAGEREF...) con un resultado provisional."""
    _fld(par, "begin")
    r = OxmlElement("w:r")
    i = OxmlElement("w:instrText")
    i.set(qn("xml:space"), "preserve")
    i.text = instr
    r.append(i)
    par._p.append(r)
    _fld(par, "separate")
    out = escribe(par, cache, **kw)
    _fld(par, "end")
    return out


def enlace(par, texto, ancla, **kw):
    """Hipervinculo interno: salta al marcador, sin pinta de enlace web."""
    h = OxmlElement("w:hyperlink")
    h.set(qn("w:anchor"), ancla)
    par._p.append(h)
    r = escribe(par, texto, **kw)
    h.append(r._element)                # lo mueve dentro del hipervinculo
    return r


def filete(par, lado="bottom", grosor=4, espacio=6, color=FILETE):
    """Hilo fino pegado a un parrafo: hace de regla horizontal."""
    pPr = par._p.get_or_add_pPr()
    bd = pPr.find(qn("w:pBdr"))
    if bd is None:
        bd = OxmlElement("w:pBdr")
        pPr.append(bd)
    e = OxmlElement("w:" + lado)
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), str(grosor))
    e.set(qn("w:space"), str(espacio))
    e.set(qn("w:color"), color)
    bd.append(e)
    return par


def columnas(sec, n, sep_cm):
    cols = sec._sectPr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sec._sectPr.append(cols)
    cols.set(qn("w:num"), str(n))
    cols.set(qn("w:space"), str(int(round(sep_cm * 567))))
    cols.set(qn("w:equalWidth"), "1")


# --------------------------------------------------------------------------
# parrafos y runs
# --------------------------------------------------------------------------
def escribe(par, texto, *, size=None, fuente=TEXTO, bold=False, italic=False,
            color=None, caps=False, versal=False, track=0, volado=False):
    """Un run, diciendole a Word de una vez todo lo que tiene que saber."""
    r = par.add_run(texto)
    r.font.name = fuente
    r.font.size = Pt(size if size is not None else EST.texto)
    r.bold = bold
    r.italic = italic
    r.font.all_caps = caps
    r.font.small_caps = versal
    if volado:
        r.font.superscript = True
    r.font.color.rgb = color if color is not None else NEGRO
    if track:
        s = OxmlElement("w:spacing")
        s.set(qn("w:val"), str(int(round(track * 20))))
        _rpr(r).append(s)
    return r


def parrafo(doc, *, align=None, antes=0, despues=0, sangria=0, colgante=0,
            derecha=0, interlinea=None, junto=False, estilo=None):
    p = doc.add_paragraph(style=estilo)
    f = p.paragraph_format
    f.space_before = Pt(antes)
    f.space_after = Pt(despues)
    if sangria:
        f.left_indent = Cm(sangria)
    if colgante:
        f.first_line_indent = Cm(-colgante)
    if derecha:
        f.right_indent = Cm(derecha)
    if interlinea:
        f.line_spacing = interlinea
    if align is not None:
        p.alignment = align
    f.keep_with_next = junto
    f.widow_control = True
    return p


PAR_KW = ("align", "antes", "despues", "sangria", "colgante", "derecha",
          "interlinea", "junto", "estilo")


def linea(doc, texto, **kw):
    """Parrafo de una sola voz: el atajo para los casos corrientes."""
    p = parrafo(doc, **{k: kw.pop(k) for k in list(kw) if k in PAR_KW})
    if texto:
        escribe(p, texto, **kw)
    return p


def tab_derecha(par, pos_cm, puntos=False):
    par.paragraph_format.tab_stops.add_tab_stop(
        Cm(pos_cm), WD_TAB_ALIGNMENT.RIGHT,
        WD_TAB_LEADER.DOTS if puntos else WD_TAB_LEADER.SPACES)
    return par


# --------------------------------------------------------------------------
# estilos generales del documento
# --------------------------------------------------------------------------
def setup(doc, pf):
    """Estilos base, particion de palabras y geometria de la primera seccion."""
    global EST
    EST = medidas(pf)

    st = doc.settings.element
    _prop(st, "w:mirrorMargins")                  # margenes simetricos
    _prop(st, "w:evenAndOddHeaders")              # folio siempre al exterior
    _prop(st, "w:autoHyphenation", "true")
    _prop(st, "w:doNotHyphenateCaps", "true")
    _prop(st, "w:consecutiveHyphenLimit", "2")    # sin escaleras de guiones
    _prop(st, "w:hyphenationZone", "198")
    # los PAGEREF del indice se escriben sin resolver: esto hace que Word los
    # calcule nada mas abrir (LibreOffice ya los resuelve al exportar el PDF)
    _prop(st, "w:updateFields", "true")

    n = doc.styles["Normal"]
    n.font.name = TEXTO
    n.font.size = Pt(pf.texto)
    n.font.color.rgb = NEGRO
    f = n.paragraph_format
    f.space_after = Pt(0)
    f.line_spacing = pf.interlinea
    f.widow_control = True
    # el silabeo espanol es el que mejor corta el latin; sin revision
    # ortografica, para que Word no llene el texto de subrayados rojos
    rPr = n.element.get_or_add_rPr()
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "es-ES")
    rPr.append(lang)
    _prop(rPr, "w:noProof")

    escala = [(pf.tiempo, ROJO, True), (pf.grupo, ROJO, True),
              (pf.celebracion, NEGRO, False), (pf.bloque, GRIS, True)]
    for nivel, (tam, color, versal) in enumerate(escala, start=1):
        s = doc.styles["Heading %d" % nivel]
        s.font.name = TITULO_F
        s.font.size = Pt(tam)
        s.font.bold = nivel != 4
        s.font.italic = False
        s.font.all_caps = False
        s.font.small_caps = versal
        s.font.color.rgb = color
        fmt = s.paragraph_format
        fmt.keep_with_next = True
        fmt.space_before = Pt({1: 0, 2: 16, 3: 14, 4: 10}[nivel])
        fmt.space_after = Pt({1: 10, 2: 5, 3: 3, 4: 2}[nivel])
        fmt.line_spacing = 1.0

    # los estilos de cabecera traen de serie un tabulador centrado a media
    # carta de Word: con el nuestro puesto a mano, sobra y desvia el titulillo
    for nombre in ("Header", "Footer"):
        doc.styles[nombre].paragraph_format.tab_stops.clear_all()

    geometria(doc.sections[0], pf, 1)


def geometria(sec, pf, cols):
    sec.page_width, sec.page_height = Cm(pf.ancho), Cm(pf.alto)
    sec.left_margin, sec.right_margin = Cm(pf.interior), Cm(pf.exterior)
    sec.top_margin, sec.bottom_margin = Cm(pf.sup), Cm(pf.inf)
    sec.header_distance = Cm(pf.sup * 0.55)
    sec.footer_distance = Cm(pf.inf * 0.6)
    columnas(sec, cols, pf.sep_col)
    return sec


def cabecera(sec, verso, recto):
    """Folio al corte: el numero fuera y el titulillo dentro. La pagina que
    abre cada tiempo va limpia, como en cualquier libro."""
    sec.different_first_page_header_footer = True
    sec.first_page_header.is_linked_to_previous = False
    sec.first_page_header.paragraphs[0].text = ""

    for zona, texto, numero_izq in ((sec.even_page_header, verso, True),
                                    (sec.header, recto, False)):
        zona.is_linked_to_previous = False
        p = zona.paragraphs[0]
        p.text = ""
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.tab_stops.clear_all()
        tab_derecha(p, EST.ancho_texto)
        filete(p, "bottom", grosor=2, espacio=4)
        titulillo = dict(size=EST.cabecera, color=GRIS, versal=True,
                         fuente=TITULO_F, track=0.4)
        folio = dict(size=EST.cabecera, color=GRIS, fuente=TITULO_F)
        if numero_izq:
            campo(p, " PAGE ", "1", **folio)
            p.add_run("\t")
            escribe(p, texto or "", **titulillo)
        else:
            escribe(p, texto or "", **titulillo)
            p.add_run("\t")
            campo(p, " PAGE ", "1", **folio)
    return sec


def seccion(doc, cols, verso, recto, continua=False):
    """Abre una seccion nueva, con su propio titulillo."""
    sec = doc.add_section(WD_SECTION.CONTINUOUS if continua
                          else WD_SECTION.NEW_PAGE)
    geometria(sec, EST, cols)
    cabecera(sec, verso, recto)
    return sec


def abre(doc, verso, recto, cols, pinta_titulo):
    """Pagina nueva con el titulo a todo lo ancho y, debajo, el cuerpo
    repartido en columnas: un titular no se parte por la mitad de la caja."""
    seccion(doc, 1, verso, recto)
    pinta_titulo()
    if cols > 1:
        seccion(doc, cols, verso, recto, continua=True)


# --------------------------------------------------------------------------
# portadas y titulos
# --------------------------------------------------------------------------
def regla(doc, ancho=0.3, antes=0, despues=0, base=None):
    """Hilo corto y centrado, medido sobre el ancho de la caja en curso."""
    margen = (base or EST.ancho_texto) * (1 - ancho) / 2
    p = parrafo(doc, antes=antes, despues=despues, sangria=margen,
                derecha=margen)
    escribe(p, "", size=1)
    return filete(p, "bottom", grosor=4, espacio=1)


def cruz(doc, size, despues):
    return linea(doc, "✠", align=WD_ALIGN_PARAGRAPH.CENTER, fuente=SIMBOLO,
                 size=size, color=ROJO, despues=despues)


def portada(doc, titulo_obra, subtitulo, pie):
    linea(doc, "", size=EST.obra * 0.7)
    cruz(doc, EST.tiempo, EST.obra * 0.5)
    regla(doc, 0.30, despues=EST.obra * 0.45)
    for i, t in enumerate(titulo_obra):
        linea(doc, t, align=WD_ALIGN_PARAGRAPH.CENTER, fuente=TITULO_F,
              size=EST.obra, track=EST.obra * 0.16, interlinea=1.15,
              despues=2 if i + 1 < len(titulo_obra) else 0)
    regla(doc, 0.30, antes=EST.obra * 0.5, despues=EST.obra * 0.5)
    for t in subtitulo:
        linea(doc, t, align=WD_ALIGN_PARAGRAPH.CENTER, fuente=TITULO_F,
              size=EST.grupo, italic=True, despues=6)
    linea(doc, "", size=EST.obra * 0.9)
    for t in pie:
        linea(doc, t, align=WD_ALIGN_PARAGRAPH.CENTER, size=EST.nota,
              color=GRIS, versal=True, track=0.3, despues=4)


def portadilla(doc, nombre, pie=None):
    """Media portada: la que abre cada leccionario dentro del tomo completo."""
    linea(doc, "", size=EST.obra)
    cruz(doc, EST.grupo, EST.tiempo)
    partes = nombre.split(" · ")
    linea(doc, partes[0], align=WD_ALIGN_PARAGRAPH.CENTER, fuente=TITULO_F,
          size=EST.tiempo * 1.35, track=EST.tiempo * 0.1, versal=True,
          despues=6)
    if len(partes) > 1:
        regla(doc, 0.22, antes=6, despues=10)
        linea(doc, " · ".join(partes[1:]), align=WD_ALIGN_PARAGRAPH.CENTER,
              fuente=TITULO_F, size=EST.grupo, italic=True, despues=8)
    if pie:
        linea(doc, pie, align=WD_ALIGN_PARAGRAPH.CENTER, size=EST.nota,
              color=GRIS, versal=True, track=0.3)


def titulo_tiempo(doc, texto):
    """Apertura de un tiempo liturgico: versalitas entre dos hilos."""
    linea(doc, "", size=EST.tiempo * 1.1)
    regla(doc, 0.24, despues=EST.tiempo * 0.7)
    p = doc.add_paragraph(texto, style="Heading 1")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:
        s = OxmlElement("w:spacing")
        s.set(qn("w:val"), str(int(EST.tiempo * 0.14 * 20)))
        _rpr(r).append(s)
    regla(doc, 0.24, antes=EST.tiempo * 0.3, despues=EST.tiempo * 1.1)
    return p


def titulo_grupo(doc, texto):
    return filete(doc.add_paragraph(texto, style="Heading 2"),
                  "bottom", grosor=2, espacio=3)


# --------------------------------------------------------------------------
# indice navegable, con numero de pagina real
# --------------------------------------------------------------------------
def pagina_de(par, slug, size=None, italic=False):
    """Numero de pagina del marcador; Word y LibreOffice lo calculan solos."""
    return campo(par, " PAGEREF %s \\h " % slug, "·",
                 size=size or EST.indice, color=GRIS, fuente=TITULO_F,
                 italic=italic)


def entrada_indice(doc, bloque, sangria):
    p = parrafo(doc, sangria=sangria, despues=1.5, interlinea=1.0)
    tab_derecha(p, EST.ancho_col_indice - 0.05, puntos=True)
    if bloque["secundaria"]:
        escribe(p, "— ", size=EST.indice, color=GRIS)
    enlace(p, bloque["texto"], bloque["slug"], size=EST.indice)
    p.add_run("\t")
    pagina_de(p, bloque["slug"])
    return p


def entradas_inline(doc, items, sangria, grupo=None):
    """Los dias de una semana, apretados en una linea: 'lun 12 · mar 13'."""
    p = parrafo(doc, sangria=sangria + (EST.sangria if grupo else 0),
                colgante=EST.sangria if grupo else 0, despues=1.5,
                interlinea=1.0)
    if grupo:
        escribe(p, grupo + "  ", size=EST.indice, italic=True)
    for i, b in enumerate(items):
        if i:
            escribe(p, " · ", size=EST.indice, color=GRIS)
        enlace(p, b.get("texto") or b["titulo_indice"], b["slug"],
               size=EST.indice)
        escribe(p, " ", size=EST.indice * 0.7)
        # en cursiva: apretado contra el nombre del dia, un numero redondo se
        # leeria como parte del titulo
        pagina_de(p, b["slug"], size=EST.indice * 0.92, italic=True)
    return p


def cabeza_indice(doc, texto, ancla):
    p = linea(doc, texto, fuente=TITULO_F, size=EST.indice_seccion * 1.3,
              versal=True, track=EST.indice_seccion * 0.1, color=ROJO,
              despues=10, junto=True)
    filete(p, "bottom", grosor=4, espacio=5)
    return marcador(p, ancla)


def docx_indice(doc, r8, bloques, sin_texto, ancla_indice, verso):
    abre(doc, verso, "Índice", EST.col_indice,
         lambda: cabeza_indice(doc, "Índice", ancla_indice))
    for ln in r8.lineas_indice(bloques):
        if ln["tipo"] == "seccion":
            linea(doc, ln["texto"], fuente=TITULO_F, size=EST.indice_seccion,
                  versal=True, track=0.4, color=ROJO, antes=11, despues=4,
                  junto=True)
            continue
        if ln["tipo"] == "grupo":
            linea(doc, ln["texto"], size=EST.indice, italic=True,
                  sangria=EST.sangria * ln["sangria"], antes=5, despues=2,
                  junto=True)
            continue
        sang = EST.sangria * ln["sangria"]
        if ln["inline"]:
            entradas_inline(doc, ln["items"], sang, ln["grupo"])
        else:
            for b in ln["items"]:
                entrada_indice(doc, b, sang + (EST.sangria
                                               if b["secundaria"] else 0))
    if sin_texto:
        linea(doc, "Entradas del índice sin formulario de lecturas "
                   "(introducciones, listas de aclamaciones, textos "
                   "comunes): %s."
              % "; ".join(t for _, t in sin_texto), size=EST.nota, italic=True,
              color=GRIS, antes=14)
    linea_indice_anexos(doc)


# --------------------------------------------------------------------------
# cuerpo: las lecturas
# --------------------------------------------------------------------------
def rubrica(doc, texto, cita):
    """Linea de rubrica: 'LECTIO PRIMA' a la izquierda, la cita al corte."""
    p = parrafo(doc, antes=EST.texto * 0.95, despues=1, junto=True,
                interlinea=1.0)
    tab_derecha(p, EST.ancho_col - 0.05)
    escribe(p, texto, fuente=TITULO_F, size=EST.rubrica, color=ROJO,
            versal=True, bold=True, track=EST.rubrica * 0.09)
    if cita:
        p.add_run("\t")
        escribe(p, cita, size=EST.cita, color=GRIS, italic=True)
    return p


def verse_par(doc, tramos, numerar, sangria=0, despues=None, r8=None,
              salmo=False):
    p = parrafo(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, sangria=sangria,
                despues=EST.texto * 0.3 if despues is None else despues)
    for i, tr in enumerate(tramos):
        if i:
            escribe(p, " [...] ", color=ROJO, bold=True)
        for v in tr:
            t = v["texto"]
            if salmo and r8 is not None:
                # el epigrafe del salmo ("Magistro chori. PSALMUS. David.") no
                # se imprime en los libros liturgicos
                t = r8.sin_titulo_salmo(t, v["cap"], v["vers"])
                if not t:
                    continue
            if numerar:
                escribe(p, "%s" % v["vers"], size=EST.versiculo, color=ROJO,
                        volado=True)
                escribe(p, " ", size=EST.texto * 0.5)
            escribe(p, (r8.ac(t) if r8 is not None else t) + " ")
    return p


def erre(par, size, sufijo="."):
    """El ℟ de responsorio, que solo trae Cambria."""
    escribe(par, "℟", fuente=SIMBOLO, size=size, color=ROJO, bold=True)
    escribe(par, sufijo, size=size, color=ROJO, bold=True)
    return par


def docx_lecturas(doc, r8, lecturas, formulas, siglas, corpus, numerar):
    """Las lecturas de un formulario: rubrica, cita, formula y texto latino."""
    for e in lecturas:
        cita = r8.cita_latina(e, siglas)
        if e.get("aprox_cf"):
            cita = "cf. " + cita
        rubrica(doc, r8.titulo_lectura(e), cita)

        if e["tipo"] not in ("aleluya", "secuencia", "salmo responsorial"):
            linea(doc, formulas.get(e["libro_vulgata"], "Lectio"),
                  size=EST.formula, italic=True, despues=EST.texto * 0.35,
                  junto=True)

        if e["tipo"] == "salmo responsorial":
            ant = r8.antifona_latina(e, corpus)
            if ant:
                p = parrafo(doc, sangria=EST.sangria * 1.5,
                            colgante=EST.sangria * 1.5,
                            despues=EST.texto * 0.5, junto=True)
                erre(p, EST.antifona, ".  ")
                escribe(p, ant, size=EST.antifona, italic=True)
            for tr in e["tramos"]:
                # el ℟ cierra la estrofa en el mismo renglon: un leccionario
                # no gasta una linea entera en repetir el signo
                p = verse_par(doc, [tr], numerar, sangria=EST.sangria * 1.5,
                              despues=EST.texto * 0.5, r8=r8, salmo=True)
                escribe(p, "   ")
                erre(p, EST.antifona)
        else:
            verse_par(doc, e["tramos"], numerar, r8=r8)
            if e["tipo"] not in ("aleluya", "secuencia"):
                linea(doc, r8.ac("Verbum Domini."), size=EST.formula,
                      italic=True,
                      color=ROJO, despues=EST.texto * 0.2)


ANEXO_ANCLA = "anexos"
CON_ANEXOS = False        # lo fija main(); gobierna la linea del indice


def linea_indice_anexos(doc):
    """La entrada 'Apendices' al pie del indice, con su numero de pagina."""
    if not CON_ANEXOS:
        return
    p = parrafo(doc, antes=11, despues=4, junto=True, interlinea=1.0)
    tab_derecha(p, EST.ancho_col_indice - 0.05, puntos=True)
    enlace(p, "APÉNDICES", ANEXO_ANCLA, size=EST.indice_seccion,
           fuente=TITULO_F, versal=True, track=0.4, color=ROJO)
    p.add_run("	")
    pagina_de(p, ANEXO_ANCLA, size=EST.indice)
    # y cada apendice con su linea, que es lo que se busca de verdad
    ruta = os.path.join(DATA, "anexos.json")
    if not os.path.exists(ruta):
        return
    for a in json.load(open(ruta, encoding="utf-8"))["anexos"]:
        if a.get("ausente"):
            continue
        q = parrafo(doc, sangria=EST.sangria, despues=1.5, interlinea=1.0)
        tab_derecha(q, EST.ancho_col_indice - 0.05, puntos=True)
        enlace(q, a["ambito"], "anexo_" + a["id"], size=EST.indice)
        q.add_run("	")
        pagina_de(q, "anexo_" + a["id"])
    if not CON_IT:
        return
    r = parrafo(doc, antes=9, despues=4, junto=True, interlinea=1.0)
    tab_derecha(r, EST.ancho_col_indice - 0.05, puntos=True)
    enlace(r, "ÍNDICE DE TEXTOS", IT_ANCLA, size=EST.indice_seccion,
           fuente=TITULO_F, versal=True, track=0.4, color=ROJO)
    r.add_run("	")
    pagina_de(r, IT_ANCLA, size=EST.indice)


def docx_anexos(doc, r8, obra, siglas, corpus, numerar, fuente,
                ancla_indice=None):
    """Los apendices: listas numeradas, no formularios de un dia.

    Se componen como un tiempo liturgico mas -su portadilla, sus dos columnas,
    su entrada en el Panel de navegacion- porque es donde el lector los busca:
    al final del libro.
    """
    meta, resueltas, fijo = r8.load_anexos(fuente)
    if not meta:
        return []
    abre(doc, obra, "Apéndices", EST.columnas,
         lambda: titulo_tiempo(doc, "APÉNDICES"))
    p = doc.add_paragraph("", style="Heading 1")
    marcador(p, ANEXO_ANCLA)
    p.paragraph_format.space_after = Pt(0)
    linea(doc, "Listas que el leccionario pone detrás de los formularios: los "
               "versículos que pueden sustituir al del día antes del "
               "Evangelio, y los salmos que pueden cantarse en lugar del "
               "propio del día.",
          size=EST.nota, italic=True, color=GRIS,
          despues=EST.texto * 1.2, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    hechos, ausentes = [], []
    for a in meta["anexos"]:
        if a.get("ausente"):
            ausentes.append(a)
            continue
        ancla = "anexo_" + a["id"]
        hechos.append((a, ancla))
        cab = doc.add_paragraph(a["titulo"], style="Heading 2")
        marcador(cab, ancla)
        filete(cab, "bottom", grosor=2, espacio=3)
        pie = parrafo(doc, despues=EST.texto * 0.6, junto=True, interlinea=1.0)
        escribe(pie, a["ambito"], size=EST.nota, italic=True, color=GRIS)
        if ancla_indice:
            escribe(pie, "   ·   ", size=EST.nota, color=GRIS)
            enlace(pie, "↑ Índice", ancla_indice, size=EST.nota, color=GRIS)

        tiempo = None
        for e in a["entradas"]:
            if e.get("tiempo") and e["tiempo"] != tiempo:
                tiempo = e["tiempo"]
                doc.add_paragraph(tiempo, style="Heading 3")
            if e.get("sin_cita"):
                row = fijo.get((a["id"], str(e["n"])))
                if not row:
                    continue
                p = parrafo(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                            sangria=EST.sangria * 1.5,
                            colgante=EST.sangria * 1.5,
                            despues=EST.texto * 0.45)
                escribe(p, "%s.  " % e["n"], size=EST.texto, bold=True,
                        color=ROJO)
                escribe(p, r8.texto_fijo(row["latin"]))
                continue
            lec = resueltas.get((a["id"], e["orden"]))
            if not lec or not lec["tramos"]:
                continue
            cita = r8.cita_latina(lec, siglas)
            if lec.get("aprox_cf"):
                cita = "cf. " + cita
            if lec["tipo"] == "salmo responsorial":
                rubrica(doc, "", cita)
                ant = r8.antifona_latina(lec, corpus)
                if ant:
                    p = parrafo(doc, sangria=EST.sangria * 1.5,
                                colgante=EST.sangria * 1.5,
                                despues=EST.texto * 0.5, junto=True)
                    erre(p, EST.antifona, ".  ")
                    escribe(p, ant, size=EST.antifona, italic=True)
                for tr in lec["tramos"]:
                    p = verse_par(doc, [tr], numerar,
                                  sangria=EST.sangria * 1.5,
                                  despues=EST.texto * 0.5, r8=r8, salmo=True)
                    escribe(p, "   ")
                    erre(p, EST.antifona)
            else:
                # el numero manda el renglon y la cita se va al corte
                p = parrafo(doc, antes=EST.texto * 0.5, despues=1,
                            junto=True, interlinea=1.0)
                tab_derecha(p, EST.ancho_col - 0.05)
                escribe(p, "%s." % e["n"], size=EST.rubrica, bold=True,
                        color=ROJO)
                p.add_run("\t")
                escribe(p, cita, size=EST.cita, color=GRIS, italic=True)
                verse_par(doc, lec["tramos"], False, sangria=EST.sangria * 1.5,
                          r8=r8)
        if a.get("respuestas"):
            doc.add_paragraph("Respuestas salmódicas alternativas",
                              style="Heading 3")
            linea(doc, "Son antífonas sin cita bíblica: el leccionario no da "
                       "su referencia, así que no hay de dónde sacar su "
                       "latín. Se dan en castellano.",
                  size=EST.nota, italic=True, color=GRIS,
                  despues=EST.texto * 0.6, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
            for r in a["respuestas"]:
                p = parrafo(doc, sangria=EST.sangria * 1.5,
                            colgante=EST.sangria * 1.5,
                            despues=EST.texto * 0.25)
                escribe(p, r["tiempo"] + "  ", size=EST.nota, bold=True)
                escribe(p, r["es"], size=EST.nota)
    if ausentes:
        linea(doc, "Faltan por incorporar %d listas cuyas páginas el sitio no "
                   "ha llegado a servir: %s. El rastreador las vuelve a pedir "
                   "en cada pasada."
                   % (len(ausentes), "; ".join(a["ambito"] for a in ausentes)),
              size=EST.nota, italic=True, color=GRIS,
              antes=EST.texto, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    return hechos


IT_ANCLA = "indice_textos"
CON_IT = False            # lo fija main()


def docx_indice_textos(doc, r8, obra, siglas, ancla_indice=None):
    """El leccionario al reves: cada pasaje y donde se lee, con su pagina."""
    it = r8.load_indice_textos()
    if not it:
        return
    abre(doc, obra, "Índice de textos", EST.col_indice,
         lambda: titulo_tiempo(doc, "ÍNDICE DE TEXTOS"))
    p = doc.add_paragraph("", style="Heading 1")
    marcador(p, IT_ANCLA)
    p.paragraph_format.space_after = Pt(0)
    n_p = sum(len(l["pasajes"]) for l in it["libros"])
    linea(doc, "Los %d pasajes bíblicos del leccionario, por orden de libro y "
               "capítulo, con las celebraciones en que se leen y su página."
               % n_p,
          size=EST.nota, italic=True, color=GRIS, despues=EST.texto,
          align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    for libro in it["libros"]:
        linea(doc, libro["es"], fuente=TITULO_F, size=EST.indice_seccion,
              versal=True, track=0.3, color=ROJO, antes=9, despues=3,
              junto=True)
        for x in libro["pasajes"]:
            q = parrafo(doc, sangria=EST.sangria, colgante=EST.sangria,
                        despues=1.2, interlinea=1.0)
            tab_derecha(q, EST.ancho_col_indice - 0.05, puntos=True)
            escribe(q, r8.cita_lat(x["cita"], x["sigla"], siglas,
                                   libro["libro"]) + "  ",
                    size=EST.indice, bold=True)
            for i, d in enumerate(x["donde"]):
                if i:
                    escribe(q, " · ", size=EST.indice, color=GRIS)
                texto = r8.corto(d["celebracion"])
                if d["slug"]:
                    enlace(q, texto, d["slug"], size=EST.indice, color=GRIS)
                else:
                    escribe(q, texto, size=EST.indice, color=GRIS)
            q.add_run("\t")
            primero = next((d["slug"] for d in x["donde"] if d["slug"]), None)
            if primero:
                pagina_de(q, primero)


def docx_remision(doc, rem, ancla, ancla_indice=None):
    """Una memoria que el libro resuelve remitiendo al Comun.

    Nueve memorias del santoral no traen lecturas propias: una linea
    ("Del Comun de pastores") es todo su formulario. Sin esto, esos nueve
    dias del ano se caerian del documento sin decir nada.
    """
    p = doc.add_paragraph(rem["celebracion"], style="Heading 3")
    marcador(p, ancla)
    etiqueta = " · ".join(x for x in (rem.get("fecha"),
                                     rem.get("grado")) if x)
    if etiqueta or ancla_indice:
        pie = parrafo(doc, despues=EST.texto * 0.5, junto=True,
                      interlinea=1.0)
        if etiqueta:
            escribe(pie, etiqueta, size=EST.nota, italic=True, color=GRIS)
        if ancla_indice:
            if etiqueta:
                escribe(pie, "   ·   ", size=EST.nota, color=GRIS)
            enlace(pie, "↑ Índice", ancla_indice, size=EST.nota,
                   color=GRIS)
    for r in rem.get("comunes") or []:
        q = parrafo(doc, despues=EST.texto * 0.4, junto=True,
                    interlinea=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
        escribe(q, r["texto"].rstrip(" .;,"), size=EST.rubrica,
                italic=True, color=ROJO)


def docx_celebracion(doc, r8, lecturas, ancla, formulas, siglas, corpus,
                     numerar, ancla_indice=None):
    cab = lecturas[0]
    p = doc.add_paragraph(cab["celebracion"], style="Heading 3")
    marcador(p, ancla)
    # el dia del mes (leccionario V) y el ciclo comparten la linea de pie
    etiqueta = " · ".join(x for x in (cab.get("_fecha"), cab.get("_grado"),
                                     cab.get("ciclo")) if x)
    if etiqueta or ancla_indice:
        pie = parrafo(doc, despues=EST.texto * 0.5, junto=True, interlinea=1.0)
        if etiqueta:
            escribe(pie, etiqueta, size=EST.nota, italic=True, color=GRIS)
        if ancla_indice:
            if etiqueta:
                escribe(pie, "   ·   ", size=EST.nota, color=GRIS)
            enlace(pie, "↑ Índice", ancla_indice, size=EST.nota, color=GRIS)
    # "Del Comun de pastores": en el santoral casi todas las memorias lo
    # llevan, y es rubrica del libro, no un enlace del sitio
    for rem in cab.get("_comunes") or []:
        r = parrafo(doc, despues=EST.texto * 0.4, junto=True, interlinea=1.0,
                    align=WD_ALIGN_PARAGRAPH.CENTER)
        escribe(r, rem["texto"].rstrip(" .;,"), size=EST.rubrica, italic=True,
                color=ROJO)
    docx_lecturas(doc, r8, lecturas, formulas, siglas, corpus, numerar)


# --------------------------------------------------------------------------
# un leccionario entero
# --------------------------------------------------------------------------
def docx_leccionario(doc, r8, lect, celebs, arbol, formulas, siglas, corpus,
                     numerar, con_indice=True, con_portada=True):
    p = r8.plan(lect, celebs, arbol)
    n_lect = sum(len(v) for v in celebs.values())
    n_vers = sum(e["n_versiculos"] for v in celebs.values() for e in v)
    nombre = r8.NOMBRE_LECT.get(lect, "Leccionario " + lect)
    corto = CABECERA_LECT.get(lect, "Leccionario " + lect)
    ancla_indice = "indice_%s" % lect.lower()
    pie = "%d celebraciones · %d lecturas · %d versículos" % (
        p["n_celebraciones"], n_lect, n_vers)

    if con_portada:
        portada(doc, ["LECTIONARIUM", "LATINUM"],
                [nombre, FUENTE_TEXTO],
                ["Estructura: Leccionario de Servicios Koinonía", pie])
    else:
        seccion(doc, 1, corto, corto)
        portadilla(doc, nombre, pie)

    if con_indice:
        docx_indice(doc, r8, p["bloques"], p["sin_texto"], ancla_indice, corto)

    abierta = False
    for b in p["bloques"]:
        if b["tipo"] == "seccion":
            abre(doc, corto, b["texto"], EST.columnas,
                 lambda t=b["texto"]: titulo_tiempo(doc, t))
            abierta = True
            continue
        if not abierta:                 # entradas sueltas antes del primer
            seccion(doc, EST.columnas, corto, corto)   # tiempo liturgico
            abierta = True
        if b["tipo"] == "grupo":
            titulo_grupo(doc, b["texto"])
        elif b["tipo"] == "remision":
            docx_remision(doc, b["remision"], b["slug"],
                          ancla_indice if con_indice else None)
        elif not b["repetida"]:
            docx_celebracion(doc, r8, celebs[b["clave"]], b["slug"], formulas,
                             siglas, corpus, numerar,
                             ancla_indice if con_indice else None)
    return p


# --------------------------------------------------------------------------
# el ano liturgico de corrido: los cinco leccionarios en un solo documento
# --------------------------------------------------------------------------
def docx_indice_anual(doc, r8, cal, ancla_indice, verso):
    """Una linea por semana: el domingo y detras sus ferias, todo enlazado."""
    abre(doc, verso, "Índice del año", EST.col_indice,
         lambda: cabeza_indice(doc, "Índice del año", ancla_indice))
    for sec in cal["secciones"]:
        linea(doc, sec["titulo"], fuente=TITULO_F, size=EST.indice_seccion,
              versal=True, track=0.4, color=ROJO, antes=11, despues=4,
              junto=True)
        for g in sec["grupos"]:
            if g["dias"]:
                entradas_inline(doc, g["dias"], EST.sangria,
                                g["titulo"] or None)
    linea_indice_anexos(doc)


def docx_anual(doc, r8, cal, bl, formulas, siglas, corpus, numerar):
    ancla_indice = "indice_anual"
    dias = sum(len(g["dias"]) for s in cal["secciones"] for g in s["grupos"])
    formularios = sum(len(d["bloques"]) for s in cal["secciones"]
                      for g in s["grupos"] for d in g["dias"])
    obra = "Lectionarium latinum"
    portada(doc, ["LECTIONARIUM", "LATINUM"],
            ["El año litúrgico completo", FUENTE_TEXTO],
            ["Cada domingo con sus tres ciclos y, detrás, las ferias "
             "de su semana",
             "Estructura: Leccionario de Servicios Koinonía",
             "%d días · %d formularios" % (dias, formularios)])

    docx_indice_anual(doc, r8, cal, ancla_indice, obra)

    for sec in cal["secciones"]:
        abre(doc, obra, sec["titulo"], EST.columnas,
             lambda t=sec["titulo"]: titulo_tiempo(doc, t))
        for g in sec["grupos"]:
            if g["titulo"]:
                titulo_grupo(doc, g["titulo"])
            for dia in g["dias"]:
                p = doc.add_paragraph(dia["titulo"], style="Heading 3")
                marcador(p, dia["slug"])
                pie = parrafo(doc, despues=EST.texto * 0.4, junto=True,
                              interlinea=1.0)
                enlace(pie, "↑ Índice", ancla_indice, size=EST.nota,
                       color=GRIS)
                for b in dia["bloques"]:
                    lecturas = bl.get(tuple(b["clave"]))
                    if not lecturas:
                        continue
                    doc.add_paragraph(b["etiqueta"], style="Heading 4")
                    docx_lecturas(doc, r8, lecturas, formulas, siglas, corpus,
                                  numerar)


# --------------------------------------------------------------------------
def nuevo(pf):
    doc = Document()
    setup(doc, pf)
    return doc


def enlaces_rotos(doc):
    """Anclas a las que apunta un enlace y que el documento no define.

    El indice del leccionario vive de sus hipervinculos internos, y un enlace
    roto no da ningun error al abrir: simplemente no salta. Se cuenta al
    guardar para que no pueda pasar en silencio.
    """
    x = doc.element.body.xml
    marc = set(re.findall(r'w:name="([^"]+)"', x))
    enl = re.findall(r'w:anchor="([^"]+)"', x)
    pref = re.findall(r"PAGEREF (\w+)", x)
    return sorted({a for a in enl + pref if a not in marc})


def guarda(doc, pf, nombre):
    carpeta = os.path.join(OUT, pf.clave)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    rotos = enlaces_rotos(doc)
    doc.save(ruta)
    print("%-68s %6d KB%s" % (ruta[len(ROOT) + 1:],
                              os.path.getsize(ruta) // 1024,
                              "" if not rotos else
                              "   ENLACES ROTOS: %d (%s...)"
                              % (len(rotos), ", ".join(rotos[:3]))))


def construye(pf, args, r8, entradas, formulas, siglas, corpus, toc, por_lect):
    numerar = not args.sin_numeros
    con_indice = not args.celebracion
    nombre_dado = os.path.basename(args.salida) if args.salida else None

    if args.anual:
        doc = nuevo(pf)
        docx_anual(doc, r8, r8.load_calendario(),
                   r8.bloques_por_clave(entradas), formulas, siglas, corpus,
                   numerar)
        if not args.sin_anexos:
            docx_anexos(doc, r8, "Lectionarium latinum", siglas, corpus,
                        numerar, args.fuente, "indice_anual")
        if CON_IT:
            docx_indice_textos(doc, r8, "Lectionarium latinum", siglas,
                               "indice_anual")
        guarda(doc, pf, nombre_dado or r8.ARCHIVO_ANUAL + ".docx")
        return

    if args.separados:
        for lect in r8.ORDEN_LECT:
            if lect not in por_lect:
                continue
            doc = nuevo(pf)
            docx_leccionario(doc, r8, lect, por_lect[lect], toc.get(lect, {}),
                             formulas, siglas, corpus, numerar, con_indice,
                             con_portada=True)
            if not args.sin_anexos:
                docx_anexos(doc, r8, r8.NOMBRE_LECT.get(lect, "Leccionario"),
                            siglas, corpus, numerar, args.fuente,
                            "indice_%s" % lect.lower())
            if CON_IT:
                docx_indice_textos(doc, r8,
                                   r8.NOMBRE_LECT.get(lect, "Leccionario"),
                                   siglas, "indice_%s" % lect.lower())
            guarda(doc, pf, r8.ARCHIVO_LECT[lect] + ".docx")
        return

    doc = nuevo(pf)
    portada(doc, ["LECTIONARIUM", "LATINUM"],
            [FUENTE_TEXTO],
            ["Estructura: Leccionario de Servicios Koinonía",
             "%d lecturas · %d versículos"
             % (len(entradas), sum(e["n_versiculos"] for e in entradas))])
    regla(doc, 0.18, antes=EST.obra, despues=EST.tiempo)
    for lect in r8.ORDEN_LECT:
        if lect in por_lect:
            p = parrafo(doc, align=WD_ALIGN_PARAGRAPH.CENTER, despues=4)
            enlace(p, r8.NOMBRE_LECT.get(lect, "Leccionario " + lect),
                   "indice_%s" % lect.lower(), size=EST.formula)

    for lect in r8.ORDEN_LECT:
        if lect in por_lect:
            docx_leccionario(doc, r8, lect, por_lect[lect], toc.get(lect, {}),
                             formulas, siglas, corpus, numerar, con_indice,
                             con_portada=False)
    if not args.sin_anexos:
        docx_anexos(doc, r8, "Lectionarium latinum", siglas, corpus, numerar,
                    args.fuente)
    if CON_IT:
        docx_indice_textos(doc, r8, "Lectionarium latinum", siglas)
    guarda(doc, pf, nombre_dado or "lectionarium.docx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leccionario", default=None)
    ap.add_argument("--celebracion", default=None)
    ap.add_argument("--salida", default=None, help="solo el nombre del fichero")
    ap.add_argument("--perfil", default="ambos",
                    choices=["carta", "media", "ambos"])
    ap.add_argument("--separados", action="store_true",
                    help="un fichero por leccionario, cada uno con su indice")
    ap.add_argument("--anual", action="store_true",
                    help="un solo documento en el orden del ano liturgico")
    ap.add_argument("--sin-numeros", action="store_true")
    ap.add_argument("--sin-anexos", action="store_true",
                    help="sin los apendices (por omision van al final)")
    ap.add_argument("--sin-indice-textos", action="store_true",
                    help="sin el indice de textos (por omision va al final)")
    ap.add_argument("--fuente", default="clementina",
                    choices=["clementina", "nova"],
                    help="corpus latino: la Clementina o la Nova Vulgata")
    ap.add_argument("--sin-acentos", action="store_true",
                    help="sin acentuacion liturgica (por omision va acentuado)")
    args = ap.parse_args()

    r8 = load_render()
    r8.activa_acentos(not args.sin_acentos)
    cfg = r8.FUENTES[args.fuente]
    global OUT, FUENTE_TEXTO, CON_ANEXOS, CON_IT
    CON_ANEXOS = (not args.sin_anexos
                  and os.path.exists(os.path.join(DATA, "anexos.json")))
    # solo en el documento anual: ver la nota de 8_render.py
    CON_IT = (args.anual and not args.sin_indice_textos
              and os.path.exists(os.path.join(DATA, "indice_textos.json")))
    FUENTE_TEXTO = TEXTO_FUENTE[args.fuente]
    if cfg["salida"]:
        OUT = os.path.join(OUT, cfg["salida"])
        os.makedirs(OUT, exist_ok=True)
    if args.fuente == "nova":
        r8.TITULI = r8.load_tituli_salmos()
    entradas = json.load(open(os.path.join(DATA, cfg["lecturas"]),
                              encoding="utf-8"))
    if args.leccionario:
        entradas = [e for e in entradas if e["leccionario"] == args.leccionario]
    if args.celebracion:
        pat = args.celebracion.lower()
        entradas = [e for e in entradas if pat in e["celebracion"].lower()]
    if not entradas:
        raise SystemExit("ningun texto coincide con el filtro")

    formulas, siglas = r8.load_formulas(cfg["formulas"])
    corpus = json.load(open(os.path.join(DATA, cfg["corpus"]),
                            encoding="utf-8"))
    toc = r8.load_toc()
    por_lect = r8.celebraciones(entradas)

    claves = ["carta", "media"] if args.perfil == "ambos" else [args.perfil]
    for clave in claves:
        construye(medidas(PERFILES[clave]), args, r8, entradas, formulas,
                  siglas, corpus, toc, por_lect)


if __name__ == "__main__":
    main()
