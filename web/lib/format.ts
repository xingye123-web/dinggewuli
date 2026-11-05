const SCIENTIFIC_ABOVE = 10000;
const SCIENTIFIC_BELOW = 0.001;

function plain(value: number, digits: number) {
  const text = value.toFixed(digits);
  return text.includes(".") ? text.replace(/\.?0+$/, "") : text;
}

function needsScientific(value: number) {
  const size = Math.abs(value);
  return value !== 0 && (size > SCIENTIFIC_ABOVE || size < SCIENTIFIC_BELOW);
}

function scientific(value: number) {
  let exponent = Math.floor(Math.log10(Math.abs(value)));
  let mantissa = Number((value / 10 ** exponent).toFixed(4));
  if (Math.abs(mantissa) >= 10) {
    mantissa = Number((mantissa / 10).toFixed(4));
    exponent += 1;
  }
  return `${plain(mantissa, 4)}×10<sup>${exponent}</sup>`;
}

/**
 * 网页上的数字写法，和视频里一致：绝对值大于 10000 或小于 0.001 写成 1.5×10<sup>4</sup>，
 * 否则保留 digits 位小数。返回的文字要交给 Markup 显示。
 */
export function formatNumber(value: number, digits: number): string {
  return needsScientific(value) ? scientific(value) : value.toFixed(digits);
}

/** 模型给的数值可能是数字，也可能是文字，只有数字需要转换，小数去掉末尾的 0。 */
export function formatAny(value: number | string | undefined): string {
  if (typeof value !== "number") return value ?? "";
  return needsScientific(value) ? scientific(value) : plain(value, 4);
}
