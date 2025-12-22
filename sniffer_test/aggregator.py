import time
from collections import deque
from threading import Lock

class RollingAggregator:
    def __init__(self, window_seconds=60):
        self.window_seconds = window_seconds
        self.buckets = deque()
        self.lock = Lock()  # protects shared memory

    def add_packet(self, metadata):
        with self.lock:
            now_sec = int(time.time())

            if not self.buckets or self.buckets[-1]["timestamp"] != now_sec:
                self.buckets.append({
                    "timestamp": now_sec,
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "packet_count": 0,
                    "tcp_packets": 0,
                    "udp_packets": 0,
                    "dns_packets": 0,
                    "src_ips": set(),
                })

            bucket = self.buckets[-1]

            if metadata["src_ip"].startswith(("192.168.", "10.", "172.")):
                bucket["bytes_out"] += metadata["size"]
            else:
                bucket["bytes_in"] += metadata["size"]

            bucket["packet_count"] += 1

            if metadata["protocol"] == "TCP":
                bucket["tcp_packets"] += 1
            elif metadata["protocol"] == "UDP":
                bucket["udp_packets"] += 1

            if metadata["dns_query"] or metadata["dns_response"]:
                bucket["dns_packets"] += 1

            # Track unique senders in this second
            bucket["src_ips"].add(metadata["src_ip"])

            self._trim_old()

    def _trim_old(self):
        cutoff = int(time.time()) - self.window_seconds
        while self.buckets and self.buckets[0]["timestamp"] < cutoff:
            self.buckets.popleft()

    def get_snapshot(self):
        """
        Safe read-only snapshot for UI / plotting
        """
        with self.lock:
            return list(self.buckets)
