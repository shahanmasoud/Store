const latinDigits = "0123456789";
const persianDigits = "۰۱۲۳۴۵۶۷۸۹";
const arabicDigits = "٠١٢٣٤٥٦٧٨٩";

export function toEnglishDigits(value: string | number) {
  return String(value).replace(/[۰-۹٠-٩]/g, (digit) => {
    const persianIndex = persianDigits.indexOf(digit);
    if (persianIndex >= 0) return latinDigits[persianIndex];
    const arabicIndex = arabicDigits.indexOf(digit);
    return arabicIndex >= 0 ? latinDigits[arabicIndex] : digit;
  });
}

export function toPersianDigits(value: string | number) {
  return String(value).replace(/\d/g, (digit) => persianDigits[Number(digit)]);
}

export function parseLocalizedNumber(value: unknown) {
  const normalized = toEnglishDigits(String(value ?? ""))
    .replace(/[,\s٬،]/g, "")
    .replace(/[٫/]/g, ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

export function rialToToman(value: number) {
  return Math.round(Math.max(0, value) / 10);
}

export function tomanToRial(value: number) {
  return Math.round(Math.max(0, value) * 10);
}

export function moneyInputValue(valueRial: number) {
  return valueRial > 0 ? rialToToman(valueRial).toLocaleString("fa-IR") : "";
}

export function normalizeMoney(value: unknown) {
  return tomanToRial(parseLocalizedNumber(value));
}

export function formatRial(value: number) {
  return `${rialToToman(value).toLocaleString("fa-IR")} تومان`;
}

export function formatDecimal(value: number | string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toLocaleString("fa-IR") : toPersianDigits(value);
}

export function normalizeDecimal(value: unknown) {
  const localized = toEnglishDigits(String(value ?? "0")).trim();
  const validPlain = /^\d+(?:[.٫]\d+)?$/.test(localized);
  const validGrouped = /^\d{1,3}([,٬])\d{3}(?:\1\d{3})*(?:[.٫]\d+)?$/.test(localized);
  if (!validPlain && !validGrouped) return 0;
  const parsed = Number(localized.replace(/[,٬]/g, "").replace("٫", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
}

/**
 * Canonical editing contract for decimal fields: ASCII digits, at most one dot,
 * and no grouping separators. A trailing dot is kept so decimal typing does not
 * jump or lose the user's in-progress value.
 */
export function canonicalDecimalInput(value: unknown) {
  const localized = toEnglishDigits(String(value ?? ""))
    .replace(/[\s,٬،]/g, "")
    .replace(/٫/g, ".")
    .replace(/[^\d.]/g, "");
  const [integer = "", ...fractionParts] = localized.split(".");
  const hasDecimal = localized.includes(".");
  const normalizedInteger = integer.replace(/^0+(?=\d)/, "");
  return `${normalizedInteger}${hasDecimal ? `.${fractionParts.join("")}` : ""}`;
}

export function formatDecimalInput(value: unknown) {
  const canonical = canonicalDecimalInput(value);
  if (!canonical) return "";
  const [integer, fraction] = canonical.split(".");
  const grouped = (integer || "0").replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
  return toPersianDigits(`${grouped}${fraction !== undefined ? `٫${fraction}` : ""}`);
}
