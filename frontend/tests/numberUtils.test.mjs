import assert from "node:assert/strict";
import test from "node:test";

import {
  moneyInputValue,
  normalizeDecimal,
  normalizeMoney,
  toEnglishDigits,
  toPersianDigits,
} from "../src/numberUtils.ts";

test("normalizes Persian and Arabic digits without losing identifiers", () => {
  assert.equal(toEnglishDigits("۰۹١۲-۳"), "0912-3");
  assert.equal(toPersianDigits("0912-3"), "۰۹۱۲-۳");
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
