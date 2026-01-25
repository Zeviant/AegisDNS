"""
Use dnspython library maybe.
Possible paramaters that can be used for risk score:
    - A / AAAA records (A = IPv4, AAAA = IPv6 // Malicious or disposable domains often use: cheap or shared hosting IPs, 
    rapidly changing IPs (fast-flux networks) IP addresses in unusual countries)
    - MX records (determines email provider, disposable domains often skip email setup)
    - NS records (Cheap/free DNS providers are often used for malicious purposes)
    - CNAME / TXT records (Look for domain verification or SPF/DKIM; some spam domains omit SPF) --> (idk what this means yet)
    - TTL values (Very low TTL sometimes indicates fast-flux/malicious infrastructure)
"""