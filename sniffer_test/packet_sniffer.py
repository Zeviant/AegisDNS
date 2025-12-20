from scapy.all import sniff, IP, TCP, UDP, DNS
from datetime import datetime, timezone

def packet_handler(packet, aggregator):
    try: 
        if IP not in packet:
            return

        ip_layer = packet[IP]

        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "src_ip": ip_layer.src,
            "dst_ip": ip_layer.dst,
            "protocol": None,
            "src_port": None,
            "dst_port": None,
            "size": len(packet),
            "dns_query": None,
            "dns_response": None,
        }

        # Here recognizes the protocol
        if TCP in packet and packet[TCP].dport == 80:
                print("TCP port 80 detected:", ip_layer.dst)
        if TCP in packet:
            metadata["protocol"] = "TCP"
            metadata["src_port"] = packet[TCP].sport
            metadata["dst_port"] = packet[TCP].dport


        elif UDP in packet:
            metadata["protocol"] = "UDP"
            metadata["src_port"] = packet[UDP].sport
            metadata["dst_port"] = packet[UDP].dport

        if DNS in packet:
            dns_layer = packet[DNS]
            # DNS Query
            if dns_layer.qr == 0 and dns_layer.qd:
                try:
                    metadata["dns_query"] = dns_layer.qd.qname.decode(errors="ignore")
                except Exception:
                    metadata["dns_query"] = None

            # DNS Response
            elif dns_layer.qr == 1 and dns_layer.an:
                try:
                    # Some DNS answers don't have rdata
                    if hasattr(dns_layer.an, "rdata"):
                        metadata["dns_response"] = str(dns_layer.an.rdata)
                except Exception:
                    metadata["dns_response"] = None

            aggregator.add_packet(metadata)
    
    except Exception as e:
        print("[Sniffer error]", e)


def start_sniffing(aggregator, interface=None):
    print("[*] Starting packet sniffer...")
    sniff(
        iface=interface,
        prn=lambda pkt: packet_handler(pkt, aggregator),
        store=False
    )
