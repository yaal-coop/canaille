import re


def extract_csrf_token(html: str) -> str:
    """Extract CSRF token from HTML form."""
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    if match:
        return match.group(1)
    raise ValueError("CSRF token not found in HTML")
