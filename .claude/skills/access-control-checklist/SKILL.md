---
name: access-control-checklist
description: Diagnostic procedures for IDOR/BOLA, privilege escalation (horizontal & vertical), and business logic bypass vulnerabilities in web applications. Use when testing whether a server actually enforces authorization on objects, roles, or multi-step workflows — as opposed to relying on client-side or UI-only restrictions.
---

# Access Control Diagnostic Procedures

Two check families below. Both hinge on one question: is the restriction enforced **server-side**, on every request, or only implied by the UI / trusted from the client?

## Family 1 — IDOR / BOLA / Privilege Escalation

### Check 1 — Enumerate object references
List every endpoint that takes an object identifier as input: path param (`/user/:id`), query param (`?id=`, `?order_id=`), body field, or even an opaque token/cookie value. Include IDs that appear indirectly (hidden form fields, JSON responses that echo an id you didn't request).

### Check 2 — Static check for ownership enforcement
For each identified endpoint, read the handler. Look for a line that ties the object being accessed to the *authenticated* identity — not just "is logged in," but "is logged in **as the owner/appropriate role**":
- Good sign: `if resource.user_id != session.user.id: abort(403)`
- Bad sign: handler fetches `Resource.find(params[:id])` and returns it with no ownership comparison at all
- Ambiguous: ownership check exists but is applied inconsistently across GET/PUT/DELETE for the same resource — check all verbs, not just one

Record per endpoint: check present (yes/no/partial) and where.

### Check 3 — Horizontal escalation (same role, different object)
With User A authenticated, note an object id that belongs to User A. With User B authenticated (different account, same privilege level), request User A's object id. If User B can read/modify/delete it, that's a CONFIRMED IDOR/BOLA.
Test across the full CRUD surface for that resource — a fix on GET doesn't imply a fix on PUT/DELETE.

### Check 4 — Vertical escalation (lower role reaching higher-role functionality)
Identify endpoints intended for elevated roles (admin panels, `/admin/*`, role-management APIs, feature flags). With a low-privilege identity:
- Try direct access to the endpoint/route even if it's not linked from the low-priv UI
- Try role/parameter tampering: a hidden `role` or `is_admin` field in a request body, a JWT/cookie claim that's client-readable or client-writable
- Try omitted-auth-check endpoints: some apps check role only in the UI layer, not the API layer

### Check 5 — Indirect object reference / mass assignment
Check whether the app uses direct database ids (sequential, guessable) vs indirect references (per-session tokens). Sequential ids make Check 3 easy to script across a range. Also check whether update endpoints accept extra fields beyond what the form exposes (mass assignment) — e.g., PATCH `/profile` accepting `role: admin` even though the UI only shows a name field.

### Using code-intelligence tools
When "go to definition" / "find references" tooling is available, use it to:
- Jump from a route definition to its handler, then to any authorization decorator/middleware it calls
- Find all callers of a shared "get resource by id" helper — if that helper doesn't enforce ownership, every caller inherits the gap
- Find references to a role-check function to see which endpoints call it and which conspicuously don't

## Family 2 — Business Logic Bypass

Business logic issues are harder to grep for — they're violations of an intended *process*, not a missing permission check. Reason from the workflow, not the code alone.

### Check 1 — Map the intended workflow
Identify the sequence of steps the application expects (e.g., cart → address → payment → confirm; or draft → submit → review → approve). Note any step that's supposed to gate the next one.

### Check 2 — Step-skipping / out-of-order execution
Try calling a later-stage endpoint directly without completing earlier steps (e.g., hit the "confirm order" endpoint without a valid payment record; hit an "approve" endpoint on a resource still in "draft" state). If the server accepts it, that's a state-machine enforcement gap.

### Check 3 — Client-trusted values
Identify any value the client sends that should be server-computed: price, discount %, quantity limits, currency conversion, shipping cost. Tamper with it in the request and see whether the server recalculates/validates server-side or trusts the client's number.

### Check 4 — Repeat / race / limit bypass
For anything meant to happen once (redeem a coupon, submit a vote, claim a reward) or within a limit (rate limit, quantity in stock), test:
- Simple repetition (does resubmitting the same request work twice?)
- Concurrent/parallel requests (race condition — does a limit check-then-act have a TOCTOU gap?)

### Check 5 — Negative / boundary values
Quantity = -1, 0, or extremely large; dates in the past for "future-only" fields; empty/null where a value is assumed present. These often reveal unvalidated business assumptions rather than crashes.

## Reporting discipline

- CONFIRMED requires an observed bypass, not a hypothesis
- Always note which identity(ies) were used and what the expected-vs-actual result was
- For business logic findings, state the *intended* rule you believe is being violated — the reviewer needs to agree the rule exists before agreeing it was bypassed
