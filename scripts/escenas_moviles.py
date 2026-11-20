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
    if name == "night-city":
        root.find(".//*[@id='identity']").set("transform", "translate(433 34) scale(.51)")
        root.find(".//*[@id='stack-icons']").set("transform", "translate(45 222) scale(1.35)")
        root.find(".//*[@id='title-shade']").attrib.update(x="435", width="322", opacity=".64")
    root.insert(0, ET.Comment(f" Generated from {name}.svg by scripts/escenas_moviles.py "))
    content = ET.tostring(root, encoding="unicode")
    (ASSETS / f"{name}-movil.svg").write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_mobile("night-city", "435 0 525 332")
    build_mobile("contacto", "49 6 502 334")
