"""数字的写法。绝对值大于 10000 或小于 0.001 的数用科学计数法，比如 15000 写成 1.5×10⁴，0.0008 写成 8×10⁻⁴。"""

import math
import re

SCIENTIFIC_ABOVE = 10000
SCIENTIFIC_BELOW = 0.001
_SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
# spoken_number 的读法，字幕要把它换回符号写法
_SPOKEN = re.compile(r"(-?\d+(?:\.\d+)?)乘10的(负?)(\d+)次方")


def _plain(value, digits):
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _parts(value):
    """拆成 系数 × 10 的 指数，系数最多保留 4 位小数。"""
    exponent = math.floor(math.log10(abs(value)))
    mantissa = round(value / 10**exponent, 4)
    if abs(mantissa) >= 10:
        mantissa, exponent = round(mantissa / 10, 4), exponent + 1
    return _plain(mantissa, 4), exponent


def needs_scientific(value):
    return value is not None and value != 0 and not (SCIENTIFIC_BELOW <= abs(value) <= SCIENTIFIC_ABOVE)


def scientific(value):
    """不论大小都写成科学计数法，坐标轴刻度要整根轴统一时用。"""
    mantissa, exponent = _parts(value)
    return f"{mantissa}×10{str(exponent).translate(_SUPERSCRIPT)}"


def sci(value, digits=2):
    """画面上显示数字时用它：很大或很小的数写成 1.5×10⁴，否则保留 digits 位小数。"""
    if value is None:
        return "—"
    return scientific(value) if needs_scientific(value) else f"{value:.{digits}f}"


def board_number(value, digits):
    """板书里的数字，用上标标签。"""
    if not needs_scientific(value):
        return _plain(value, digits)
    mantissa, exponent = _parts(value)
    return f"{mantissa}×10<sup>{exponent}</sup>"


def spoken_number(value, digits):
    """旁白里的数字，按老师的读法写出来，比如 1.5乘10的4次方、5乘10的负5次方。"""
    if not needs_scientific(value):
        return _plain(value, digits)
    mantissa, exponent = _parts(value)
    sign = "负" if exponent < 0 else ""
    return f"{mantissa}乘10的{sign}{abs(exponent)}次方"


def to_display(text):
    """字幕和讲解文字：把读法换回符号写法，配音仍然读中文。"""
    def replace(match):
        exponent = ("-" if match.group(2) else "") + match.group(3)
        return f"{match.group(1)}×10{exponent.translate(_SUPERSCRIPT)}"

    return _SPOKEN.sub(replace, text)
