import asyncio
import socket
from datetime import datetime

import dns.resolver
import dns.reversename

BLACKLISTS = [
    "zen.spamhaus.org",
    "dbl.spamhaus.org",
    "b.barracudacentral.org",
    "dnsbl.sorbs.net",
    "bl.spamcop.net",
    "multi.uribl.com",
]


def _check_blacklist_sync(domain: str, blacklist: str) -> bool:
    try:
        query = f"{domain}.{blacklist}"
        answers = dns.resolver.resolve(query, "A", lifetime=5)
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False
    except Exception:
        return False


def _resolve_domain_ip(domain: str) -> str:
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return ""


def _reverse_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(reversed(parts))
    return ip


async def check_domain(domain: str) -> dict:
    blacklists_found = []
    loop = asyncio.get_event_loop()
    ip = await loop.run_in_executor(None, _resolve_domain_ip, domain)
    reversed_ip = _reverse_ip(ip) if ip else domain

    for bl in BLACKLISTS:
        found = await loop.run_in_executor(None, _check_blacklist_sync, reversed_ip, bl)
        if found:
            blacklists_found.append(bl)

    return {
        "domain": domain,
        "ip": ip,
        "is_blacklisted": len(blacklists_found) > 0,
        "blacklists_found_on": blacklists_found,
        "checked_at": datetime.utcnow(),
    }
