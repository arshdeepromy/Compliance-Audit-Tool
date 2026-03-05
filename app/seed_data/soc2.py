"""SOC 2 Type II — Trust Services Criteria template seed data.

Contains 5 sections (Trust Services Criteria) with 3 criteria each (15 total),
3 scoping questions, and scoping rules for availability SLA,
processing integrity, and privacy requirements.
"""

TEMPLATE_NAME = "SOC 2 Type II \u2014 Trust Services Criteria"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "IT Security",
    "compliance_framework": "SOC 2 Type II",
}

# ---------- Sections (5 Trust Services Criteria) ----------

SECTIONS = [
    {
        "name": "Security (Common Criteria)",
        "codes": ["SOC2-CC1", "SOC2-CC2", "SOC2-CC3"],
    },
    {
        "name": "Availability",
        "codes": ["SOC2-A1", "SOC2-A2", "SOC2-A3"],
    },
    {
        "name": "Processing Integrity",
        "codes": ["SOC2-PI1", "SOC2-PI2", "SOC2-PI3"],
    },
    {
        "name": "Confidentiality",
        "codes": ["SOC2-C1", "SOC2-C2", "SOC2-C3"],
    },
    {
        "name": "Privacy",
        "codes": ["SOC2-P1", "SOC2-P2", "SOC2-P3"],
    },
]

# ---------- Criteria (3 per section, 15 total) ----------

CRITERIA = {
    # ── Security (Common Criteria) ──
    "SOC2-CC1": {
        "title": "Control Environment and Governance",
        "guidance": "The organisation demonstrates a commitment to integrity and ethical values, exercises oversight responsibility, establishes structure, authority, and responsibility, and demonstrates commitment to competence (CC1.1–CC1.5).",
        "question": "Is a control environment established with governance oversight, ethical values, and defined responsibilities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No formal control environment or governance."},
            {"score": 1, "description": "Some governance exists but roles and ethical standards not formalised."},
            {"score": 2, "description": "Governance structure defined but oversight not active or competence requirements incomplete."},
            {"score": 3, "description": "Control environment with board oversight, code of conduct, defined roles and responsibilities, competence requirements, and accountability mechanisms."},
            {"score": 4, "description": "Mature governance with independent audit committee, continuous control monitoring, ethics hotline, and integrated GRC platform."},
        ],
        "evidence": [
            {"text": "Governance structure and oversight documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Code of conduct and ethics policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-CC2": {
        "title": "Logical and Physical Access Controls",
        "guidance": "The organisation restricts logical and physical access to information assets, manages user identities and credentials, authorises access based on role, and removes access when no longer required (CC6.1–CC6.8).",
        "question": "Are logical and physical access controls implemented with identity management and role-based authorisation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No access control mechanisms."},
            {"score": 1, "description": "Basic passwords but no role-based access or identity management."},
            {"score": 2, "description": "Access controls exist but provisioning/deprovisioning not timely or physical access not controlled."},
            {"score": 3, "description": "Role-based access controls, identity lifecycle management, MFA for privileged access, physical access controls, and regular access reviews."},
            {"score": 4, "description": "Zero-trust architecture with continuous authentication, automated provisioning/deprovisioning, privileged access management, and real-time access analytics."},
        ],
        "evidence": [
            {"text": "Access control policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Access review records and user provisioning logs", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-CC3": {
        "title": "Change Management and Risk Assessment",
        "guidance": "The organisation manages changes to infrastructure, data, software, and procedures through a controlled process. Risk assessments identify threats and vulnerabilities to system components (CC3.1–CC3.4, CC8.1).",
        "question": "Are change management and risk assessment processes established for system components?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No change management or risk assessment processes."},
            {"score": 1, "description": "Changes made ad-hoc without formal approval or risk assessment."},
            {"score": 2, "description": "Change process exists but risk assessment not integrated or emergency changes not controlled."},
            {"score": 3, "description": "Formal change management with approval workflow, risk assessment, testing, rollback plans, and emergency change procedures."},
            {"score": 4, "description": "Automated CI/CD pipeline with security gates, continuous risk assessment, change analytics, and automated rollback capabilities."},
        ],
        "evidence": [
            {"text": "Change management policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Change records and risk assessment documentation", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Availability ──
    "SOC2-A1": {
        "title": "System Availability and Capacity Planning",
        "guidance": "The organisation maintains system availability to meet service commitments including capacity planning, performance monitoring, and infrastructure redundancy (A1.1).",
        "question": "Are system availability commitments defined with capacity planning and performance monitoring?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No availability commitments or monitoring."},
            {"score": 1, "description": "Basic uptime awareness but no formal SLAs or monitoring."},
            {"score": 2, "description": "SLAs defined but capacity planning or monitoring incomplete."},
            {"score": 3, "description": "Availability SLAs defined, capacity planning conducted, performance monitored, and redundancy implemented for critical components."},
            {"score": 4, "description": "Auto-scaling infrastructure with predictive capacity planning, real-time availability dashboards, and SLA compliance tracking."},
        ],
        "evidence": [
            {"text": "Service level agreements with availability commitments", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Capacity planning and performance monitoring reports", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-A2": {
        "title": "Disaster Recovery and Business Continuity",
        "guidance": "The organisation implements disaster recovery and business continuity plans to restore system availability after disruptions, including backup procedures, recovery testing, and communication plans (A1.2).",
        "question": "Are disaster recovery and business continuity plans established, tested, and maintained?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No disaster recovery or business continuity plans."},
            {"score": 1, "description": "Basic backups but no formal DR plan or testing."},
            {"score": 2, "description": "DR plan exists but not regularly tested or recovery objectives not defined."},
            {"score": 3, "description": "DR and BCP with defined RTO/RPO, regular backup verification, annual DR testing, communication plans, and documented recovery procedures."},
            {"score": 4, "description": "Active-active architecture with automated failover, continuous DR testing, chaos engineering, and sub-hour recovery capabilities."},
        ],
        "evidence": [
            {"text": "Disaster recovery and business continuity plans", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "DR test results and backup verification records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-A3": {
        "title": "Incident Response and Recovery",
        "guidance": "The organisation implements incident response procedures to detect, respond to, and recover from security and availability incidents, including escalation procedures and post-incident review (A1.3).",
        "question": "Are incident response procedures established with detection, escalation, and post-incident review?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No incident response procedures."},
            {"score": 1, "description": "Incidents handled reactively without formal procedures."},
            {"score": 2, "description": "Incident response plan exists but escalation or post-incident review not formalised."},
            {"score": 3, "description": "Incident response plan with detection, classification, escalation, communication, resolution, and post-incident review with lessons learned."},
            {"score": 4, "description": "SOAR platform with automated detection and response, incident simulation exercises, threat intelligence integration, and continuous improvement."},
        ],
        "evidence": [
            {"text": "Incident response plan and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Incident logs and post-incident review reports", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Processing Integrity ──
    "SOC2-PI1": {
        "title": "Data Processing Completeness and Accuracy",
        "guidance": "The organisation implements controls to ensure system processing is complete, valid, accurate, and timely, including input validation, processing checks, and output reconciliation (PI1.1–PI1.3).",
        "question": "Are controls in place to ensure data processing is complete, valid, accurate, and timely?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No processing integrity controls."},
            {"score": 1, "description": "Basic input validation but no processing or output checks."},
            {"score": 2, "description": "Some controls exist but not comprehensive across all processing stages."},
            {"score": 3, "description": "Input validation, processing checks, output reconciliation, and error handling implemented with monitoring and exception reporting."},
            {"score": 4, "description": "End-to-end data lineage tracking, automated reconciliation, real-time integrity monitoring, and machine learning anomaly detection."},
        ],
        "evidence": [
            {"text": "Processing integrity controls documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Reconciliation reports and error logs", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-PI2": {
        "title": "Error Detection and Correction",
        "guidance": "The organisation implements processes to detect and correct processing errors in a timely manner, including error monitoring, alerting, root cause analysis, and corrective actions (PI1.4).",
        "question": "Are error detection and correction processes implemented with monitoring and root cause analysis?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No error detection or correction processes."},
            {"score": 1, "description": "Errors detected reactively by users."},
            {"score": 2, "description": "Some automated error detection but correction not timely or root cause not analysed."},
            {"score": 3, "description": "Automated error detection with alerting, timely correction, root cause analysis, and corrective actions to prevent recurrence."},
            {"score": 4, "description": "Predictive error detection with self-healing systems, automated correction workflows, and continuous processing quality improvement."},
        ],
        "evidence": [
            {"text": "Error detection and correction procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Error logs with root cause analysis and corrective actions", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-PI3": {
        "title": "System Input and Output Controls",
        "guidance": "The organisation implements controls over system inputs to ensure authorisation and completeness, and over outputs to ensure they are distributed only to intended recipients (PI1.5).",
        "question": "Are system input authorisation and output distribution controls implemented?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No input or output controls."},
            {"score": 1, "description": "Basic input controls but output distribution not controlled."},
            {"score": 2, "description": "Input and output controls exist but not consistently applied."},
            {"score": 3, "description": "Input authorisation with validation, output distribution controls with recipient verification, and audit trails for both."},
            {"score": 4, "description": "Automated input validation with business rules engine, DLP for output control, and real-time audit logging."},
        ],
        "evidence": [
            {"text": "Input and output control procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Input authorisation and output distribution logs", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Confidentiality ──
    "SOC2-C1": {
        "title": "Confidential Information Identification and Classification",
        "guidance": "The organisation identifies and classifies confidential information based on sensitivity, establishes handling requirements, and communicates classification to personnel.",
        "question": "Is confidential information identified, classified, and are handling requirements communicated?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No information classification scheme."},
            {"score": 1, "description": "Some awareness of confidential data but no formal classification."},
            {"score": 2, "description": "Classification scheme exists but not consistently applied or communicated."},
            {"score": 3, "description": "Information classification scheme with defined levels, handling requirements, labelling, and personnel awareness training."},
            {"score": 4, "description": "Automated data classification with DLP integration, machine learning classification, and continuous monitoring of classification compliance."},
        ],
        "evidence": [
            {"text": "Information classification policy and scheme", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of classification application and training", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-C2": {
        "title": "Confidential Information Protection",
        "guidance": "The organisation implements controls to protect confidential information during storage, processing, and transmission, including encryption, access restrictions, and secure disposal.",
        "question": "Are controls implemented to protect confidential information during storage, processing, and transmission?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No protection controls for confidential information."},
            {"score": 1, "description": "Basic access controls but no encryption or secure disposal."},
            {"score": 2, "description": "Some protection measures but not comprehensive across all states (rest, transit, use)."},
            {"score": 3, "description": "Encryption at rest and in transit, access restrictions based on classification, secure disposal procedures, and DLP controls."},
            {"score": 4, "description": "End-to-end encryption with key management, confidential computing, automated DLP with real-time blocking, and secure enclaves."},
        ],
        "evidence": [
            {"text": "Confidential information protection procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Encryption and DLP implementation records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-C3": {
        "title": "Confidential Information Disposal",
        "guidance": "The organisation implements procedures to securely dispose of confidential information when no longer needed, including secure deletion, media destruction, and disposal verification.",
        "question": "Are secure disposal procedures implemented for confidential information?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No secure disposal procedures."},
            {"score": 1, "description": "Data deleted but not securely wiped or media not destroyed."},
            {"score": 2, "description": "Secure disposal for some media but not comprehensive."},
            {"score": 3, "description": "Secure disposal procedures for all media types with verified deletion, certificates of destruction, and disposal logs."},
            {"score": 4, "description": "Automated lifecycle disposal with crypto-shredding, certified destruction services, and disposal compliance monitoring."},
        ],
        "evidence": [
            {"text": "Secure disposal and destruction procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Disposal logs and certificates of destruction", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Privacy ──
    "SOC2-P1": {
        "title": "Privacy Notice and Choice",
        "guidance": "The organisation provides notice about its privacy practices and offers choices to data subjects regarding the collection, use, retention, and disclosure of personal information.",
        "question": "Are privacy notices provided and do data subjects have choices regarding their personal information?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No privacy notices or choices provided."},
            {"score": 1, "description": "Basic privacy policy exists but not comprehensive or accessible."},
            {"score": 2, "description": "Privacy notice provided but choices limited or opt-out mechanisms unclear."},
            {"score": 3, "description": "Comprehensive privacy notice with clear choices, opt-in/opt-out mechanisms, consent management, and accessible communication."},
            {"score": 4, "description": "Dynamic privacy centre with granular preference management, just-in-time notices, and automated consent lifecycle management."},
        ],
        "evidence": [
            {"text": "Privacy notice and policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Consent and preference management records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-P2": {
        "title": "Personal Information Collection and Use Limitation",
        "guidance": "The organisation collects personal information only for identified purposes, limits use to those purposes, and retains information only as long as necessary to fulfil the stated purposes.",
        "question": "Is personal information collection limited to identified purposes with appropriate retention?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No limitations on personal information collection or use."},
            {"score": 1, "description": "Some purpose awareness but collection not limited."},
            {"score": 2, "description": "Collection purposes defined but retention not managed or use limitation not enforced."},
            {"score": 3, "description": "Collection limited to identified purposes, use restricted accordingly, retention schedules defined and enforced, and disposal procedures in place."},
            {"score": 4, "description": "Automated purpose limitation with data catalogue integration, retention automation, and continuous compliance monitoring."},
        ],
        "evidence": [
            {"text": "Data collection and use limitation procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Retention schedules and disposal records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "SOC2-P3": {
        "title": "Data Subject Access and Disclosure",
        "guidance": "The organisation provides data subjects with access to their personal information for review and update, and discloses personal information to third parties only for identified purposes with appropriate agreements.",
        "question": "Can data subjects access and update their information, and are third-party disclosures controlled?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No data subject access or third-party disclosure controls."},
            {"score": 1, "description": "Access provided on request but no formal process or third-party controls."},
            {"score": 2, "description": "Access process exists but third-party disclosure agreements incomplete."},
            {"score": 3, "description": "Formal data subject access process with identity verification, third-party disclosure agreements, and disclosure logging."},
            {"score": 4, "description": "Self-service access portal with real-time data views, automated third-party agreement management, and disclosure audit trails."},
        ],
        "evidence": [
            {"text": "Data subject access request procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Third-party disclosure agreements and logs", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
}

SCOPING_QUESTIONS = [
    {
        "identifier": "soc2-q1",
        "question_text": "Does the organisation have formal availability SLAs with customers or service commitments?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "soc2-q2",
        "question_text": "Does the organisation process transactions or data where completeness and accuracy are critical (e.g. financial, healthcare)?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "soc2-q3",
        "question_text": "Does the organisation collect, store, or process personal information of individuals?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
]

SCOPING_RULES = [
    {
        "question_identifier": "soc2-q1",
        "trigger_answer": "Yes",
        "target_type": "section",
        "target_code": "Availability",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "soc2-q1",
        "trigger_answer": "No",
        "target_type": "section",
        "target_code": "Availability",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "soc2-q2",
        "trigger_answer": "Yes",
        "target_type": "section",
        "target_code": "Processing Integrity",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "soc2-q2",
        "trigger_answer": "No",
        "target_type": "section",
        "target_code": "Processing Integrity",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "soc2-q3",
        "trigger_answer": "Yes",
        "target_type": "section",
        "target_code": "Privacy",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "soc2-q3",
        "trigger_answer": "No",
        "target_type": "section",
        "target_code": "Privacy",
        "applicability_status": "not_applicable",
    },
]
