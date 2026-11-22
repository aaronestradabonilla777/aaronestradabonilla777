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
    if name == "contacto":
        root.set("class", "compact")
        # Keep the theatre on the quay between the two billboards in the close-up.
        root.find(".//*[@id='projection-theatre']").set("transform", "translate(-47 107) scale(.62)")
    if name == "night-city":
        root.find(".//*[@id='identity']").set("transform", "translate(433 34) scale(.51)")
        root.find(".//*[@id='wordmark']").set("transform", "translate(54 100) scale(.60) skewX(-12)")
        root.find(".//*[@id='tower-district']").attrib.update(x="435", width=width, viewBox="219 0 525 324")
        root.find(".//*[@id='night-market']").attrib.update(x="435", width=width, viewBox="170 0 525 274")
        root.find(".//*[@id='stack-icons']").set("transform", "translate(45 222) scale(1.35)")
        root.find(".//*[@id='title-shade']").attrib.update(x="435", width="322", opacity=".64")
    if name == "atlantis":
        root.find(".//*[@id='caption']").set("transform", "translate(22 32) scale(.83)")
        root.find(".//*[@id='city']").set("transform", "translate(301 292) scale(.87)")
        root.find(".//*[@id='sunlight']").set("transform", "translate(-323 0)")
        root.find(".//*[@id='shade']").attrib.update(x2="0", y2="1")
        root.find(".//*[@id='caption-shade']").attrib.update(width=width, height="174", opacity=".64")
    if name == "arcadia":
        root.find(".//*[@id='caption']").set("transform", "translate(338 35) scale(.78)")
        root.find(".//*[@id='wrist']").set("transform", "translate(724 367)")
        root.find(".//*[@id='caption-shadow']").attrib.update(x="315", width="225")
        visor = root.find(".//*[@id='visor']")
        visor.set("transform", "translate(315 0) scale(.5104167 1)")
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
    build_mobile("night-city", "435 0 525 996")
    build_mobile("contacto", "49 6 502 334")
    build_mobile("atlantis", "0 0 482 334")
    build_mobile("arcadia", "315 0 490 452")
    build_mobile("loki-code-guide", "0 0 384 186")
