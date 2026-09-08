# Security Model

The Educational Capstone Portal authenticates users through Google OAuth and JWT, enforces authorization through faculty roles and a leader-only privilege check, and hardens the application with security middleware and inline upload validation. This document describes the implemented controls and the scanning capabilities that are planned but absent.

## Purpose

To document the end-to-end security posture of the backend: how principals are authenticated, how their authority is enforced per action, how uploaded report archives are validated before processing, and which protective controls are still gaps. The model favors inline, synchronous validation over external scanning services that the current codebase does not implement.

## Scope

In scope: identity (Google OAuth + JWT), authorization (faculty roles, leader-only submit), transport/application hardening (security headers, trusted proxy hosts, rate limiting), and upload safety (ZIP validation, type/size checks).

Out of scope (not implemented, tracked as gaps): malware scanning and dependency vulnerability scanning (G3), OCR (G1), and Turnitin integration (G2).

## Responsibilities

The security model assigns the following responsibilities across authentication, authorization, application hardening, and upload safety.

### OAuth

Students and faculty authenticate via **Google OAuth**; a session is then represented by a **JWT** issued and validated by the application. The OAuth and JWT logic lives in `app/shared/auth/service.py` (token issuance/verification) and `app/shared/auth/deps.py` (request-time authentication dependencies). The model relies on Google as the identity provider; no claim is made here about specific OAuth library internals beyond the grounded use of Google OAuth plus application-issued JWTs.

### Authorization

Authorization is role-based. Faculty authority derives from `faculty_roles.role_type`, CHECK-constrained to `hod | dean | project_coordinator | panel_member | guide`, with `status ∈ {active, inactive}` and scoping by `school_id`, `department_id`, and `programme_code`. Authorization dependencies in `app/shared/auth/deps.py` gate router handlers by the required role.

### Role Enforcement

- Faculty powers are enforced per the grounded role map: guides decide ideas and accept/reject submissions and record scores; project coordinators schedule reviews and manage marks and edit-requests; panel members enter review marks; HODs approve re-review applications and mark edit-requests; deans and HODs hold venue-approval roles.
- The team-leader privilege is enforced at the application layer: only a student whose membership role is `leader` may submit the team idea. A non-leader submit attempt returns **HTTP 403** ("only the team leader may submit").

### ZIP Validation

Uploaded report source archives are validated inline by `app/security/zip_validator.py` before extraction. The validator guards against:

- **ZIP bombs** (decompression-ratio / expanded-size limits).
- **Path traversal** (entry names escaping the extraction root).
- **Corrupt ZIP** archives (malformed central directory / bad entries).

This is inline validation, not a standalone "Security Scanner Service."

### Upload Security

The upload path (`app/modules/reports/services/upload.py` via `UploadService`) enforces:

- File type: `.zip` only.
- Size: `≤ MAX_COMPRESSED_SIZE_MB`.
- Per-student rate limiting via Redis (`app/security/rate_limiter.py`).
- A row-level `SELECT … FOR UPDATE` lock to prevent concurrent uploads, returning **HTTP 409** when compilation status is `PROCESSING`.
- Acceptance only when `submission_status ∈ {NOT_SUBMITTED, REJECTED}` and `compilation_status ≠ PROCESSING`.

### Future Malware Scanning

**[Planned] — G3.** There is no malware scanning of uploaded archives or their extracted contents. Inline validation covers structural and resource-exhaustion threats (bomb/traversal/corrupt/type/size) but does not inspect file content for malicious payloads. A future control would scan extracted files before compilation.

### Future Vulnerability Scanning

**[Planned] — G3.** There is no dependency or artifact vulnerability scanning in the pipeline. A future control would scan build inputs and dependencies for known vulnerabilities as part of CI or the processing pipeline.

## Workflow References

- The validated upload → compile pipeline that these controls protect: [report processing pipeline](../diagrams/report-processing-pipeline.md).
- Audit attribution of authenticated actions: [audit trail](./audit-trail.md).

## Business Rules

- Authentication is via Google OAuth; sessions are JWT-based.
- Faculty authority is role-scoped (`faculty_roles`), and only `active` roles confer power.
- Only the team leader may submit the idea (HTTP 403 otherwise).
- Upload: `.zip` only, `≤ MAX_COMPRESSED_SIZE_MB`, per-student Redis rate limit, row lock against concurrent upload, 409 if `PROCESSING`.
- ZIP extraction guards path traversal, decompression bombs, and corrupt archives.

## Constraints

- `SecurityHeadersMiddleware` in `app/main.py` adds **HSTS**, **X-Content-Type-Options**, and a **Content-Security-Policy** to responses.
- `TRUSTED_PROXY_HOSTS` constrains which upstream proxies the application trusts for forwarded client information; client IP–based controls (such as rate limiting) depend on this being configured correctly behind the Caddy reverse proxy.
- Security validation is inline and synchronous; there is no asynchronous scanning queue.

## Edge Cases

- **E14** — A faculty member who is also an admin can approve their own proposal; there is no conflict-of-interest guard. Role enforcement permits the action because both roles are individually authorized, so the only record of the dual capacity is in the audit trail.

## Security Considerations

- Trusting forwarded headers requires `TRUSTED_PROXY_HOSTS` to be set; otherwise client-IP-derived controls (rate limiting) can be spoofed.
- The CSP and `X-Content-Type-Options: nosniff` reduce XSS and MIME-confusion risk for any browser-rendered responses; HSTS enforces HTTPS on supporting clients.
- Because uploaded archive contents are not scanned for malicious payloads (G3), compilation runs on partially-untrusted input; the TeX Live compile runs inside a Docker image (`docker/Dockerfile.texlive`), which provides the primary isolation boundary.
- Score immutability (unique constraint + `SERIALIZABLE`) protects scoring integrity against tampering through the normal write path.

## Implementation Notes

- OAuth/JWT and authorization dependencies: `app/shared/auth/service.py`, `app/shared/auth/deps.py`.
- Leader-only submit enforcement: idea submission router (returns HTTP 403).
- Security headers and trusted proxy configuration: `app/main.py` (`SecurityHeadersMiddleware`, `TRUSTED_PROXY_HOSTS`).
- ZIP validation: `app/security/zip_validator.py`. Rate limiting: `app/security/rate_limiter.py`.
- Upload enforcement: `app/modules/reports/services/upload.py` (`UploadService`).

## Future Enhancements

- **G3 — Malware & vulnerability scanning absent.** `[Planned]` Only zip-bomb, path-traversal, corrupt-ZIP, size, and type checks exist today. Adding content malware scanning and dependency/artifact vulnerability scanning would close the gap between structural validation and content-level threat detection. Related absent integrations: OCR (G1) and Turnitin (G2) are also `[Planned]` and are not part of the security controls.
