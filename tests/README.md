# LIMS Test Suite

This directory hosts the cross-cutting integration tests (Playwright E2E) for
the LIMS app. The unit and API tests for each side live next to their code:

| Layer | Location | Runner | What it covers |
|---|---|---|---|
| Backend unit + API | `backend/tests/` | `pytest` | FastAPI routers via TestClient, service-layer unit tests, auth/permission dependencies, master-data assembly |
| Frontend unit + component | `frontend/components/__tests__/`, `frontend/src/**/__tests__/`, `frontend/app/__tests__/` | `vitest` + `@testing-library/react` (jsdom) | Sidebar role-gating, AuthGate branches, AccountPage table+modal, AuthContext lifecycle, service-layer axios wrappers |
| End-to-end | `tests/e2e/tests/*.spec.ts` | `@playwright/test` (Chromium) | Full browser flow through the running stack: login, role-based sidebar, account create, logout cookie clearance |

---

## Running each layer

### Backend (pytest)

```bash
cd backend
. .venv/bin/activate                  # macOS/Linux
pytest                                 # full suite
pytest --cov=app                       # with coverage
pytest tests/e_tests/test_auth.py -v   # one file
```

The conftest provisions a `lims_test` database against the running Postgres
instance (`make infra` brings it up).

### Frontend (vitest)

```bash
cd frontend
npm test                       # all unit/component tests
npm run test:coverage          # also writes HTML report to frontend/coverage/
```

Coverage uses `@vitest/coverage-v8` and reports against `components/` + `src/`.

**Current coverage** (as of this commit):

| Metric | % |
|---|---|
| Statements | 92.3 |
| Branches | 79.5 |
| Functions | 88.4 |
| Lines | 92.2 |

Target was ≥70% on `components/` + `src/`. Met comfortably.

### E2E (Playwright)

```bash
# 1. Bring up the full stack
make infra                              # postgres + redis
cd backend && . .venv/bin/activate
make -C .. migrate                      # alembic upgrade head
make -C .. seed                         # creates the four seed accounts
make -C .. dev-backend &                # uvicorn :8000
cd ../frontend && npm run dev &         # next :3000

# 2. Install browsers (one-time)
cd tests/e2e
npm install
npx playwright install --with-deps chromium

# 3. Run
npx playwright test                     # all specs, headless
npx playwright test --headed            # see the browser
npx playwright show-report              # open the last HTML report
```

`workers: 1` is enforced in `playwright.config.ts` because the suite shares a
single seed DB — parallel runs would race on user-create state.

Outputs:

- HTML report → `tests/e2e/playwright-report/`
- Traces / screenshots / videos for failures → `tests/e2e/test-results/`

---

## E2E coverage matrix

| Spec | Account used | What it asserts |
|---|---|---|
| `auth-happy.spec.ts` | `admin@example.com` / `Admin1234` | Login -> sidebar shows `系統` section -> `/account` lists ≥4 seed users including `admin@example.com` |
| `auth-role-gating.spec.ts` | `requester@example.com` / `Reque1234` | Plant user sees `委託流程` (`委託單管理` + `收樣管理`) but NOT `結案與倉儲` / `系統` / `簽核管理` / `帳號管理` / `OVERVIEW`. `/account` page still renders but `+ 建立使用者` is gated and the row body shows the read-failure / empty message |
| `account-create.spec.ts` | `admin@example.com` / `Admin1234` | Open modal, fill unique email (`e2e-<timestamp>@example.com`), submit, new row appears |
| `logout.spec.ts` | `admin@example.com` / `Admin1234` | Click `登出` in the sidebar footer → LoginForm reappears → `access_token` cookie is cleared |

Seed accounts (from `backend/scripts/seed_dev.py`):

| Email | Password | Role | Expected sidebar |
|---|---|---|---|
| `admin@example.com` | `Admin1234` | system_admin | All sections (wildcard `*` permission) |
| `supervisor@example.com` | `Super1234` | lab_supervisor | OVERVIEW, 委託流程 (incl. 簽核管理), 執行與機台, 結案與倉儲 |
| `engineer@example.com` | `Engin1234` | lab_engineer | Execution-side items, no approvals, no account admin |
| `requester@example.com` | `Reque1234` | plant_user | `委託流程` (orders + samples), `執行與機台` (only 樣品交接) |

---

## Debugging tips for failing E2E

1. **`Error: page.goto: net::ERR_CONNECTION_REFUSED`** — frontend dev server isn't running. Check `curl localhost:3000`.
2. **`API request failed: 401`** in the test output — the seed accounts aren't in the DB. Re-run `make seed`.
3. **`+ 建立使用者` not found** — admin user lost its `users:create` permission. Check the `permissions` table (`master_data` API or psql).
4. **Modal opens but submit hangs** — confirm `/api/users` POST works manually:
   ```bash
   curl -c c.txt -X POST http://localhost:8000/api/auth/login \
        -H 'Content-Type: application/json' \
        -d '{"email":"admin@example.com","password":"Admin1234"}'
   curl -b c.txt -X POST http://localhost:8000/api/users \
        -H 'Content-Type: application/json' \
        -d '{"email":"t@x.c","name":"T","password":"Passw0rd!"}'
   ```
5. **Cookie assertion fails in `logout.spec.ts`** — backend may be returning the cookie with a wrong domain. Inspect the response of `POST /api/auth/logout`; it must `Set-Cookie: access_token=; Max-Age=0` for the test cookie store to clear it.
6. **Flaky table-count assertions** — TanStack Query may still be fetching. The specs already use `await expect(...).toBeVisible()`; if you add a new assertion, prefer the auto-retrying matchers over `toHaveCount(n)` with a hard number.
7. **Run a single spec with traces:**
   ```bash
   cd tests/e2e
   npx playwright test logout.spec.ts --trace on --headed
   npx playwright show-trace test-results/<folder>/trace.zip
   ```

---

## Notes

- One known-failing backend test: `tests/e_tests/test_master_data_service.py::test_gather_returns_enums_and_db_collections` asserts `"info" in severities` but the enum exposes `["low","medium","high","critical"]`. The test is wrong but per task constraint it was not modified — needs a separate ticket.
- CI runs the same commands in `.github/workflows/ci.yml`; the devops-engineer agent owns those files.
