"""Resolve preview links independently of GTK or the working directory."""
from urllib.parse import urljoin, urlsplit, unquote


def resolve_link(destination, document_uri=None):
    destination = destination.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in destination):
        raise ValueError("This link contains invalid control characters.")
    if destination.startswith("#") or not destination:
        return "fragment", unquote(destination.lstrip("#"))
    if destination.startswith("//"):
        destination = "https:" + destination
    parsed = urlsplit(destination)
    if not parsed.scheme:
        if not document_uri:
            raise ValueError("Save this note first so relative links can be resolved from its folder.")
        destination = urljoin(document_uri, destination)
        parsed = urlsplit(destination)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https", "mailto", "file"):
        raise ValueError(f"Links using '{scheme}' are not supported.")
    if scheme in ("http", "https") and not parsed.netloc:
        raise ValueError("This web link is missing a website address.")
    return ("file" if scheme == "file" else "uri"), destination
