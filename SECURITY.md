# Security Policy

POMS is a demonstration / portfolio project (see the disclaimer in [README.md](./README.md)). It is **not intended for production use** and is provided without warranty. That said, security reports are welcome and will be handled in good faith.

## Supported Versions

Only the latest commit on the `main` branch is supported. There are no tagged releases or long-term support branches; fixes land on `main` and older commits are not patched.

| Version | Supported |
| ------- | --------- |
| `main` (latest) | Yes |
| Any other branch or commit | No |

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report vulnerabilities privately through GitHub's built-in vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability** to open a private security advisory.
3. Provide as much detail as possible (see below).

If private advisories are unavailable, you may contact the maintainer directly via their GitHub profile.

### What to include

To help triage quickly, please include:

- A clear description of the issue and its impact.
- The affected component (e.g., `backend/api/routes/webhook.py`, RAG pipeline, Gmail integration, frontend).
- Steps to reproduce, ideally with a minimal proof of concept.
- The commit hash or branch you tested against.
- Any suggested remediation, if you have one.

### What to expect

- **Acknowledgement:** within a few days of receiving the report.
- **Triage & assessment:** the maintainer will confirm the issue and assess severity.
- **Fix & disclosure:** once a fix is ready, the advisory will be published and credit given to the reporter (unless anonymity is requested).

Because POMS is a solo-maintained demo project, response times are best-effort and not guaranteed.

## Scope

The following are **in scope** for security reports:

- Authentication or authorization flaws in the API (`backend/api/routes/`).
- Injection vulnerabilities (SQL, command, prompt injection in the AI pipeline).
- Insecure handling of uploaded files (PDF, XLSX, images) in the parsing pipeline.
- Secrets or credentials leaking through logs, errors, or API responses.
- Server-side request forgery (SSRF), path traversal, or deserialization issues.
- Known-vulnerable dependencies with a realistic exploitation path in this codebase.
- Gmail OAuth token handling and storage (`token.json`, `credentials.json`).
- Cross-site scripting (XSS) or CSRF in the React frontend.

The following are **out of scope**:

- Issues that require a fully compromised host, developer machine, or LLM provider account.
- Social engineering of maintainers or contributors.
- Denial of service via resource exhaustion (the demo has no rate limiting by design).
- Missing security headers, cookie flags, or TLS configuration on local dev servers — POMS is meant to run behind a proper reverse proxy in any non-demo use.
- Lack of authentication on the API and dashboard — the demo runs on `localhost` without auth by design.
- Output quality, hallucinations, or misclassifications from the LLM (these are correctness issues, not security issues).
- Vulnerabilities in third-party services (Azure OpenAI, Gmail API, PostgreSQL, LanceDB) — please report those to the respective vendors.
- Findings from automated scanners without a demonstrated impact.

## Handling Secrets and Credentials

POMS integrates with external services that require credentials. When reporting or reproducing issues, **never include real secrets** in reports, logs, screenshots, or commits. The following files are sensitive and must never be committed:

- `.env` — Azure OpenAI keys, database URLs, Gmail configuration.
- `backend/credentials.json` — Gmail OAuth client credentials.
- `backend/token.json` — Gmail OAuth access/refresh tokens.

If you believe a secret has been committed to the repository's history, please report it privately as described above.

## AI / LLM-Specific Considerations

POMS processes untrusted input (emails and attachments) through an LLM pipeline. Relevant risks include:

- **Prompt injection** via email body, subject, or attachment contents influencing extraction, validation, or routing decisions.
- **Indirect prompt injection** via RAG knowledge base poisoning.
- **Data exfiltration** through crafted content that causes the agent to leak other orders or knowledge base contents in responses.

Reports that demonstrate a concrete impact (e.g., bypassing the "never auto-reject" principle, forcing auto-approval of a hard-tagged PO, leaking data across orders) are in scope and highly appreciated.

## Safe Harbor

Good-faith security research on your own local deployment of POMS is welcome. Please:

- Only test against instances you own or have explicit permission to test.
- Avoid accessing, modifying, or exfiltrating data that is not yours.
- Give the maintainer reasonable time to address reported issues before public disclosure.

Thank you for helping keep POMS and its users safe.
