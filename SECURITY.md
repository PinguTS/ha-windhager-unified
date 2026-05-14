# Security Policy

## Scope

This policy covers security issues in the **Windhager Unified** Home Assistant
integration code, including:

- Authentication and credential handling
- TLS / SSL certificate verification behaviour
- Any code path that could expose the HA host, the Windhager device, or user
  credentials to unintended parties

This policy does **not** cover general product support, configuration questions,
or bugs unrelated to security. Use [GitHub Issues](../../issues) for those.

## Reporting a vulnerability

**Do not open a public GitHub issue for undisclosed security problems.** Public
disclosure before a fix is available can put other users at risk.

Please report security vulnerabilities using
[GitHub private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-on-vulnerabilities/privately-reporting-a-security-vulnerability):

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Fill in the description, steps to reproduce, and potential impact.

If you cannot use the GitHub reporting UI, contact the maintainer directly through
the profile linked from this repository.

## Response

We aim to acknowledge reports within **7 days** and to provide an assessment or fix
within **30 days** depending on severity.

## Supported versions

Only the latest published release is actively maintained. Please verify you are
running the current version before filing a report.
