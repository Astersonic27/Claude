# Kudos System Specification

**Status:** Approved - implementation follows this document.
**Initial request:** *"Create a feature for our internal web app that allows users to give 'kudos' to their colleagues. A user should be able to select another user from a list, write a short message of appreciation, and submit it. There should also be a public feed on the main dashboard where all recently submitted kudos are visible."*

**Architect additions to the first draft** (marked **[ARCH]** below): administrator moderation (user story 8), the moderation fields on the `kudos` table plus the `moderation_log` audit table, and abuse controls (rate limit, duplicate detection, self-kudos block).

---

## 1. Functional Requirements

### 1.1 User stories

| # | Story |
|---|-------|
| 1 | As an employee, I can sign in so that kudos are attributed to me. |
| 2 | As a user, I can select a colleague from a dropdown list (excluding myself). |
| 3 | As a user, I can write a message of appreciation (1-500 characters). |
| 4 | As a user, I can submit the kudos, which is stored in the database. |
| 5 | As a user, I get clear inline errors when my input is invalid or rejected. |
| 6 | As a user, I can view a feed of recent kudos on the main dashboard, newest first, and load older ones. |
| 7 | As a user, I can use the dashboard on a phone, tablet or desktop. |
| 8 | **[ARCH]** As an administrator, I can **hide** (reversibly) or **delete** (permanently) an inappropriate kudos message, optionally recording a reason, so that it no longer appears in the public feed. |
| 9 | **[ARCH]** As an administrator, I can see hidden kudos and **unhide** one hidden by mistake. |
| 10 | **[ARCH]** As an administrator, I want every moderation action recorded (who, when, why) so decisions can be audited. |

### 1.2 Acceptance criteria

**Authentication and authorization (1)**
- Anonymous requests to `/` redirect to `/login`; anonymous API calls return `401`.
- Wrong username or password returns `401` with one generic message (does not reveal which was wrong).
- Passwords are stored only as salted hashes.
- Moderation endpoints return `403` for non-administrators.

**Giving kudos (2-5)**
- The recipient list contains all active users except the current user.
- Message is trimmed; empty or whitespace-only messages are rejected (`422`); messages over 500 characters are rejected (`422`); control characters are stripped.
- `recipient_id` must be an integer identifying an active user, otherwise `422`. Giving kudos to yourself is rejected (`422`).
- **[ARCH] Spam:** a sender may give at most 5 kudos per rolling hour (configurable); the 6th returns `429` with a friendly message.
- **[ARCH] Duplicates:** an identical message (case-insensitive) from the same sender to the same recipient within 24 hours returns `409`.
- On success the API returns `201` with the stored kudos, the form clears, and the feed refreshes.
- Validation errors name the offending field and are shown beside it.

**Public feed (6, 7)**
- Shows sender, recipient, message and time for **visible** kudos only, newest first, 20 per page, with a "Load more" control (cursor pagination).
- Every authenticated user can see the feed; hidden or deleted kudos never appear in it.
- Layout is one column below 800px and two columns above; controls are keyboard accessible and error text has `role="alert"`.

**Moderation (8-10) [ARCH]**
- Hide sets `is_visible = 0` and stores `moderated_by`, `moderated_at`, `moderation_reason`; the kudos disappears from the public feed immediately.
- Unhide restores visibility.
- Delete removes the row permanently; a snapshot of the message is kept in `moderation_log`.
- Every hide/unhide/delete writes a `moderation_log` row. Unknown ids return `404`.
- Administrators see hidden items (marked "Hidden") with Hide/Unhide/Delete controls on the dashboard.

### 1.3 Out of scope
Notifications, reactions or comments, editing kudos after posting, SSO integration, user management UI (users are seeded), automated profanity filtering.

---

## 2. Technical Design

### 2.1 Architecture
Python 3 / Flask application with server-rendered pages, a JSON API, SQLite storage and a small vanilla-JS front end. No build step. SQLite keeps the demo self-contained; the schema is portable to PostgreSQL.

### 2.2 Database schema

**users**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| username | TEXT UNIQUE NOT NULL | login name |
| display_name | TEXT NOT NULL | shown in dropdown and feed |
| password_hash | TEXT NOT NULL | salted hash |
| is_admin | INTEGER NOT NULL DEFAULT 0 | 0/1 |
| is_active | INTEGER NOT NULL DEFAULT 1 | 0/1 |

**kudos**

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | cursor for pagination |
| sender_id | INTEGER FK users.id NOT NULL | |
| recipient_id | INTEGER FK users.id NOT NULL | CHECK sender_id <> recipient_id |
| message | TEXT NOT NULL | CHECK length 1-500 |
| created_at | TEXT NOT NULL | UTC ISO-8601, default now |
| **is_visible** **[ARCH]** | INTEGER NOT NULL DEFAULT 1 | 0/1; **default true** |
| **moderated_by** **[ARCH]** | INTEGER FK users.id NULL | admin who last hid/unhid |
| **moderated_at** **[ARCH]** | TEXT NULL | time of last moderation |
| **moderation_reason** **[ARCH]** | TEXT NULL | free text, max 300 chars |

Indexes: `(is_visible, id DESC)` for the feed; `(sender_id, created_at)` for rate-limit and duplicate checks.

**moderation_log [ARCH]**: `id`, `kudos_id` (no FK, so rows survive deletion), `admin_id` FK users.id, `action` (`hide` | `unhide` | `delete`), `reason`, `message` (snapshot), `created_at`.

Relationships: users 1-N kudos (as sender), users 1-N kudos (as recipient), users 1-N moderation_log.

### 2.3 API endpoints
All endpoints except `POST /login` require a session. All state-changing requests require the `X-CSRF-Token` header. Errors are JSON `{ "error": "...", "fields": {...} }`.

| Method & path | Auth | Purpose | Success | Errors |
|---|---|---|---|---|
| GET `/` | user | Dashboard page | 200 | 302 to /login |
| GET/POST `/login` | none | Sign in form | 302 | 401 |
| POST `/logout` | user | End session | 302 | 403 |
| GET `/api/users` | user | Colleagues except self | 200 `{users:[{id,name}]}` | 401 |
| POST `/api/kudos` | user | Give kudos. Body `{recipient_id:int, message:str}` | 201 `{kudos}` | 400, 401, 403, 409 duplicate, 422 validation, 429 rate limit |
| GET `/api/kudos?limit&before_id` | user | Public feed, visible only, newest first (limit 1-50, default 20) | 200 `{kudos:[], next_before_id}` | 400, 401 |
| GET `/api/admin/kudos?status=all\|hidden\|visible` | admin | Moderation list (latest 100) incl. hidden | 200 | 400, 401, 403 |
| POST `/api/admin/kudos/{id}/hide` | admin | Hide. Body `{reason?}` | 200 | 403, 404 |
| POST `/api/admin/kudos/{id}/unhide` | admin | Unhide | 200 | 403, 404 |
| DELETE `/api/admin/kudos/{id}` | admin | Permanently delete. Body `{reason?}` | 200 | 403, 404 |

### 2.4 Frontend components

```
dashboard.html
 |- Topbar (user name, admin badge, sign-out form)
 |- GiveKudosForm  (recipient <select>, message <textarea> + live counter, inline errors, status)
 |- Feed (<ul>)
      |- FeedItem (sender -> recipient, time, message)
      |    '- AdminControls (Hide/Unhide, Delete)  -- admins only
      '- LoadMore button (cursor pagination)
```
Interactions: page load fetches `/api/users` and the feed; a successful submit clears the form and reloads the feed; moderation actions confirm/prompt, call the API, then reload the feed.

### 2.5 Security considerations
- **Authentication:** server-side signed session cookie (HttpOnly, SameSite=Lax); session reset on login; salted password hashes.
- **Authorization:** checked on the server for every admin endpoint; the UI hiding buttons is cosmetic only.
- **CSRF:** per-session token required on every state-changing request.
- **XSS / sanitization:** messages are stored as plain text and rendered only with `textContent`; strict Content-Security-Policy (`default-src 'self'`, no inline scripts); `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` headers.
- **Injection:** parameterized SQL only.
- **Input limits:** 16 KB request body cap; type, length and range validation; control characters stripped.
- **Abuse:** per-sender hourly limit, duplicate detection, no self-kudos.
- **Production notes:** set `SECRET_KEY` from the environment, serve over HTTPS, set `SESSION_COOKIE_SECURE`, replace seeded demo passwords with the portal's SSO.

### 2.6 Performance considerations
- Cursor (keyset) pagination on the indexed `id`, so cost does not grow with page depth.
- Feed query is a single join over indexed columns; page size capped at 50.
- Possible later: short-TTL cache of the first feed page, WAL mode for write concurrency.

### 2.7 Error handling and logging
- Consistent JSON error shape; `404`, `413` and `500` handled globally; unexpected exceptions are logged with a stack trace and return a generic message (no internal details leaked).
- Info logs for each created kudos and each moderation action (ids only, not message bodies).
- Database writes use explicit commits; a failed insert returns `500` and is logged.

---

## 3. Implementation Plan

| # | Task | Depends on |
|---|------|------------|
| 1 | Project scaffold, `requirements.txt`, `.gitignore` | - |
| 2 | Schema (`users`, `kudos` with moderation fields, `moderation_log`), DB helpers | 1 |
| 3 | App factory, security headers, CSRF, global error handlers | 1 |
| 4 | Authentication: login/logout, `login_required`, `admin_required` | 2, 3 |
| 5 | Users list and create-kudos API with validation, rate limit, duplicate check | 4 |
| 6 | Public feed API with cursor pagination | 5 |
| 7 | Moderation API: hide, unhide, delete, admin list, audit log | 5, 6 |
| 8 | Front end: templates, responsive CSS, JS (form, feed, admin controls) | 5-7 |
| 9 | Seed script for demo users | 2 |
| 10 | Automated tests (auth, validation, abuse, pagination, XSS, moderation) | 4-7 |
| 11 | README and deployment notes | all |

**Testing strategy:** `unittest` with Flask's test client against a temporary SQLite file; each acceptance criterion above maps to at least one test (18 tests). Manual smoke test of login, post and feed against a running server.

**Deployment considerations:** run behind a production WSGI server (e.g. gunicorn) over HTTPS; `SECRET_KEY` and the database path come from the environment; back up the SQLite file or migrate to PostgreSQL for multi-instance deployments; run `python seed.py` only for demo or development data.
