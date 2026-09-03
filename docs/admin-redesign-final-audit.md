# Admin redesign: final dashboard, navigation, and regression audit

## Scope

This final slice verifies the admin panel as one coherent product after all functional sections have been redesigned. It must fix cross-cutting issues rather than add unrelated business scope.

## Confirmed gaps

- Dashboard sales, collection, stock-warning, and cheque-due numbers are hard-coded demo values instead of current API data.
- Changing sections preserves the previous document scroll position; a newly opened section can start halfway down the page.
- Mobile navigation is a horizontally scrolling desktop menu with a visible scrollbar and hidden destinations.
- The production JavaScript bundle is above the 500 kB warning threshold and has grown with every section because all admin views live in one eager `App.tsx` module.
- A hard-coded Jalali date was used across forms; the reports/online slice is responsible for replacing it with a runtime Tehran/Persian-calendar default, and this audit must verify every consumer.
- Accessibility has not yet been checked end-to-end for keyboard focus, modal focus return, landmark/heading hierarchy, control names, status announcements, reduced motion, and contrast.

## Deliverable

- Replace dashboard placeholders with authenticated report/inventory/dues data and complete loading, error/retry, and honest empty states.
- Provide a simple responsive navigation pattern: persistent sidebar on desktop and an accessible drawer/menu or compact primary navigation on mobile, with no horizontal scrollbar or hidden required section.
- Reset/focus the main section heading when navigation changes while preserving expected browser behavior.
- Split admin section code into lazy-loaded modules or another maintainable route/module boundary so the initial bundle warning is materially reduced; do not merely raise the warning limit.
- Remove obsolete duplicate CSS and dead legacy helpers when evidence shows they are no longer used.
- Preserve RTL, Persian labels, the green/cream visual identity, touch targets of at least 44px, and layout without overlap.

## Regression matrix

- Desktop: dashboard plus all eight destinations open, load their populated/empty state, and return to dashboard.
- Mobile `390 × 844`: navigation exposes every destination, opens at the top, document width does not exceed the viewport, dialogs fit, and primary actions remain reachable.
- Keyboard: reach navigation, primary forms, filters, list actions, and dialogs in a meaningful order; focus is visible.
- Runtime: no console errors during the complete route tour and no unauthorized request loop.
- Automated: full backend suite, TypeScript, production build, Alembic upgrade from empty database, and migration downgrade/upgrade checks pass.
- Git: only the feature branch is committed; no merge or push to `main` occurs before review in the original chat.

## Manual test

1. Sign in at desktop width and verify dashboard numbers correspond to the underlying reports rather than placeholder text.
2. Scroll within a long section, choose another destination, and verify its heading starts in view and receives sensible focus.
3. At `390 × 844`, open the mobile navigation and visit every destination; confirm there is no horizontal navigation scrollbar or clipped item.
4. Traverse the dashboard, one create form, one filter, and one confirmation dialog using only the keyboard.
5. Reload the admin page, repeat the route tour, and check the browser console for errors.

## Implemented result

- The dashboard now loads today's journal, inventory summary, and due items from authenticated APIs. It has explicit loading, error/retry, and truthful zero states.
- The desktop sidebar remains persistent. At widths up to 920px it is replaced by a labelled Material UI drawer containing the dashboard and all eight management destinations; the old horizontal navigation is no longer exposed.
- Every section change closes the drawer, resets the document to the top, and moves focus to the current level-one heading with a visible focus ring.
- The storefront shell and admin application now form a real lazy boundary. The verified production build emits a 448.27 kB entry chunk and a separate 185.77 kB admin chunk, with no JavaScript chunk above 500 kB.
- Mobile header controls, drawer destinations, and tested dialog actions meet the 44px touch-target minimum.

## Verification evidence

- Backend: `96 passed` in the full suite.
- Frontend: TypeScript and the Vite production build pass; `git diff --check` is clean.
- SQLite: a fresh database upgrades from base to head, downgrades from revision `0007` to `0006`, and upgrades to head again.
- Desktop route tour: dashboard and all eight destinations render at the top with no console errors or document overflow.
- Mobile route tour at `390 × 844`: all nine drawer destinations are reachable; every destination focuses its H1 at scroll position zero; document width remains within the viewport.
- Mobile dialog check: the reorder-level dialog fits inside the viewport and both actions are 44px high. No consequential action was submitted during browser QA.
