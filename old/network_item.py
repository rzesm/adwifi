from dataclasses import dataclass


@dataclass
class NetworkItem:
    path: str
    ssid: str
    security: str
    signal: int
    connected: bool
