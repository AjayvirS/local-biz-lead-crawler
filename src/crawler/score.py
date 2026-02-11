"""
Deterministic scoring for small-business websites.

Keep this simple and explainable. We score based on basic quality signals that we
can extract without invasive scanning.
"""


from __future__ import annotations


def score_site(
    *,
    https: bool,
    has_viewport: bool,
    title: str | None,
    has_email: bool,
    has_phone: bool,
    has_address: bool,
    stack_hint: str | None,
) -> tuple[int, list[str]]:
    """
    Returns (score 0-100, reasons list)
    Lower score = worse site = better lead candidate.
    """
    score = 100
    reasons: list[str] = []

    # Security / trust
    if not https:
        score -= 20
        reasons.append("Site is not served over HTTPS (security/trust issue).")

    # Mobile readiness
    if not has_viewport:
        score -= 15
        reasons.append("Missing mobile viewport meta tag (likely not mobile-optimized).")

    # SEO basics
    if not title:
        score -= 5
        reasons.append("Missing <title> tag (hurts SEO and browser display).")

    # Contact discoverability (rough but practical)
    missing = []
    if not has_phone:
        missing.append("phone")
    if not has_email:
        missing.append("email")
    if not has_address:
        missing.append("address")
    if len(missing) >= 2:
        score -= 10
        reasons.append("Contact info seems hard to find (missing multiple basic signals).")

    # Stack hints: not inherently bad, but some hint at higher maintenance / modernization potential
    if stack_hint == "joomla":
        score -= 3
        reasons.append("Tech stack hint suggests a legacy CMS (modernization opportunity).")

    # Clamp
    score = max(0, min(100, score))
    return score, reasons