# Canaille per-client OIDC nonce requirement — validation report

## Scope and repository state

- Baseline: `72f8c225333bda10ce0b487b5a0ef4920d6bea41`
- Branch: `feat/oidc-per-client-nonce`
- Starting branch commit: `b5181db0bc7ccced17ffd84074b22f26677584f7`
- Production Canaille was not modified.
- No pull request, issue, or upstream push was created.
- Authlib under test: `1.7.2`.

## Authlib nonce execution path

Authlib 1.7.2 uses `authlib.oidc.core.grants.util.validate_nonce(request, exists_nonce, required=False)`. It reads `request.payload.data.get("nonce")`; a missing nonce raises `InvalidRequestError("Missing 'nonce' in request.")` only when `required` is true. A supplied nonce is always passed to `exists_nonce`; a replay raises `InvalidRequestError("Replay attack")` even when `required` is false.

- **Authorization Code:** Canaille registers `OpenIDCode()` without a fixed `require_nonce`. Authlib invokes `OpenIDCode.__call__`, which registers `validate_openid_authorization_request` on `after_validate_authorization_request_payload`; Canaille's override calls `validate_nonce(..., required=require_nonce_for_request(grant.request))`. The hook runs from `validate_code_authorization_request` after client lookup, redirect validation, response-type authorization, and scope validation.
- **Implicit:** Authlib's `OpenIDImplicitGrant.validate_authorization_request` calls the OAuth implicit validator, checks `openid`, and then hard-codes `validate_nonce(..., required=True)`. Canaille overrides this method, deliberately calls the parent OAuth validator via `super(oidc_core.OpenIDImplicitGrant, self)`, retains the OpenID scope check and redirect-fragment error behavior, and replaces only the nonce call with the per-client effective policy. ID-token generation copies the supplied request nonce into the ID token.
- **Hybrid:** Authlib's `OpenIDHybridGrant.validate_authorization_request` installs a nonce hook with `required=True`, then calls `validate_code_authorization_request`; `create_granted_params` saves the authorization code before producing the implicit token/ID token, and passes the code to `process_implicit_token` for `c_hash`. Canaille retains this path through `validate_code_authorization_request` while installing an equivalent hook using the effective per-client policy. The saved code receives `request.payload.data.get("nonce")` through the existing Canaille save method, and the implicit ID token receives the nonce from the request.

Thus, the three flows share Authlib's exact nonce validator and replay behavior, but require separate integration points because implicit and hybrid do not consume `OpenIDCode`'s extension hook.

## Authorization Code results

Existing six-cell matrix passes on memory and SQLite: global true/false × client None/true/false. Missing nonce is rejected for effective true and accepted for effective false; `None` inherits the global setting. Existing GUI/persistence tests pass.

## Implicit results

Added and passed five cases on memory:

- global true + inherit + missing nonce → rejection;
- global true + client false + missing nonce → success;
- global false + client true + missing nonce → rejection;
- client false + nonce → success and nonce present in ID token;
- client true + nonce → success.

Command: `uv run pytest -q --backend memory tests/oidc/test_implicit_flow.py::test_oidc_implicit_client_nonce_policy` — **5 passed**.

## Hybrid results

Added and passed the analogous five cases using `response_type=code id_token token`. Tests verify missing-nonce rejection/success, authorization-code persistence (`authcode.nonce`), and nonce presence in the ID token when supplied.

Command: `uv run pytest -q --backend memory tests/oidc/test_hybrid_flow.py::test_oidc_hybrid_client_nonce_policy` — **5 passed**.

## Dynamic Client Registration decision

**require_nonce is intentionally NOT exposed through RFC7591/RFC7592.** It is an administrative Canaille security policy, not standard client metadata. The DCR regression test sends unsupported `require_nonce` metadata and verifies that the dynamically created client has `require_nonce is None` and that the response does not expose the field. No DCR implementation was added; an untrusted client cannot set or change this policy through standard registration or management metadata.

Command: `uv run pytest -q --backend memory tests/oidc/test_dynamic_client_registration.py::test_client_registration_does_not_accept_require_nonce_metadata` — **1 passed**.

## LDAP baseline comparison

Commands:

```text
# Baseline
cd /tmp/canaille-baseline
uv sync --frozen
uv run pytest -q --backend ldap tests/backends/ldap/test_models.py

# Branch
cd /home/user/canaille-nonce
uv run pytest -q --backend ldap tests/backends/ldap/test_models.py
```

Both baseline and branch fail before the relevant model test can execute with the same environment/fixture error:

```text
TypeError: expected str, bytes or os.PathLike object, not NoneType
  tests/backends/ldap/__init__.py:17
  os.path.exists(os.path.join(self.SCHEMADIR, schema))
```

The branch's full tox run reaches the same failure in `tests/app/commands/test_config_check.py[ldap]`. This is an environment/LDAP fixture failure, not a demonstrated branch regression. The baseline initially also lacks `ldap` in its isolated environment until LDAP extras are synchronized; after synchronization, the fixture reaches the identical `SCHEMADIR=None` error. A supported LDAP/OpenLDAP environment was not available, so the full LDAP Client model lifecycle (None/True/False, save/reload/edit/inheritance) could not be executed.

## Migration review

Migration `1786000000_add_client_require_nonce.py` is additive, has a nullable Boolean with no server default, preserves existing rows as NULL, and drops the column on downgrade. Model and migration agree on a nullable Boolean. SQLite migration tests pass, including downgrade-to-base/re-upgrade and data-survival coverage.

Command: `uv run pytest -q --backend sql:sqlite tests/backends/sql/test_alembic.py tests/oidc/test_client_admin.py tests/backends/test_models.py` — **34 passed**.

The invariant is preserved: an existing client after migration has `require_nonce == None`, therefore it inherits the global setting exactly as before the upgrade.

## Full suite

Official project command is `uv run pytest` (or `uv run tox`); tox uses all extras and runs `pytest --showlocals --full-trace tests`.

- `uv run pytest -q --backend memory` — collection stopped with **8 errors** due to unavailable optional packages in the non-all-extras environment: `webauthn`, `otpauth`, and `asgiref`.
- `uv run tox -e py312 -- -x` — **1 error**, first failure is LDAP fixture `TypeError: expected str, bytes or os.PathLike object, not NoneType`; collection reported **4140 items**.
- A full tox py312 run was started; it encountered the same LDAP fixture error across the parametrized suite and was stopped after confirming the environmental failure. No reliable complete passed/skipped/xfail count is claimed.
- Maximum relevant OIDC/memory suite: `uv run pytest -q --backend memory tests/oidc/test_authorization_code_flow.py tests/oidc/test_implicit_flow.py tests/oidc/test_hybrid_flow.py tests/oidc/test_dynamic_client_registration.py tests/oidc/test_dynamic_client_registration_management.py tests/oidc/test_client_admin.py` — **97 passed, 2 warnings**.

No 100% coverage attempt was made; the new logical paths are covered directly.

## Final lint/type checks

- `uv run tox -e style -- --show-diff-on-failure` — **passed** (uv-lock, ruff, ruff-format, file checks, DjHTML, codespell).
- `uv run ruff check .` — **passed**.
- `uv run ruff format --check .` — **passed**.
- `uv run mypy canaille` — unavailable: `mypy` is not declared/installed in the project environment (`Failed to spawn: mypy`). No project type-checker command is configured in `pyproject.toml`.

## Self-review diff

Reviewed with `git diff 72f8c225333bda10ce0b487b5a0ef4920d6bea41...HEAD` and the final working-tree diff. Effective-policy resolution uses explicit `override is None`, so `False` is not confused with inheritance. No request parameter controls the policy. No DCR metadata extension was introduced. The only remaining working-tree changes are test additions/formatting plus the existing implementation files touched by formatting; no production-instance or unrelated backend-specific behavior was added.

## Remaining blockers

1. Full official suite cannot complete because the repository's LDAP fixture has `SCHEMADIR=None` in this environment; baseline reproduces the same error.
2. `mypy` is not part of the repository's configured toolchain and is unavailable; no type-check result can be claimed.
3. PostgreSQL/MySQL and supported external LDAP service runs were not available in this workspace.

These are validation-environment limitations, not a demonstrated nonce implementation failure. Manual review should inspect the Authlib hook override and LDAP schema/OID choices.

## Ready for manual review

The nonce implementation and requested logical test matrix are ready for manual review, but the requested full-suite definition of done is not fully achievable in this environment because of the blockers above.

NOT READY FOR MANUAL REVIEW
