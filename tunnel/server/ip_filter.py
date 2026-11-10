from typing import Set

class IPFilter:
    def __init__(self, blocked_ips: Set[str] = None):
        self.blocked_ips: Set[str] = blocked_ips or set()

    def block_ip(self, ip: str) -> None:
        self.blocked_ips.add(ip.strip())

    def unblock_ip(self, ip: str) -> None:
        self.blocked_ips.discard(ip.strip())

    def is_allowed(self, ip: str) -> bool:
        return ip.strip() not in self.blocked_ips
