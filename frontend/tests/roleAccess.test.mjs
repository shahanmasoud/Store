import assert from "node:assert/strict";
import test from "node:test";

import { canAccessAdminView } from "../src/roleAccess.ts";

const permissionViews = [
  ["can_sales", ["sales"]],
  ["can_catalog_inventory", ["products", "purchase", "inventory"]],
  ["can_ledger", ["ledger"]],
  ["can_cheques_reports", ["cheques", "reports"]],
];
const operationalViews = permissionViews.flatMap(([, views]) => views);

for (let mask = 0; mask < 16; mask += 1) {
  test(`role permission union ${mask.toString(2).padStart(4, "0")}`, () => {
    const user = { is_superuser: false };
    permissionViews.forEach(([permission], index) => { user[permission] = Boolean(mask & (1 << index)); });
    assert.equal(canAccessAdminView(user, "dashboard"), true);
    assert.equal(canAccessAdminView(user, "reminders"), Boolean(mask & 0b1101));
    for (const view of operationalViews) {
      const permissionIndex = permissionViews.findIndex(([, views]) => views.includes(view));
      assert.equal(canAccessAdminView(user, view), Boolean(mask & (1 << permissionIndex)), view);
    }
    assert.equal(canAccessAdminView(user, "online"), false);
    assert.equal(canAccessAdminView(user, "users"), false);
  });
}

test("superuser can access every admin view and guests cannot", () => {
  const views = ["dashboard", "reminders", ...operationalViews, "online", "users"];
  for (const view of views) {
    assert.equal(canAccessAdminView({ is_superuser: true }, view), true);
    assert.equal(canAccessAdminView(null, view), false);
  }
});
