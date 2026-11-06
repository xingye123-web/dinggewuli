"""把 Noto Serif SC 裁成网站要用的小字体文件。

网站的标题用宋体，但完整的中文字体有十几 MB，所以只截出 web/fonts/serif-text.txt 里列出的字。
另外截一份常规粗细的拉丁和希腊字母，给物理量符号用（G、h、η、ρ 这些）。
Noto Serif SC 是 SIL OFL 1.1 许可，可以裁剪后分发；裁出的字体改名为 Dingge Serif，许可信息保留在字体的 name 表里。

用法：python scripts/build_fonts.py [Noto Serif SC 可变字体的路径]
改了用宋体的标题后，把新字加进 web/fonts/serif-text.txt 再运行一次。
"""

import string
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Windows\Fonts\NotoSerifSC-VF.ttf")
TEXT = ROOT / "web" / "fonts" / "serif-text.txt"
OUT = ROOT / "web" / "public" / "fonts"
FAMILY = "Dingge Serif"
GREEK = "αβγδεηθλμνπρστφωΔΘΛΣΦΩ"
LATIN = string.ascii_letters + string.digits + " .,:;!?()[]/+-=×÷−%'\""


def build(weight, text, name):
    font = TTFont(SOURCE)
    font = instancer.instantiateVariableFont(font, {"wght": weight})
    options = subset.Options()
    options.flavor = "woff"
    options.name_IDs = ["*"]  # 保留版权和许可证说明
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    style = "Bold" if weight >= 600 else "Regular"
    for record in font["name"].names:
        if record.nameID in (1, 16):
            record.string = FAMILY
        elif record.nameID in (2, 17):
            record.string = style
        elif record.nameID == 4:
            record.string = f"{FAMILY} {style}"
        elif record.nameID == 6:
            record.string = f"DinggeSerif-{style}"
    font.flavor = "woff"
    path = OUT / name
    font.save(path)
    print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.0f} KB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    headings = "".join(sorted(set(TEXT.read_text(encoding="utf-8")) - set("\r\n")))
    build(700, headings + LATIN + GREEK, "dingge-serif-700.woff")
    build(400, LATIN + GREEK, "dingge-serif-400.woff")


if __name__ == "__main__":
    main()
