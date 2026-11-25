"""Build the self-contained close-ups used by the README's mobile picture sources."""

from pathlib import Path
from xml.etree import ElementTree as ET


ASSETS = Path(__file__).resolve().parents[1] / "assets"
ET.register_namespace("", "http://www.w3.org/2000/svg")


def build_mobile(name, view_box):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    scene = ET.parse(ASSETS / f"{name}.svg", parser=parser)
    root = scene.getroot()
    _, _, width, height = view_box.split()
    root.attrib.update(viewBox=view_box, width=width, height=height)
    if name == "night-city-crew":
        root.find(".//*[@id='workshop']").attrib.update(x="0", y="270")
        divider = root.find(".//*[@id='divider-line']")
        if divider is not None:
            divider.set("d", "M0 270 H480")
    if name == "contacto":
        root.set("class", "compact")
        # Keep the theatre on the quay between the two billboards in the close-up when present.
        theatre = root.find(".//*[@id='projection-theatre']")
        if theatre is not None:
            theatre.set("transform", "translate(-47 107) scale(.62)")
    if name == "night-city":
        root.find(".//*[@id='identity']").set("transform", "translate(433 34) scale(.51)")
        root.find(".//*[@id='wordmark']").set("transform", "translate(54 100) scale(.60) skewX(-12)")
        root.find(".//*[@id='tower-district']").attrib.update(x="435", width=width, viewBox="219 0 525 324")
        # Keep the Arasaka neon sign framed inside the mobile canyon view when present.
        for sel, tx in (
            (".//*[@id='west-residences']", "translate(193 0) scale(.62 1)"),
            (".//*[@id='east-hotel']", "translate(624 0) scale(.82 1)"),
            (".//*[@id='arasaka-sign']", "translate(656 84) skewY(-8) scale(.82)"),
        ):
            el = root.find(sel)
            if el is not None:
                el.set("transform", tx)
        root.find(".//*[@id='night-market']").attrib.update(x="435", width=width, height="274", viewBox="170 0 525 274")
        root.find(".//*[@id='stack-icons']").set("transform", "translate(45 222) scale(1.35)")
        root.find(".//*[@id='title-shade']").attrib.update(x="435", width="322", opacity=".64")
    if name == "atlantis":
        root.find(".//*[@id='caption']").set("transform", "translate(474 18) scale(.62)")
        root.find(".//*[@id='shade']").attrib.update(x2="0", y2="1")
        root.find(".//*[@id='caption-shade']").attrib.update(x="455", y="0", width="482", height="145", opacity=".76")
    if name == "arcadia":
        root.find(".//*[@id='teaser-link']").set("transform", "translate(468 386)")
        root.find(".//*[@id='caption']").set("transform", "translate(468 26) scale(.68)")
        root.find(".//*[@id='caption-shadow']").attrib.update(x="450", width="235")
        visor = root.find(".//*[@id='visor']")
        visor.set("transform", "translate(450 0) scale(.5104167 1)")
    if name == "loki-code-guide":
        root.find(".//*[@id='terminal']").set("transform", "translate(71 4) scale(1.62)")
    if name in ("night-city", "contacto"):
        style = root.find(".//{http://www.w3.org/2000/svg}style")
        style.text = style.text.rstrip() + """
      .secondary { opacity:.48 }
      .rain, .return, .beacons { opacity:.31 }
      .far.secondary { opacity:.45 }
      .inbound, .outbound { opacity:.55 }
      .freight, .rider { opacity:.72 }
"""
    root.insert(0, ET.Comment(f" Generated from {name}.svg by scripts/escenas_moviles.py "))
    content = ET.tostring(root, encoding="unicode")
    (ASSETS / f"{name}-movil.svg").write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_mobile("night-city-crew", "0 0 480 540")
    build_mobile("night-city", "435 0 525 996")
    build_mobile("contacto", "49 6 502 334")
    build_mobile("atlantis", "455 0 482 334")
    build_mobile("arcadia", "450 0 490 452")
    build_mobile("loki-code-guide", "0 0 384 186")
