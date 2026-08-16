# Canaille per-client OIDC nonce requirement — review report

## Upstream baseline

- Repository: `https://github.com/yaal-coop/canaille` (official GitHub mirror; upstream development repository is GitLab).
- Branch: `main`.
- Starting commit: `72f8c225333bda10ce0b487b5a0ef4920d6bea41`.
- Working branch: `feat/oidc-per-client-nonce`.

## Existing implementation

The global setting is `CANAILLE_OIDC.REQUIRE_NONCE`, declared in `canaille/oidc/configuration.py` and passed to Authlib's `OpenIDCode` extension in `canaille/oidc/provider.py`. The authorization-code OIDC flow therefore used one server-wide boolean. Authlib's implicit and hybrid OIDC implementations also hard-coded nonce as required.

## Existing upstream research

The GitHub API was checked for all issues and pull requests. The repository currently reports no open issues and one historical documentation PR. Searches of the repository and GitHub API found no existing per-client nonce implementation or active related change. The project directs feature discussion to the GitLab issue tracker and Matrix room (`CONTRIBUTING.rst`); no issue or discussion was created by this work.

## Architecture

The proposed implementation stores a nullable `Client.require_nonce`:

- `None`: inherit `CANAILLE_OIDC.REQUIRE_NONCE`;
- `True`: require nonce for that client;
- `False`: do not require nonce for that client.

The effective value is resolved from `request.client`, not from an untrusted request parameter. A supplied nonce remains subject to the existing Authlib replay validation even when the requirement is disabled.

The GUI uses a three-option select field on the existing client edit form: server default, require nonce, and do not require nonce. Existing clients remain `NULL` after migration.

Alternatives rejected:

- replacing the global setting — breaks deployments with mixed clients;
- writing `True`/`False` during migration — changes existing semantics;
- rejecting nonce when disabled — violates the requested meaning and OIDC interoperability;
- request-parameter-controlled behavior — unsafe and not client-specific.

## Files changed

- `canaille/oidc/basemodels.py`: nullable per-client field and semantics.
- `canaille/backends/sql/models/oidc.py`: SQL nullable Boolean column.
- `canaille/backends/sql/migrations/1786000000_add_client_require_nonce.py`: additive migration; existing rows remain `NULL`.
- `canaille/backends/ldap/models/oidc.py`: LDAP attribute mapping.
- `canaille/backends/ldap/schemas/oauth2-openldap.schema`: LDAP attribute and optional object-class field.
- `canaille/backends/ldap/schemas/oauth2-openldap.ldif`: generated LDAP schema equivalent.
- `canaille/oidc/endpoints/forms.py`: translated GUI select field and help text.
- `canaille/oidc/endpoints/clients.py`: form normalization and persistence.
- `canaille/oidc/provider.py`: effective-value resolution in authorization-code, implicit, and hybrid OIDC paths.
- `doc/howtos/sso.rst`: global default and override documentation.
- `tests/oidc/test_authorization_code_flow.py`: six-cell global/override matrix.
- `tests/oidc/test_client_admin.py`: default and GUI persistence assertions.

## Data migration

SQL migration is additive and nullable. LDAP uses an optional attribute, so old entries without `oauthRequireNonce` deserialize as `None`. Memory backend receives the inherited base model field automatically. No existing client is assigned `True` or `False`.

## Tests

Passed:

```text
ruff check canaille tests/oidc/test_authorization_code_flow.py tests/oidc/test_client_admin.py
All checks passed!

uv run pytest --backend memory tests/oidc/test_authorization_code_flow.py::test_nonce_required_in_oidc_requests tests/oidc/test_client_admin.py::test_client_add tests/oidc/test_client_admin.py::test_client_edit
3 passed

uv run pytest --backend memory tests/oidc/test_authorization_code_flow.py::test_client_nonce_requirement_override
6 passed

uv run pytest --backend sql:sqlite tests/oidc/test_client_admin.py::test_client_add tests/oidc/test_client_admin.py::test_client_edit tests/oidc/test_authorization_code_flow.py::test_client_nonce_requirement_override
8 passed
```

LDAP test invocation was attempted, but the repository LDAP fixture failed before the relevant tests because the test environment did not provide a usable LDAP server/configuration (`TypeError: expected str, bytes or os.PathLike object, not NoneType`; subsequent parametrized LDAP fixture setup also exposed a pytest fixture-finalizer issue). This must be rerun in the project's supported LDAP environment before upstream submission.

The full test suite and coverage gate were not completed in this workspace. This is an explicit review blocker.

## Security review

- Override is read from `request.client`, after normal client resolution.
- No request parameter controls the setting.
- `client_id` substitution still goes through the existing client lookup and redirect/client validation.
- `True` forces nonce requirement even when the server default is false.
- `False` only disables the missing-nonce rejection; supplied nonce values still use Authlib's existing replay check.
- Dynamic registration does not expose this operational/admin-only setting through standard RFC metadata. The interaction with Canaille's management API should be decided during review before treating the patch as upstream-ready.

## Compatibility

The global `REQUIRE_NONCE` remains present and remains the fallback for all old and unset clients. The migration does not alter existing rows. The new field is backend-neutral in the common model, SQL, LDAP mapping, and memory backend.

## Git status

- Branch: `feat/oidc-per-client-nonce`.
- No upstream PR, draft PR, issue, merge, or production Canaille change was made.
- No fork push was performed: no authenticated user fork URL was available in the workspace (`https://github.com/Dragonk/canaille.git` was not found). The branch remains local.

## Suggested PR (not published)

### Title

`feat: allow per-client OIDC nonce requirement overrides`

### Description

Add a nullable per-client nonce requirement that inherits the server-wide `CANAILLE_OIDC.REQUIRE_NONCE` setting by default. Administrators can require or not require a nonce for an individual client without weakening the policy for all other clients. A nonce supplied by a client remains validated when the requirement is disabled. SQL and LDAP persistence, administration UI, documentation, and OIDC flow tests are included.

### Checklist

- [ ] Confirm upstream maintainer preference for the field name and whether it should be exposed via dynamic client management.
- [ ] Run full test suite and 100% coverage.
- [ ] Run SQL PostgreSQL/MySQL variants where supported.
- [ ] Run LDAP tests in supported OpenLDAP environment.
- [ ] Add/refresh translation catalogs according to project workflow.
- [ ] Review implicit and hybrid flow behavior against Authlib version supported by upstream.
- [ ] Confirm LDAP OID allocation/schema compatibility with maintainers.
- [ ] Push branch to user's fork only after authenticated fork remote is supplied.
- [ ] Open PR manually only after user approval and morning review.

## Open questions

1. Should `require_nonce` be an administrative Canaille extension only, or should it be represented in the dynamic client registration management API?
2. Should implicit and hybrid flows be covered by dedicated end-to-end tests in addition to the authorization-code matrix?
3. Is the chosen LDAP OID namespace acceptable upstream?
4. Should the GUI field be available on client creation, or only on edit as implemented here?
5. Does upstream require generated translation catalogs in the same change?
6. Full LDAP and full-suite/coverage runs remain to be completed in a supported environment.

## Review warning

This is a work-in-progress review branch, not a claim that the definition of done has been reached: the branch is local rather than safely pushed to a fork, and the complete project test/coverage matrix has not yet run. No PR was created.
