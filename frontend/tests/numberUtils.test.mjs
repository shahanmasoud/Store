import assert from "node:assert/strict";
import test from "node:test";

import {
  moneyInputValue,
  canonicalDecimalInput,
  formatDecimalInput,
  normalizeDecimal,
  normalizeMoney,
  toEnglishDigits,
  toPersianDigits,
} from "../src/numberUtils.ts";

test("normalizes Persian and Arabic digits without losing identifiers", () => {
  assert.equal(toEnglishDigits("۰۹١۲-۳"), "0912-3");
  assert.equal(toPersianDigits("0912-3"), "۰۹۱۲-۳");
});

test("keeps decimal editing canonical while formatting Persian grouped output", () => {
  assert.equal(canonicalDecimalInput("۱٬۲۳۴٫۵۰"), "1234.50");
  assert.equal(canonicalDecimalInput("0012."), "12.");
  assert.equal(canonicalDecimalInput("1,2x3.4.5"), "123.45");
  assert.equal(formatDecimalInput("1234567.50"), "۱٬۲۳۴٬۵۶۷٫۵۰");
  assert.equal(formatDecimalInput("12."), "۱۲٫");
  assert.equal(formatDecimalInput(""), "");
});

test("formats typed toman values and returns canonical rial", () => {
  assert.equal(normalizeMoney("۱٬۲۳۴٬۵۶۷"), 12_345_670);
  assert.equal(normalizeMoney("1,234,567"), 12_345_670);
  assert.equal(moneyInputValue(12_345_670), "۱٬۲۳۴٬۵۶۷");
});

test("uses one unambiguous policy for decimal quantities", () => {
  assert.equal(normalizeDecimal("۲٫۵"), 2.5);
  assert.equal(normalizeDecimal("1,234.5"), 1234.5);
  assert.equal(normalizeDecimal("۱٬۲۳۴٫۵"), 1234.5);
  assert.equal(normalizeDecimal("1,5"), 0);
  assert.equal(normalizeDecimal("1٬23"), 0);
  assert.equal(normalizeDecimal("1.2.3"), 0);
});
