"""PCI DSS v4.0 — Payment Card Security template seed data.

Contains 12 principal requirement sections with 5 criteria each (60 total),
5 scoping questions, and scoping rules for cloud-hosted and third-party
payment processor environments.
"""

TEMPLATE_NAME = "PCI DSS v4.0 \u2014 Payment Card Security"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "IT Security",
    "compliance_framework": "PCI DSS v4.0",
}

# ---------- Sections (12 principal requirements) ----------

SECTIONS = [
    {
        "name": "Req 1: Install and Maintain Network Security Controls",
        "codes": ["PCI-1.1", "PCI-1.2", "PCI-1.3", "PCI-1.4", "PCI-1.5"],
    },
    {
        "name": "Req 2: Apply Secure Configurations",
        "codes": ["PCI-2.1", "PCI-2.2", "PCI-2.3", "PCI-2.4", "PCI-2.5"],
    },
    {
        "name": "Req 3: Protect Stored Account Data",
        "codes": ["PCI-3.1", "PCI-3.2", "PCI-3.3", "PCI-3.4", "PCI-3.5"],
    },
    {
        "name": "Req 4: Protect Cardholder Data with Strong Cryptography",
        "codes": ["PCI-4.1", "PCI-4.2", "PCI-4.3", "PCI-4.4", "PCI-4.5"],
    },
    {
        "name": "Req 5: Protect Against Malicious Software",
        "codes": ["PCI-5.1", "PCI-5.2", "PCI-5.3", "PCI-5.4", "PCI-5.5"],
    },
    {
        "name": "Req 6: Develop and Maintain Secure Systems",
        "codes": ["PCI-6.1", "PCI-6.2", "PCI-6.3", "PCI-6.4", "PCI-6.5"],
    },
    {
        "name": "Req 7: Restrict Access by Business Need to Know",
        "codes": ["PCI-7.1", "PCI-7.2", "PCI-7.3", "PCI-7.4", "PCI-7.5"],
    },
    {
        "name": "Req 8: Identify Users and Authenticate Access",
        "codes": ["PCI-8.1", "PCI-8.2", "PCI-8.3", "PCI-8.4", "PCI-8.5"],
    },
    {
        "name": "Req 9: Restrict Physical Access",
        "codes": ["PCI-9.1", "PCI-9.2", "PCI-9.3", "PCI-9.4", "PCI-9.5"],
    },
    {
        "name": "Req 10: Log and Monitor All Access",
        "codes": ["PCI-10.1", "PCI-10.2", "PCI-10.3", "PCI-10.4", "PCI-10.5"],
    },
    {
        "name": "Req 11: Test Security of Systems and Networks",
        "codes": ["PCI-11.1", "PCI-11.2", "PCI-11.3", "PCI-11.4", "PCI-11.5"],
    },
    {
        "name": "Req 12: Support Information Security with Policies and Programs",
        "codes": ["PCI-12.1", "PCI-12.2", "PCI-12.3", "PCI-12.4", "PCI-12.5"],
    },
]

# ---------- Criteria (5 per section, 60 total) ----------

CRITERIA = {
    # ── Req 1: Network Security Controls ──
    "PCI-1.1": {
        "title": "Network Security Control Processes",
        "guidance": "Processes and mechanisms for installing and maintaining network security controls are defined, documented, and known to all affected parties.",
        "question": "Are processes for managing network security controls defined and documented?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No documented network security control processes."},
            {"score": 1, "description": "Some processes exist but are incomplete or outdated."},
            {"score": 2, "description": "Processes documented but not consistently followed."},
            {"score": 3, "description": "Processes defined, documented, assigned to responsible personnel, and reviewed at least annually."},
            {"score": 4, "description": "Processes are automated where possible, with continuous improvement and regular effectiveness reviews."},
        ],
        "evidence": [
            {"text": "Network security control policy and procedures document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of annual review and sign-off", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Roles and responsibilities assignment for network security", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },
    "PCI-1.2": {
        "title": "Firewall and Router Configuration Standards",
        "guidance": "Network security controls (NSCs) are configured and maintained to restrict traffic between trusted and untrusted networks.",
        "question": "Are firewall and router configurations documented and restrict inbound/outbound traffic to that which is necessary?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No firewall configuration standards."},
            {"score": 1, "description": "Firewalls exist but configurations are not documented."},
            {"score": 2, "description": "Configurations documented but not reviewed regularly."},
            {"score": 3, "description": "Configurations documented, deny-all default rule in place, reviewed at least every six months."},
            {"score": 4, "description": "Automated configuration management with drift detection and alerting."},
        ],
        "evidence": [
            {"text": "Current firewall/router configuration standards document", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of six-monthly rule-set review", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
            {"text": "Network diagram showing trust boundaries", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-1.3": {
        "title": "CDE Network Segmentation",
        "guidance": "Network access to and from the cardholder data environment (CDE) is restricted and segmented from other networks.",
        "question": "Is the cardholder data environment segmented from other networks with appropriate controls?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No network segmentation of the CDE."},
            {"score": 1, "description": "Partial segmentation with significant gaps."},
            {"score": 2, "description": "Segmentation in place but not validated."},
            {"score": 3, "description": "CDE fully segmented, validated with penetration testing, and documented."},
            {"score": 4, "description": "Micro-segmentation implemented with continuous monitoring of inter-segment traffic."},
        ],
        "evidence": [
            {"text": "Network segmentation architecture diagram", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Penetration test report validating segmentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Access control lists for CDE boundary devices", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },
    "PCI-1.4": {
        "title": "Personal Firewall Controls",
        "guidance": "Network connections between trusted and untrusted networks are controlled, including personal firewall software on portable devices.",
        "question": "Are personal firewalls installed and active on all portable computing devices that connect to the CDE?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No personal firewall controls on portable devices."},
            {"score": 1, "description": "Personal firewalls on some devices only."},
            {"score": 2, "description": "Firewalls deployed but users can disable them."},
            {"score": 3, "description": "Personal firewalls active on all portable devices, centrally managed, users cannot disable."},
            {"score": 4, "description": "Endpoint detection and response (EDR) integrated with personal firewall and centrally monitored."},
        ],
        "evidence": [
            {"text": "Endpoint management policy for portable devices", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "MDM/endpoint management console screenshot showing compliance", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-1.5": {
        "title": "Cloud Network Security Controls",
        "guidance": "Network security controls for cloud-hosted CDE components ensure equivalent protection to on-premises controls, including cloud provider shared responsibility model documentation.",
        "question": "Are network security controls for cloud-hosted CDE components documented and equivalent to on-premises controls?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud-specific network security controls."},
            {"score": 1, "description": "Basic cloud security groups but no formal documentation."},
            {"score": 2, "description": "Cloud NSCs documented but shared responsibility model not addressed."},
            {"score": 3, "description": "Cloud NSCs documented, shared responsibility model defined, security groups reviewed regularly."},
            {"score": 4, "description": "Infrastructure-as-code for cloud NSCs with automated compliance checking."},
        ],
        "evidence": [
            {"text": "Cloud shared responsibility matrix for network security", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Cloud security group/firewall rule documentation", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
            {"text": "Cloud network architecture diagram", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },

    # ── Req 2: Apply Secure Configurations ──
    "PCI-2.1": {
        "title": "Secure Configuration Standards",
        "guidance": "Configuration standards are developed for all system components, consistent with industry-accepted hardening standards.",
        "question": "Are secure configuration standards defined for all system components in the CDE?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No configuration standards defined."},
            {"score": 1, "description": "Standards exist for some systems only."},
            {"score": 2, "description": "Standards defined but not based on industry benchmarks."},
            {"score": 3, "description": "Standards based on CIS/NIST benchmarks, cover all system types, reviewed annually."},
            {"score": 4, "description": "Automated configuration enforcement with continuous compliance monitoring."},
        ],
        "evidence": [
            {"text": "System hardening standards document referencing CIS/NIST benchmarks", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "List of all system component types with applicable standards", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-2.2": {
        "title": "Default Credentials Removal",
        "guidance": "Vendor-supplied defaults (passwords, accounts, settings) are changed or removed before systems are deployed.",
        "question": "Are all vendor-supplied default accounts and passwords changed or disabled before deployment?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Default credentials still in use."},
            {"score": 1, "description": "Some defaults changed but process is ad-hoc."},
            {"score": 2, "description": "Process exists but not consistently applied."},
            {"score": 3, "description": "Documented process ensures all defaults are changed/removed; verified during deployment checklist."},
            {"score": 4, "description": "Automated scanning detects default credentials with mandatory remediation before go-live."},
        ],
        "evidence": [
            {"text": "Deployment checklist including default credential removal", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Scan results showing no default credentials on CDE systems", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-2.3": {
        "title": "Wireless Environment Configuration",
        "guidance": "Wireless environments connected to the CDE or transmitting cardholder data are configured securely with strong encryption.",
        "question": "Are wireless networks in the CDE configured with strong encryption and authentication?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No wireless security controls."},
            {"score": 1, "description": "Wireless encryption in use but weak protocols (WEP/WPA)."},
            {"score": 2, "description": "WPA2/WPA3 in use but default SSIDs or weak passphrases."},
            {"score": 3, "description": "WPA3 or WPA2-Enterprise with strong authentication, default SSIDs changed, rogue AP detection."},
            {"score": 4, "description": "Wireless IDS/IPS deployed with automated rogue AP containment."},
        ],
        "evidence": [
            {"text": "Wireless security configuration standards", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Wireless scan results showing no rogue access points", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-2.4": {
        "title": "System Component Inventory",
        "guidance": "An inventory of all in-scope system components is maintained, including purpose and owner for each component.",
        "question": "Is an accurate inventory of all in-scope system components maintained?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No system component inventory."},
            {"score": 1, "description": "Partial inventory with significant gaps."},
            {"score": 2, "description": "Inventory exists but not regularly updated."},
            {"score": 3, "description": "Complete inventory with owner, purpose, and classification for each component; reviewed quarterly."},
            {"score": 4, "description": "Automated asset discovery integrated with CMDB and real-time inventory updates."},
        ],
        "evidence": [
            {"text": "System component inventory with owner and purpose", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of quarterly inventory review", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-2.5": {
        "title": "Cloud Configuration Management",
        "guidance": "Cloud service configurations are managed securely, with cloud-specific hardening applied and shared responsibility obligations documented.",
        "question": "Are cloud service configurations hardened and managed according to documented standards?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud configuration management."},
            {"score": 1, "description": "Basic cloud configurations but no formal standards."},
            {"score": 2, "description": "Standards exist but not consistently applied."},
            {"score": 3, "description": "Cloud configurations hardened per CIS benchmarks, shared responsibility documented, reviewed quarterly."},
            {"score": 4, "description": "Cloud security posture management (CSPM) tool deployed with automated remediation."},
        ],
        "evidence": [
            {"text": "Cloud hardening standards based on CIS benchmarks", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "CSPM or manual review report showing compliance", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 3: Protect Stored Account Data ──
    "PCI-3.1": {
        "title": "Data Retention Policy",
        "guidance": "Processes and mechanisms for protecting stored account data are defined, including data retention and disposal policies.",
        "question": "Is there a documented data retention and disposal policy for cardholder data?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No data retention policy."},
            {"score": 1, "description": "Informal retention practices with no documentation."},
            {"score": 2, "description": "Policy exists but retention periods not defined or enforced."},
            {"score": 3, "description": "Policy defines retention periods, disposal methods, and quarterly review of stored data."},
            {"score": 4, "description": "Automated data discovery and retention enforcement with alerts for policy violations."},
        ],
        "evidence": [
            {"text": "Data retention and disposal policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of quarterly data retention review", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-3.2": {
        "title": "Sensitive Authentication Data Handling",
        "guidance": "Sensitive authentication data (SAD) is not stored after authorisation, even if encrypted.",
        "question": "Is sensitive authentication data purged immediately after authorisation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "SAD stored after authorisation."},
            {"score": 1, "description": "Some SAD purged but process is incomplete."},
            {"score": 2, "description": "SAD purged but no verification process."},
            {"score": 3, "description": "SAD never stored post-authorisation; verified through regular scans and code reviews."},
            {"score": 4, "description": "Automated DLP controls prevent SAD storage with real-time alerting."},
        ],
        "evidence": [
            {"text": "SAD handling procedures document", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Data discovery scan results confirming no SAD storage", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-3.3": {
        "title": "PAN Display Masking",
        "guidance": "The primary account number (PAN) is masked when displayed, showing only the minimum digits needed for business purposes.",
        "question": "Is the PAN masked when displayed, with only authorised roles able to see more than the first six/last four digits?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "PAN displayed in full without masking."},
            {"score": 1, "description": "Masking applied inconsistently across systems."},
            {"score": 2, "description": "Masking applied but some roles see full PAN without business justification."},
            {"score": 3, "description": "PAN masked to first 6/last 4 by default; full PAN access restricted to authorised roles with documented need."},
            {"score": 4, "description": "Dynamic masking with role-based display rules enforced at the application layer."},
        ],
        "evidence": [
            {"text": "PAN masking policy and role-based access matrix", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Screenshots showing masked PAN in applications", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-3.4": {
        "title": "PAN Storage Encryption",
        "guidance": "PAN is rendered unreadable anywhere it is stored using strong cryptography, truncation, tokenisation, or one-way hashing.",
        "question": "Is stored PAN rendered unreadable using strong cryptography or equivalent methods?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "PAN stored in clear text."},
            {"score": 1, "description": "Some PAN encrypted but not all storage locations covered."},
            {"score": 2, "description": "Encryption applied but weak algorithms or poor key management."},
            {"score": 3, "description": "All stored PAN encrypted with AES-256 or equivalent; key management procedures documented."},
            {"score": 4, "description": "Tokenisation implemented to eliminate PAN from most systems; encryption for remaining storage."},
        ],
        "evidence": [
            {"text": "Encryption standards document specifying algorithms and key lengths", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Key management procedures document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data discovery scan confirming no clear-text PAN", "age_label": "< 3 months", "age_class": "age-1y", "required": False},
        ],
    },
    "PCI-3.5": {
        "title": "Encryption Key Management",
        "guidance": "Cryptographic keys used to protect stored account data are managed securely throughout their lifecycle.",
        "question": "Are cryptographic key management procedures defined covering generation, distribution, storage, rotation, and destruction?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No key management procedures."},
            {"score": 1, "description": "Keys exist but management is ad-hoc."},
            {"score": 2, "description": "Some key management procedures but lifecycle not fully covered."},
            {"score": 3, "description": "Full key lifecycle documented: generation, distribution, storage, rotation, retirement, destruction; HSM or equivalent used."},
            {"score": 4, "description": "Automated key rotation with HSM-backed key management and split-knowledge/dual-control."},
        ],
        "evidence": [
            {"text": "Key management procedures covering full lifecycle", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of key rotation schedule and last rotation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 4: Protect Cardholder Data with Strong Cryptography ──
    "PCI-4.1": {
        "title": "Cryptography Policy for Data in Transit",
        "guidance": "Processes and mechanisms for protecting cardholder data with strong cryptography during transmission over open, public networks are defined and documented.",
        "question": "Are policies and procedures for encrypting cardholder data in transit documented?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No cryptography policy for data in transit."},
            {"score": 1, "description": "Some encryption used but no formal policy."},
            {"score": 2, "description": "Policy exists but does not cover all transmission channels."},
            {"score": 3, "description": "Policy covers all transmission channels, specifies TLS 1.2+ or equivalent, reviewed annually."},
            {"score": 4, "description": "Automated certificate management with continuous monitoring of encryption strength."},
        ],
        "evidence": [
            {"text": "Data-in-transit encryption policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "TLS configuration standards document", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-4.2": {
        "title": "TLS Implementation",
        "guidance": "Strong cryptography is used during transmission of cardholder data, with only trusted keys and certificates accepted.",
        "question": "Is TLS 1.2 or higher enforced for all cardholder data transmissions?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No encryption for data in transit."},
            {"score": 1, "description": "Encryption used but weak protocols (SSL, TLS 1.0/1.1)."},
            {"score": 2, "description": "TLS 1.2 used but weak cipher suites not disabled."},
            {"score": 3, "description": "TLS 1.2+ enforced, weak ciphers disabled, certificates from trusted CAs, HSTS enabled."},
            {"score": 4, "description": "TLS 1.3 preferred, automated certificate renewal, certificate transparency monitoring."},
        ],
        "evidence": [
            {"text": "SSL/TLS scan results showing protocol versions and cipher suites", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Certificate inventory with expiry dates", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-4.3": {
        "title": "Wireless Transmission Encryption",
        "guidance": "Cardholder data transmitted over wireless networks uses industry best-practice encryption.",
        "question": "Is cardholder data transmitted over wireless networks encrypted using strong cryptography?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No encryption for wireless transmissions."},
            {"score": 1, "description": "Weak wireless encryption (WEP)."},
            {"score": 2, "description": "WPA2 used but with pre-shared keys."},
            {"score": 3, "description": "WPA3 or WPA2-Enterprise with 802.1X authentication for CDE wireless."},
            {"score": 4, "description": "Wireless traffic fully tunnelled through encrypted VPN with additional application-layer encryption."},
        ],
        "evidence": [
            {"text": "Wireless encryption configuration documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Wireless security assessment results", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-4.4": {
        "title": "End-User Messaging Encryption",
        "guidance": "PAN is secured with strong cryptography when sent via end-user messaging technologies (email, instant messaging, SMS, chat).",
        "question": "Are controls in place to prevent PAN from being sent unencrypted via end-user messaging?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "PAN sent in clear text via messaging."},
            {"score": 1, "description": "Policy exists but no technical controls."},
            {"score": 2, "description": "Some DLP controls but not covering all channels."},
            {"score": 3, "description": "DLP controls on email and messaging prevent unencrypted PAN transmission; policy communicated to staff."},
            {"score": 4, "description": "Automated DLP with real-time blocking and user education prompts across all channels."},
        ],
        "evidence": [
            {"text": "DLP policy covering PAN in messaging", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "DLP tool configuration and recent alert summary", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-4.5": {
        "title": "Certificate and Key Management for Transit",
        "guidance": "Certificates and keys used for protecting data in transit are managed securely with proper lifecycle controls.",
        "question": "Are certificates and encryption keys for data-in-transit managed with documented lifecycle procedures?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No certificate management process."},
            {"score": 1, "description": "Certificates used but no inventory or tracking."},
            {"score": 2, "description": "Certificate inventory exists but renewal is manual and ad-hoc."},
            {"score": 3, "description": "Certificate inventory maintained, renewal tracked, expired certificates detected and replaced promptly."},
            {"score": 4, "description": "Automated certificate lifecycle management with ACME protocol and alerting for upcoming expirations."},
        ],
        "evidence": [
            {"text": "Certificate inventory with expiry tracking", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Certificate renewal procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 5: Protect Against Malicious Software ──
    "PCI-5.1": {
        "title": "Anti-Malware Policy",
        "guidance": "Processes and mechanisms for protecting all systems and networks from malicious software are defined and documented.",
        "question": "Are anti-malware policies and procedures documented and assigned to responsible personnel?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No anti-malware policy."},
            {"score": 1, "description": "Anti-malware deployed but no formal policy."},
            {"score": 2, "description": "Policy exists but does not cover all system types."},
            {"score": 3, "description": "Policy covers all system types, defines update frequency, scan schedules, and responsibilities."},
            {"score": 4, "description": "Next-gen anti-malware with behavioural analysis, integrated with SIEM and incident response."},
        ],
        "evidence": [
            {"text": "Anti-malware policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "List of systems with anti-malware coverage status", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-5.2": {
        "title": "Anti-Malware Deployment",
        "guidance": "Anti-malware solutions are deployed on all systems commonly affected by malicious software, kept current, and perform periodic and real-time scans.",
        "question": "Is anti-malware deployed on all applicable systems with current signatures and real-time scanning?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No anti-malware deployed."},
            {"score": 1, "description": "Anti-malware on some systems, signatures outdated."},
            {"score": 2, "description": "Deployed on most systems but real-time scanning not enabled everywhere."},
            {"score": 3, "description": "Deployed on all applicable systems, signatures updated automatically, real-time and periodic scans enabled."},
            {"score": 4, "description": "EDR/XDR solution with machine learning detection, centralised management, and automated response."},
        ],
        "evidence": [
            {"text": "Anti-malware management console report showing deployment coverage", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
            {"text": "Evidence of automatic signature updates", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-5.3": {
        "title": "Anti-Malware Mechanisms Active",
        "guidance": "Anti-malware mechanisms and processes are active, maintained, and monitored. Users cannot disable anti-malware without management approval.",
        "question": "Are anti-malware mechanisms actively running and protected from being disabled by users?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Anti-malware can be freely disabled by users."},
            {"score": 1, "description": "Tamper protection on some systems only."},
            {"score": 2, "description": "Tamper protection enabled but no monitoring of disabled instances."},
            {"score": 3, "description": "Tamper protection enabled, users cannot disable, management approval process documented, alerts on tampering."},
            {"score": 4, "description": "Automated re-enablement with SOC monitoring and incident creation for any tampering attempts."},
        ],
        "evidence": [
            {"text": "Tamper protection configuration evidence", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Management approval process for temporary disablement", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-5.4": {
        "title": "Anti-Phishing Controls",
        "guidance": "Anti-phishing mechanisms protect users against phishing attacks, including email filtering and user awareness training.",
        "question": "Are anti-phishing controls deployed including email filtering and user awareness training?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No anti-phishing controls."},
            {"score": 1, "description": "Basic email filtering only."},
            {"score": 2, "description": "Email filtering with some user training but not regular."},
            {"score": 3, "description": "Email filtering with DMARC/DKIM/SPF, regular phishing awareness training, simulated phishing exercises."},
            {"score": 4, "description": "AI-powered email security with automated phishing simulation and adaptive training based on user risk scores."},
        ],
        "evidence": [
            {"text": "Email security configuration (DMARC, DKIM, SPF records)", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Phishing awareness training records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Phishing simulation results", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "PCI-5.5": {
        "title": "Malware Incident Response",
        "guidance": "Processes are in place to detect and respond to malware incidents, including logging, alerting, and remediation procedures.",
        "question": "Are malware detection events logged, alerted, and responded to with documented procedures?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No malware incident response process."},
            {"score": 1, "description": "Malware detected but no formal response process."},
            {"score": 2, "description": "Response process exists but not tested."},
            {"score": 3, "description": "Malware events logged centrally, alerts generated, documented response procedures, tested annually."},
            {"score": 4, "description": "Automated containment and remediation with SOAR integration and post-incident analysis."},
        ],
        "evidence": [
            {"text": "Malware incident response procedure", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Evidence of malware alert configuration and recent alerts", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 6: Develop and Maintain Secure Systems ──
    "PCI-6.1": {
        "title": "Secure Development Lifecycle",
        "guidance": "A formal secure software development lifecycle (SDLC) is defined and implemented for all in-house and custom software.",
        "question": "Is a secure software development lifecycle defined and followed for custom applications?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No secure SDLC process."},
            {"score": 1, "description": "Some security activities but no formal SDLC."},
            {"score": 2, "description": "SDLC defined but not consistently followed."},
            {"score": 3, "description": "Secure SDLC documented, includes threat modelling, secure coding standards, code review, and security testing."},
            {"score": 4, "description": "DevSecOps pipeline with automated SAST/DAST, dependency scanning, and security gates."},
        ],
        "evidence": [
            {"text": "Secure SDLC policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of security activities in recent development projects", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-6.2": {
        "title": "Vulnerability Management",
        "guidance": "All system components are protected from known vulnerabilities by installing applicable security patches within defined timeframes.",
        "question": "Are security patches applied to all system components within defined timeframes?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No patch management process."},
            {"score": 1, "description": "Patches applied ad-hoc with no tracking."},
            {"score": 2, "description": "Patch process exists but critical patches not applied within 30 days."},
            {"score": 3, "description": "Critical patches applied within 30 days, all patches tracked, exceptions documented and risk-accepted."},
            {"score": 4, "description": "Automated patch management with zero-day response procedures and compensating controls."},
        ],
        "evidence": [
            {"text": "Patch management policy with defined timeframes", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Patch compliance report for CDE systems", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-6.3": {
        "title": "Secure Code Review",
        "guidance": "Custom application code is reviewed for vulnerabilities before release, using manual or automated methods.",
        "question": "Is custom application code reviewed for security vulnerabilities before deployment?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No code review process."},
            {"score": 1, "description": "Informal code reviews without security focus."},
            {"score": 2, "description": "Security code reviews performed but not for all changes."},
            {"score": 3, "description": "All code changes reviewed for security, OWASP Top 10 covered, findings tracked to remediation."},
            {"score": 4, "description": "Automated SAST integrated into CI/CD with mandatory security review gates."},
        ],
        "evidence": [
            {"text": "Code review policy and secure coding standards", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Recent code review records showing security findings", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-6.4": {
        "title": "Web Application Protection",
        "guidance": "Public-facing web applications are protected against attacks using WAF or equivalent controls.",
        "question": "Are public-facing web applications protected by a WAF or equivalent security controls?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No web application protection."},
            {"score": 1, "description": "Basic WAF deployed but not tuned."},
            {"score": 2, "description": "WAF deployed and tuned but not covering all applications."},
            {"score": 3, "description": "WAF protecting all public-facing apps, rules updated regularly, blocking mode enabled."},
            {"score": 4, "description": "WAF with machine learning, bot protection, API security, and automated rule updates."},
        ],
        "evidence": [
            {"text": "WAF deployment documentation and coverage list", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "WAF rule review and update records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-6.5": {
        "title": "Change Management for CDE",
        "guidance": "Changes to all system components in the CDE are managed through a formal change control process.",
        "question": "Is a formal change control process followed for all changes to CDE system components?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No change control process."},
            {"score": 1, "description": "Changes made without formal approval."},
            {"score": 2, "description": "Change process exists but not consistently followed."},
            {"score": 3, "description": "Formal change control with impact analysis, approval, testing, and rollback procedures for all CDE changes."},
            {"score": 4, "description": "Automated change management integrated with CI/CD, with security impact assessment and approval workflows."},
        ],
        "evidence": [
            {"text": "Change management policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Recent change records showing approval and testing", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 7: Restrict Access by Business Need to Know ──
    "PCI-7.1": {
        "title": "Access Control Policy",
        "guidance": "Processes and mechanisms for restricting access to system components and cardholder data by business need to know are defined and documented.",
        "question": "Is an access control policy defined that restricts access based on business need to know?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No access control policy."},
            {"score": 1, "description": "Informal access practices with no documentation."},
            {"score": 2, "description": "Policy exists but roles and access levels not clearly defined."},
            {"score": 3, "description": "Policy defines roles, access levels, and need-to-know requirements; reviewed annually."},
            {"score": 4, "description": "Attribute-based access control (ABAC) with automated provisioning and continuous access validation."},
        ],
        "evidence": [
            {"text": "Access control policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Role-based access matrix for CDE systems", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-7.2": {
        "title": "Role-Based Access Control",
        "guidance": "Access to system components and data is appropriately defined and assigned using role-based access control (RBAC).",
        "question": "Is role-based access control implemented for all CDE system components?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No RBAC implementation."},
            {"score": 1, "description": "Some role definitions but not consistently applied."},
            {"score": 2, "description": "RBAC implemented but excessive privileges exist."},
            {"score": 3, "description": "RBAC implemented with least-privilege principle, roles documented, access reviews performed quarterly."},
            {"score": 4, "description": "Just-in-time access provisioning with automated role mining and privilege analytics."},
        ],
        "evidence": [
            {"text": "RBAC role definitions and privilege assignments", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Quarterly access review records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-7.3": {
        "title": "Vendor Risk Assessment",
        "guidance": "Third-party service providers with access to cardholder data are assessed for security risk and monitored for compliance.",
        "question": "Are third-party service providers assessed for security risk and monitored for ongoing compliance?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No vendor risk assessment process."},
            {"score": 1, "description": "Some vendors assessed but no formal process."},
            {"score": 2, "description": "Assessment process exists but not all vendors covered."},
            {"score": 3, "description": "All vendors with CDE access assessed annually, compliance status tracked, contractual requirements defined."},
            {"score": 4, "description": "Continuous vendor risk monitoring with automated compliance evidence collection and risk scoring."},
        ],
        "evidence": [
            {"text": "Vendor risk assessment policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Vendor assessment records for CDE service providers", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-7.4": {
        "title": "Cloud Access Management",
        "guidance": "Access to cloud-hosted CDE components is managed with cloud-native IAM controls and follows the principle of least privilege.",
        "question": "Is access to cloud-hosted CDE components managed with cloud IAM and least-privilege principles?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud access management controls."},
            {"score": 1, "description": "Cloud IAM used but with overly broad permissions."},
            {"score": 2, "description": "IAM policies defined but not regularly reviewed."},
            {"score": 3, "description": "Cloud IAM with least-privilege policies, service accounts restricted, access reviewed quarterly."},
            {"score": 4, "description": "Cloud IAM with just-in-time access, automated policy analysis, and continuous compliance monitoring."},
        ],
        "evidence": [
            {"text": "Cloud IAM policy documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Cloud access review records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-7.5": {
        "title": "Service Provider Monitoring",
        "guidance": "Service providers with access to cardholder data are monitored for compliance status and contractual security requirements.",
        "question": "Are service providers monitored for ongoing PCI DSS compliance and contractual security obligations?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No service provider monitoring."},
            {"score": 1, "description": "Initial assessment only, no ongoing monitoring."},
            {"score": 2, "description": "Annual review but no contractual security requirements."},
            {"score": 3, "description": "Annual compliance review, contractual security requirements, AOC/ROC collected, incident notification clauses."},
            {"score": 4, "description": "Continuous compliance monitoring with automated evidence collection and real-time risk dashboards."},
        ],
        "evidence": [
            {"text": "Service provider agreements with security clauses", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Service provider compliance status tracker (AOC/ROC)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 8: Identify Users and Authenticate Access ──
    "PCI-8.1": {
        "title": "User Identification Policy",
        "guidance": "Processes and mechanisms for identifying users and authenticating access to system components are defined and documented.",
        "question": "Are user identification and authentication policies documented for all CDE access?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No user identification policy."},
            {"score": 1, "description": "Some authentication controls but no formal policy."},
            {"score": 2, "description": "Policy exists but does not cover all access methods."},
            {"score": 3, "description": "Policy covers all access methods, unique IDs required, shared accounts prohibited, reviewed annually."},
            {"score": 4, "description": "Zero-trust identity verification with continuous authentication and risk-based access decisions."},
        ],
        "evidence": [
            {"text": "User identification and authentication policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence that shared/generic accounts are prohibited", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-8.2": {
        "title": "Unique User Identification",
        "guidance": "Every user is assigned a unique ID before being allowed access to system components or cardholder data.",
        "question": "Is a unique ID assigned to every user with access to CDE systems?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Shared accounts used for CDE access."},
            {"score": 1, "description": "Most users have unique IDs but some shared accounts remain."},
            {"score": 2, "description": "Unique IDs assigned but naming convention inconsistent."},
            {"score": 3, "description": "All users have unique IDs, consistent naming convention, no shared accounts, disabled accounts removed promptly."},
            {"score": 4, "description": "Automated identity lifecycle management with real-time provisioning/deprovisioning."},
        ],
        "evidence": [
            {"text": "User account listing showing unique IDs", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Account management procedures (creation, modification, deletion)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-8.3": {
        "title": "Multi-Factor Authentication",
        "guidance": "Multi-factor authentication (MFA) is implemented for all access into the CDE and for all remote network access.",
        "question": "Is MFA implemented for all access to the CDE and all remote access?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No MFA implemented."},
            {"score": 1, "description": "MFA for some access but not all CDE access."},
            {"score": 2, "description": "MFA for remote access but not for local CDE access."},
            {"score": 3, "description": "MFA for all CDE access and all remote access, using at least two different authentication factors."},
            {"score": 4, "description": "Phishing-resistant MFA (FIDO2/WebAuthn) with adaptive authentication based on risk signals."},
        ],
        "evidence": [
            {"text": "MFA configuration documentation for CDE systems", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "MFA enrollment report showing coverage", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-8.4": {
        "title": "Password Policy",
        "guidance": "Strong authentication credentials are required, with minimum complexity, length, and rotation requirements.",
        "question": "Are password policies enforced with minimum complexity, length, and history requirements?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No password policy enforced."},
            {"score": 1, "description": "Basic password requirements but not technically enforced."},
            {"score": 2, "description": "Password policy enforced but does not meet PCI DSS requirements."},
            {"score": 3, "description": "Minimum 12 characters, complexity enforced, history of 4, lockout after 10 attempts, 90-day rotation."},
            {"score": 4, "description": "Passwordless authentication preferred, with password policy exceeding minimums and breach-password detection."},
        ],
        "evidence": [
            {"text": "Password policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Technical enforcement evidence (AD/IAM policy screenshots)", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-8.5": {
        "title": "Account Lifecycle Management",
        "guidance": "User accounts are managed throughout their lifecycle, including timely deactivation of terminated users and inactive accounts.",
        "question": "Are user accounts deactivated promptly upon termination and inactive accounts disabled within 90 days?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No account lifecycle management."},
            {"score": 1, "description": "Accounts sometimes disabled but no formal process."},
            {"score": 2, "description": "Process exists but inactive accounts not regularly reviewed."},
            {"score": 3, "description": "Terminated accounts disabled within 24 hours, inactive accounts disabled within 90 days, reviewed quarterly."},
            {"score": 4, "description": "Automated account lifecycle with HR integration, real-time deprovisioning, and continuous inactive account detection."},
        ],
        "evidence": [
            {"text": "Account lifecycle management procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Inactive account review report", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 9: Restrict Physical Access ──
    "PCI-9.1": {
        "title": "Physical Access Control Policy",
        "guidance": "Processes and mechanisms for restricting physical access to cardholder data are defined and documented.",
        "question": "Are physical access control policies documented for areas containing cardholder data or CDE systems?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No physical access control policy."},
            {"score": 1, "description": "Some physical controls but no formal policy."},
            {"score": 2, "description": "Policy exists but does not cover all sensitive areas."},
            {"score": 3, "description": "Policy covers all CDE areas, defines access levels, badge requirements, and visitor procedures."},
            {"score": 4, "description": "Biometric access controls with real-time monitoring and automated access revocation."},
        ],
        "evidence": [
            {"text": "Physical access control policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Facility map showing CDE areas and access control points", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-9.2": {
        "title": "Physical Access Controls Implementation",
        "guidance": "Physical access controls manage entry into facilities and sensitive areas, using badge readers, locks, or equivalent mechanisms.",
        "question": "Are physical access controls (badge readers, locks, cameras) implemented for CDE areas?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No physical access controls for CDE areas."},
            {"score": 1, "description": "Basic locks only, no electronic access control."},
            {"score": 2, "description": "Electronic access control but not all entry points covered."},
            {"score": 3, "description": "All CDE entry points have electronic access control, access logs maintained, cameras at entry/exit."},
            {"score": 4, "description": "Multi-layer physical security with mantrap, biometrics, and integration with logical access systems."},
        ],
        "evidence": [
            {"text": "Physical access control system documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Access log samples from CDE entry points", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-9.3": {
        "title": "Visitor Management",
        "guidance": "Visitor access to CDE areas is authorised, logged, and visitors are escorted at all times.",
        "question": "Are visitors to CDE areas authorised, logged, and escorted?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No visitor management process."},
            {"score": 1, "description": "Visitors sometimes logged but not consistently."},
            {"score": 2, "description": "Visitor log maintained but escorts not always provided."},
            {"score": 3, "description": "Visitors authorised before entry, logged with date/time, escorted at all times, badges visually distinct."},
            {"score": 4, "description": "Digital visitor management with pre-registration, photo ID, and automated badge expiry."},
        ],
        "evidence": [
            {"text": "Visitor management procedures", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Visitor log samples", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-9.4": {
        "title": "Media Protection",
        "guidance": "Media with cardholder data is physically secured, and its movement is controlled and tracked.",
        "question": "Is media containing cardholder data physically secured with controlled access and tracked movement?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No media protection controls."},
            {"score": 1, "description": "Some media secured but tracking is incomplete."},
            {"score": 2, "description": "Media secured but no formal tracking of movement."},
            {"score": 3, "description": "All media classified, stored securely, movement tracked, destruction procedures documented."},
            {"score": 4, "description": "Encrypted media only, automated tracking with chain-of-custody, certified destruction with certificates."},
        ],
        "evidence": [
            {"text": "Media handling and destruction policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Media inventory and movement log", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-9.5": {
        "title": "Point-of-Interaction Device Protection",
        "guidance": "Point-of-interaction (POI) devices are protected from tampering and unauthorised substitution.",
        "question": "Are POI devices inventoried, inspected regularly, and protected from tampering?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No POI device protection."},
            {"score": 1, "description": "POI devices deployed but no inventory."},
            {"score": 2, "description": "Inventory exists but inspections not performed."},
            {"score": 3, "description": "POI devices inventoried with serial numbers, inspected periodically, staff trained to detect tampering."},
            {"score": 4, "description": "Tamper-evident seals, automated health monitoring, and real-time alerts for device anomalies."},
        ],
        "evidence": [
            {"text": "POI device inventory with serial numbers and locations", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "POI inspection records and staff training evidence", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 10: Log and Monitor All Access ──
    "PCI-10.1": {
        "title": "Logging Policy",
        "guidance": "Processes and mechanisms for logging and monitoring all access to system components and cardholder data are defined and documented.",
        "question": "Are logging and monitoring policies documented for all CDE system components?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No logging policy."},
            {"score": 1, "description": "Some logging enabled but no formal policy."},
            {"score": 2, "description": "Policy exists but does not cover all system components."},
            {"score": 3, "description": "Policy covers all CDE components, defines what to log, retention periods, and review responsibilities."},
            {"score": 4, "description": "Centralised SIEM with automated log analysis, correlation, and real-time alerting."},
        ],
        "evidence": [
            {"text": "Logging and monitoring policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "List of systems with logging enabled and retention settings", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-10.2": {
        "title": "Audit Log Content",
        "guidance": "Audit logs capture all required events including user access, administrative actions, and access to cardholder data.",
        "question": "Do audit logs capture user identification, event type, date/time, success/failure, and affected data?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Audit logs do not capture required events."},
            {"score": 1, "description": "Some events logged but missing required fields."},
            {"score": 2, "description": "Most events logged but not all required event types."},
            {"score": 3, "description": "All required events logged with user ID, event type, date/time, success/failure, origin, and affected resource."},
            {"score": 4, "description": "Enhanced logging with session recording, data access patterns, and anomaly detection."},
        ],
        "evidence": [
            {"text": "Log format specification showing required fields", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Sample audit log entries demonstrating completeness", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-10.3": {
        "title": "Log Protection",
        "guidance": "Audit logs are protected from unauthorised modification and destruction.",
        "question": "Are audit logs protected from tampering, with access restricted to authorised personnel?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Logs not protected from modification."},
            {"score": 1, "description": "Basic file permissions but no integrity monitoring."},
            {"score": 2, "description": "Access restricted but no integrity verification."},
            {"score": 3, "description": "Logs stored with restricted access, integrity monitoring enabled, backed up to separate secure location."},
            {"score": 4, "description": "Write-once storage with cryptographic integrity verification and immutable log archival."},
        ],
        "evidence": [
            {"text": "Log protection and integrity monitoring configuration", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Access control list for log storage systems", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "PCI-10.4": {
        "title": "Time Synchronisation",
        "guidance": "All critical system clocks and times are synchronised using time-synchronisation technology.",
        "question": "Are all CDE system clocks synchronised to authoritative time sources?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No time synchronisation."},
            {"score": 1, "description": "Some systems synchronised but not all."},
            {"score": 2, "description": "NTP configured but not monitored for drift."},
            {"score": 3, "description": "All CDE systems synchronised to authoritative NTP sources, drift monitored, access to time settings restricted."},
            {"score": 4, "description": "Redundant NTP with automated drift alerting and GPS-backed time sources."},
        ],
        "evidence": [
            {"text": "NTP configuration documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Time synchronisation status report", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-10.5": {
        "title": "Log Review and Alerting",
        "guidance": "Audit logs are reviewed regularly to identify anomalies or suspicious activity, with automated alerting for critical events.",
        "question": "Are audit logs reviewed daily and are automated alerts configured for critical security events?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No log review process."},
            {"score": 1, "description": "Logs reviewed occasionally but not daily."},
            {"score": 2, "description": "Daily review of some logs but no automated alerting."},
            {"score": 3, "description": "Daily log review, automated alerts for critical events, exceptions investigated and documented."},
            {"score": 4, "description": "24/7 SOC monitoring with SIEM correlation, automated incident creation, and threat intelligence integration."},
        ],
        "evidence": [
            {"text": "Log review procedures and schedule", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Alert configuration and recent alert investigation records", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 11: Test Security of Systems and Networks ──
    "PCI-11.1": {
        "title": "Security Testing Policy",
        "guidance": "Processes and mechanisms for regularly testing security of systems and networks are defined and documented.",
        "question": "Are security testing policies and schedules documented for all CDE systems?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No security testing policy."},
            {"score": 1, "description": "Ad-hoc testing with no formal schedule."},
            {"score": 2, "description": "Policy exists but testing not performed on schedule."},
            {"score": 3, "description": "Policy defines testing types, frequency, scope, and responsible parties; schedule followed."},
            {"score": 4, "description": "Continuous security testing with automated vulnerability scanning and red team exercises."},
        ],
        "evidence": [
            {"text": "Security testing policy and annual schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of testing performed per schedule", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-11.2": {
        "title": "Vulnerability Scanning",
        "guidance": "Internal and external vulnerability scans are performed at least quarterly and after significant changes.",
        "question": "Are internal and external vulnerability scans performed quarterly and after significant changes?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No vulnerability scanning performed."},
            {"score": 1, "description": "Scanning performed but not quarterly."},
            {"score": 2, "description": "Quarterly scans but findings not remediated timely."},
            {"score": 3, "description": "Quarterly internal and ASV external scans, findings remediated, rescans confirm remediation."},
            {"score": 4, "description": "Continuous vulnerability scanning with automated prioritisation and integration with patch management."},
        ],
        "evidence": [
            {"text": "Most recent internal vulnerability scan report", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Most recent ASV external scan report (passing)", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Remediation tracking for identified vulnerabilities", "age_label": "< 3 months", "age_class": "age-1y", "required": False},
        ],
    },
    "PCI-11.3": {
        "title": "Penetration Testing",
        "guidance": "External and internal penetration testing is performed at least annually and after significant changes.",
        "question": "Is penetration testing performed at least annually covering both internal and external attack surfaces?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No penetration testing performed."},
            {"score": 1, "description": "Penetration testing performed but not annually."},
            {"score": 2, "description": "Annual testing but scope does not cover all CDE components."},
            {"score": 3, "description": "Annual internal and external penetration testing, covers all CDE, findings remediated and retested."},
            {"score": 4, "description": "Semi-annual penetration testing with red team exercises and purple team collaboration."},
        ],
        "evidence": [
            {"text": "Most recent penetration test report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Remediation evidence for penetration test findings", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-11.4": {
        "title": "Intrusion Detection and Prevention",
        "guidance": "Intrusion-detection and/or intrusion-prevention techniques are used to detect and/or prevent intrusions into the network.",
        "question": "Are IDS/IPS systems deployed to monitor CDE network traffic for malicious activity?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No IDS/IPS deployed."},
            {"score": 1, "description": "IDS deployed but signatures outdated."},
            {"score": 2, "description": "IDS/IPS deployed but not covering all CDE traffic."},
            {"score": 3, "description": "IDS/IPS at all CDE perimeter points, signatures current, alerts monitored, incidents investigated."},
            {"score": 4, "description": "Network detection and response (NDR) with behavioural analysis and automated threat containment."},
        ],
        "evidence": [
            {"text": "IDS/IPS deployment documentation and coverage map", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "IDS/IPS alert review and incident records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-11.5": {
        "title": "File Integrity Monitoring",
        "guidance": "File integrity monitoring (FIM) or change-detection mechanisms are deployed to alert on unauthorised modification of critical files.",
        "question": "Is file integrity monitoring deployed on critical CDE system files and configurations?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No file integrity monitoring."},
            {"score": 1, "description": "FIM on some systems but not all critical files."},
            {"score": 2, "description": "FIM deployed but alerts not reviewed regularly."},
            {"score": 3, "description": "FIM on all critical system files, alerts reviewed daily, unauthorised changes investigated."},
            {"score": 4, "description": "Real-time FIM with automated rollback for unauthorised changes and SIEM integration."},
        ],
        "evidence": [
            {"text": "FIM configuration showing monitored files and directories", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "FIM alert review records", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Req 12: Support Information Security with Policies and Programs ──
    "PCI-12.1": {
        "title": "Information Security Policy",
        "guidance": "A comprehensive information security policy is established, published, maintained, and disseminated to all relevant personnel.",
        "question": "Is a comprehensive information security policy established, reviewed annually, and communicated to all personnel?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No information security policy."},
            {"score": 1, "description": "Policy exists but outdated or not communicated."},
            {"score": 2, "description": "Policy current but not communicated to all personnel."},
            {"score": 3, "description": "Policy reviewed annually, approved by management, communicated to all personnel with acknowledgement."},
            {"score": 4, "description": "Policy integrated into onboarding, with regular refresher training and automated acknowledgement tracking."},
        ],
        "evidence": [
            {"text": "Information security policy document with review date", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Policy acknowledgement records from personnel", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-12.2": {
        "title": "Risk Assessment Process",
        "guidance": "A formal risk assessment is performed at least annually and upon significant changes to identify threats, vulnerabilities, and risks.",
        "question": "Is a formal risk assessment performed at least annually for the CDE?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No risk assessment performed."},
            {"score": 1, "description": "Informal risk identification with no formal methodology."},
            {"score": 2, "description": "Risk assessment performed but not annually."},
            {"score": 3, "description": "Annual risk assessment using recognised methodology, covers all CDE assets, findings drive remediation."},
            {"score": 4, "description": "Continuous risk assessment with quantitative analysis and integration with vulnerability management."},
        ],
        "evidence": [
            {"text": "Most recent risk assessment report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Risk register with treatment plans", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-12.3": {
        "title": "Security Awareness Training",
        "guidance": "Security awareness training is provided to all personnel upon hire and at least annually thereafter.",
        "question": "Do all personnel receive security awareness training upon hire and at least annually?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No security awareness training."},
            {"score": 1, "description": "Training provided to some personnel only."},
            {"score": 2, "description": "Training provided but not annually."},
            {"score": 3, "description": "Annual training for all personnel, covers PCI DSS requirements, social engineering, and incident reporting."},
            {"score": 4, "description": "Role-based training with simulated attacks, gamification, and continuous micro-learning."},
        ],
        "evidence": [
            {"text": "Security awareness training materials and schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Training completion records for all personnel", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "PCI-12.4": {
        "title": "Incident Response Plan",
        "guidance": "An incident response plan is established, maintained, and tested to ensure effective response to security incidents.",
        "question": "Is an incident response plan documented, tested annually, and does it cover cardholder data breach scenarios?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No incident response plan."},
            {"score": 1, "description": "Plan exists but not tested."},
            {"score": 2, "description": "Plan tested but does not cover all required scenarios."},
            {"score": 3, "description": "Plan covers detection, containment, eradication, recovery, and notification; tested annually via tabletop exercise."},
            {"score": 4, "description": "Automated incident response playbooks with SOAR integration and regular red team/blue team exercises."},
        ],
        "evidence": [
            {"text": "Incident response plan document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Annual incident response test/exercise report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Lessons learned from most recent test or real incident", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "PCI-12.5": {
        "title": "Contractual Security Requirements",
        "guidance": "PCI DSS compliance is managed and maintained by the entity, with clear accountability and contractual requirements for third parties.",
        "question": "Are contractual security requirements defined for all third parties with access to cardholder data?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No contractual security requirements for third parties."},
            {"score": 1, "description": "Some contracts include security clauses but not all."},
            {"score": 2, "description": "Security clauses in most contracts but not standardised."},
            {"score": 3, "description": "Standardised security clauses in all third-party contracts, PCI DSS compliance required, annual review."},
            {"score": 4, "description": "Automated third-party compliance monitoring with contractual SLAs and penalty clauses for non-compliance."},
        ],
        "evidence": [
            {"text": "Standard security contract clauses template", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Third-party contract inventory with compliance status", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
}

# ---------- Scoping Questions (5 per Req 3.3) ----------

SCOPING_QUESTIONS = [
    {
        "identifier": "pci-q1",
        "question_text": "Does the organisation store cardholder data?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "pci-q2",
        "question_text": "Is the cardholder data environment cloud-hosted?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "pci-q3",
        "question_text": "Does the organisation use a third-party payment processor?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
    {
        "identifier": "pci-q4",
        "question_text": "Does the organisation operate wireless networks in the cardholder data environment?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 3,
    },
    {
        "identifier": "pci-q5",
        "question_text": "Does the organisation develop custom payment applications?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 4,
    },
]

# ---------- Scoping Rules (cloud and third-party per Req 3.4, 3.5) ----------

SCOPING_RULES = [
    # Cloud-hosted CDE (pci-q2 = Yes) → cloud-specific criteria become applicable
    # Req 3.4: cloud provider shared responsibility, cloud configuration monitoring,
    #          cloud access management
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-1.5",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-2.5",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-7.4",
        "applicability_status": "applicable",
    },
    # Cloud-hosted CDE (pci-q2 = No) → cloud-specific criteria not applicable
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-1.5",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-2.5",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-7.4",
        "applicability_status": "not_applicable",
    },
    # Third-party payment processor (pci-q3 = Yes) → vendor/service provider criteria applicable
    # Req 3.5: vendor risk assessment, service provider monitoring, contractual security
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-7.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-7.5",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "PCI-12.5",
        "applicability_status": "applicable",
    },
    # Third-party payment processor (pci-q3 = No) → vendor/service provider criteria not applicable
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-7.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-7.5",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-12.5",
        "applicability_status": "not_applicable",
    },
    # Wireless networks (pci-q4 = No) → wireless criteria not applicable
    {
        "question_identifier": "pci-q4",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-2.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q4",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-4.3",
        "applicability_status": "not_applicable",
    },
    # Custom payment applications (pci-q5 = No) → secure SDLC and code review not applicable
    {
        "question_identifier": "pci-q5",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-6.1",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "pci-q5",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "PCI-6.3",
        "applicability_status": "not_applicable",
    },
]
