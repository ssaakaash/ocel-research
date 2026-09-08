# ADR-007: Security Validation

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [../architecture/security-model.md](../architecture/security-model.md)
  - [../architecture/report-processing.md](../architecture/report-processing.md)
  - [../diagrams/report-processing-pipeline.md](../diagrams/report-processing-pipeline.md)

## Context

Students upload arbitrary ZIP archives that the portal extracts and compiles with `pdflatex` inside a TeX Live Docker image. Untrusted archive input is a primary attack surface: decompression bombs, path-traversal entries, and corrupt archives can exhaust resources or escape the extraction directory. The portal also exposes authenticated HTTP and SSE endpoints behind a Caddy reverse proxy and must defend against unauthenticated access and common web-layer attacks. A dedicated malware/vulnerability scanner service was envisioned ("Security Scanner Service") but does not exist in code.

## Decision

Archive safety is enforced by **inline validation**, not by an external scanner service. The upload path validates `.zip` type, enforces a maximum compressed size (`MAX_COMPRESSED_SIZE_MB`), and applies a per-student Redis rate limit before extraction. `app/security/zip_validator.py` guards against decompression bombs, path traversal, and corrupt ZIPs; a row lock (`SELECT … FOR UPDATE`) plus a 409 response prevent concurrent uploads while a compilation is `PROCESSING`. Authentication is OAuth (Google) plus JWT (`app/shared/auth/{service,deps}.py`). `SecurityHeadersMiddleware` in `app/main.py` sets HSTS, X-Content-Type-Options, and CSP, and `TRUSTED_PROXY_HOSTS` constrains which proxy hosts are honored behind Caddy. **Malware scanning and vulnerability scanning are explicitly deferred** (G3, `[Planned]`).

## Rationale

- Inline validation runs in the request path before any extraction or compilation, so the dangerous classes that are actually exploitable in this system — zip bombs, traversal, corrupt archives, oversized or wrong-type uploads, and upload flooding — are rejected at the earliest point with no external round-trip.
- Combining the rate limit, type/size checks, and the `FOR UPDATE` row lock with a 409 on `PROCESSING` bounds resource consumption per student and prevents concurrent-upload races (E7) without a separate service.
- OAuth+JWT, security headers, and trusted-proxy configuration address the web-layer surface (authentication, transport hardening, header-based attacks, proxy spoofing) directly in the application and middleware, matching the deployed Caddy topology.
- A dedicated scanner microservice would add operational surface and latency for threat classes (malware, dependency vulnerabilities) that are not the immediate exploit path for LaTeX-source archives; deferring it keeps the pipeline correct and lean while leaving the integration point open.

## Consequences

### Positive

- Untrusted archives are screened before extraction; the most relevant attack classes are blocked inline with no external dependency or added latency.
- Per-student rate limiting and the row-lock/409 mechanism bound resource use and eliminate concurrent-upload races (E7).
- Web-layer hardening (OAuth/JWT, HSTS/X-Content-Type-Options/CSP, trusted proxy hosts) is centralized in auth dependencies and `SecurityHeadersMiddleware`.

### Negative / Trade-offs

- No malware or vulnerability scanning: a malicious payload that is a structurally valid, correctly sized ZIP passes validation (G3). The threat model deliberately excludes content-level malware detection.
- Validation logic lives inline in the upload path rather than in an independently scalable/observable service, so scanning policy changes require an application deploy.
- The portal trusts that a faculty member who also holds admin rights will not abuse self-approval; there is no conflict-of-interest guard at the authorization layer (E14).

## Alternatives Considered

- **Dedicated scanner microservice.** A standalone service performing deep content inspection (malware, vulnerability scanning) on uploads. Rejected for now (G3, `[Planned]`): it adds an external dependency and latency for threat classes outside the immediate exploit path, while the structural ZIP guards that matter most are cheaper inline.
- **Gateway-level scanning.** Push validation into the Caddy reverse proxy or an upstream gateway. Rejected: the proxy lacks the application context (per-student rate state, version/state-machine guards, row locks) needed to make safe upload decisions, and duplicating ZIP semantics at the edge would diverge from the extraction logic it is meant to protect.

## Known Gaps & Follow-ups

- **G3 — Malware & vulnerability scanning absent.** Only zip-bomb, path-traversal, corrupt-ZIP, size, and type checks plus rate limiting are implemented. A dedicated scanner (microservice or gateway-integrated) is the planned follow-up. `[Planned]`
- **E14 — Faculty who is also admin.** Such a user can approve their own proposal; no conflict-of-interest guard exists in the authorization layer and should be added as a follow-up.
