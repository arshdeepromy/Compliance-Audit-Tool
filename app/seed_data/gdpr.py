"""GDPR — General Data Protection Regulation template seed data.

Contains 8 sections with 3 criteria each (24 total),
3 scoping questions, and scoping rules for special category data,
cross-border transfers, and automated decision-making.
"""

TEMPLATE_NAME = "GDPR \u2014 General Data Protection Regulation"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "Privacy",
    "compliance_framework": "GDPR",
}

# ---------- Sections ----------

SECTIONS = [
    {
        "name": "Lawfulness of Processing",
        "codes": ["GDPR-1.1", "GDPR-1.2", "GDPR-1.3"],
    },
    {
        "name": "Purpose Limitation",
        "codes": ["GDPR-2.1", "GDPR-2.2", "GDPR-2.3"],
    },
    {
        "name": "Data Minimisation",
        "codes": ["GDPR-3.1", "GDPR-3.2", "GDPR-3.3"],
    },
    {
        "name": "Accuracy",
        "codes": ["GDPR-4.1", "GDPR-4.2", "GDPR-4.3"],
    },
    {
        "name": "Storage Limitation",
        "codes": ["GDPR-5.1", "GDPR-5.2", "GDPR-5.3"],
    },
    {
        "name": "Integrity and Confidentiality",
        "codes": ["GDPR-6.1", "GDPR-6.2", "GDPR-6.3"],
    },
    {
        "name": "Accountability",
        "codes": ["GDPR-7.1", "GDPR-7.2", "GDPR-7.3"],
    },
    {
        "name": "Data Subject Rights",
        "codes": ["GDPR-8.1", "GDPR-8.2", "GDPR-8.3"],
    },
]

# ---------- Criteria (3 per section, 24 total) ----------

CRITERIA = {
    # ── Lawfulness of Processing ──
    "GDPR-1.1": {
        "title": "Lawful Basis for Processing",
        "guidance": "The organisation shall identify and document a lawful basis under Article 6 for each processing activity. Processing is lawful only if at least one basis applies: consent, contract, legal obligation, vital interests, public task, or legitimate interests.",
        "question": "Is a lawful basis identified and documented for each personal data processing activity?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No lawful basis identified for processing activities."},
            {"score": 1, "description": "Some processing activities have a lawful basis but not systematically documented."},
            {"score": 2, "description": "Lawful basis documented for most activities but not reviewed or linked to records of processing."},
            {"score": 3, "description": "Lawful basis identified, documented, and reviewed for all processing activities with clear justification and linked to Article 30 records."},
            {"score": 4, "description": "Automated lawful basis tracking integrated with data catalogue, regular reviews triggered by processing changes, and legal team sign-off."},
        ],
        "evidence": [
            {"text": "Records of processing activities (Article 30) with lawful basis", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Lawful basis assessment documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-1.2": {
        "title": "Consent Management",
        "guidance": "Where consent is the lawful basis, it shall be freely given, specific, informed, and unambiguous. The organisation shall be able to demonstrate consent was given and provide easy mechanisms for withdrawal.",
        "question": "Where consent is relied upon, is it freely given, specific, informed, and easily withdrawable?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No consent management processes."},
            {"score": 1, "description": "Consent collected but not granular, specific, or easily withdrawable."},
            {"score": 2, "description": "Consent forms exist but records of consent not maintained or withdrawal mechanisms unclear."},
            {"score": 3, "description": "Consent is freely given, specific, informed, unambiguous, with records maintained and easy withdrawal mechanisms provided."},
            {"score": 4, "description": "Consent management platform with granular preferences, automated renewal, withdrawal tracking, and real-time processing cessation on withdrawal."},
        ],
        "evidence": [
            {"text": "Consent forms and collection mechanisms", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Consent records and withdrawal logs", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-1.3": {
        "title": "Special Category Data Processing",
        "guidance": "Processing of special category data (Article 9) requires both a lawful basis under Article 6 and an additional condition under Article 9(2), such as explicit consent, employment law, or substantial public interest.",
        "question": "Where special category data is processed, are both Article 6 and Article 9 conditions met?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "Special category data processed without additional safeguards."},
            {"score": 1, "description": "Awareness of special category requirements but conditions not formally documented."},
            {"score": 2, "description": "Article 9 conditions identified but not linked to specific processing activities."},
            {"score": 3, "description": "Both Article 6 and Article 9 conditions documented for all special category processing with appropriate safeguards."},
            {"score": 4, "description": "Automated classification of special category data with policy enforcement, enhanced access controls, and regular DPIA reviews."},
        ],
        "evidence": [
            {"text": "Special category data processing register with Article 9 conditions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data Protection Impact Assessments for special category processing", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Purpose Limitation ──
    "GDPR-2.1": {
        "title": "Specified and Explicit Purposes",
        "guidance": "Personal data shall be collected for specified, explicit, and legitimate purposes and not further processed in a manner incompatible with those purposes (Article 5(1)(b)).",
        "question": "Are purposes for data collection specified, explicit, and communicated to data subjects?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined purposes for data collection."},
            {"score": 1, "description": "Purposes vaguely defined or overly broad."},
            {"score": 2, "description": "Purposes documented but not consistently communicated to data subjects."},
            {"score": 3, "description": "Purposes specified, explicit, legitimate, documented in privacy notices, and communicated at point of collection."},
            {"score": 4, "description": "Purpose management integrated with data catalogue, automated compatibility assessments for new uses, and purpose-linked retention."},
        ],
        "evidence": [
            {"text": "Privacy notices specifying processing purposes", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Records of processing activities showing purposes", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-2.2": {
        "title": "Compatibility Assessment for Further Processing",
        "guidance": "Before processing data for a new purpose, the organisation shall assess compatibility with the original purpose considering the link between purposes, context of collection, nature of data, consequences, and safeguards.",
        "question": "Is a compatibility assessment conducted before personal data is used for new purposes?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Data used for new purposes without assessment."},
            {"score": 1, "description": "Informal consideration of compatibility but not documented."},
            {"score": 2, "description": "Compatibility considered for some new uses but no formal assessment process."},
            {"score": 3, "description": "Formal compatibility assessment process with documented criteria, conducted before any further processing, and approved by DPO or privacy team."},
            {"score": 4, "description": "Automated compatibility scoring with risk-based thresholds, mandatory DPIA triggers, and audit trail of all purpose change decisions."},
        ],
        "evidence": [
            {"text": "Compatibility assessment procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Completed compatibility assessment records", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "GDPR-2.3": {
        "title": "Privacy Notices and Transparency",
        "guidance": "The organisation shall provide data subjects with clear, concise, and accessible information about processing at the time of collection (Article 13) or within a reasonable period for indirect collection (Article 14).",
        "question": "Are privacy notices provided that are clear, concise, accessible, and contain all required information?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No privacy notices provided."},
            {"score": 1, "description": "Privacy notices exist but are unclear, incomplete, or difficult to find."},
            {"score": 2, "description": "Privacy notices contain most required information but not layered or easily accessible."},
            {"score": 3, "description": "Layered privacy notices provided at point of collection with all Article 13/14 information, in clear language, and easily accessible."},
            {"score": 4, "description": "Dynamic privacy notices with just-in-time information, multi-format delivery, accessibility compliance, and regular readability testing."},
        ],
        "evidence": [
            {"text": "Privacy notices for all collection channels", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of notice delivery at point of collection", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Data Minimisation ──
    "GDPR-3.1": {
        "title": "Adequacy and Relevance of Data",
        "guidance": "Personal data shall be adequate, relevant, and limited to what is necessary in relation to the purposes for which they are processed (Article 5(1)(c)).",
        "question": "Is personal data collected limited to what is adequate, relevant, and necessary for the stated purposes?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Excessive data collected without justification."},
            {"score": 1, "description": "Some awareness of minimisation but data fields not reviewed."},
            {"score": 2, "description": "Data fields reviewed for some systems but not all, or justification not documented."},
            {"score": 3, "description": "Data minimisation applied to all processing activities with documented justification for each data field collected."},
            {"score": 4, "description": "Privacy-by-design with automated data field justification, regular minimisation reviews, and data discovery tools to detect excess collection."},
        ],
        "evidence": [
            {"text": "Data minimisation assessment for processing activities", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data field justification documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-3.2": {
        "title": "Pseudonymisation and Anonymisation",
        "guidance": "The organisation shall implement pseudonymisation and anonymisation techniques where appropriate to reduce risks to data subjects while enabling processing objectives.",
        "question": "Are pseudonymisation and anonymisation techniques applied where appropriate?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No pseudonymisation or anonymisation applied."},
            {"score": 1, "description": "Awareness of techniques but not implemented."},
            {"score": 2, "description": "Applied in some areas but not systematically assessed across all processing."},
            {"score": 3, "description": "Pseudonymisation and anonymisation assessed for all processing, applied where appropriate, with documented rationale and technical measures."},
            {"score": 4, "description": "Advanced privacy-enhancing technologies with differential privacy, synthetic data generation, and regular re-identification risk assessments."},
        ],
        "evidence": [
            {"text": "Pseudonymisation and anonymisation policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Technical implementation records for pseudonymisation measures", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "GDPR-3.3": {
        "title": "Data Protection by Design and Default",
        "guidance": "The organisation shall implement appropriate technical and organisational measures designed to implement data protection principles and integrate safeguards into processing, both at the time of design and during processing (Article 25).",
        "question": "Is data protection by design and by default implemented in new systems and processing activities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No consideration of privacy in system design."},
            {"score": 1, "description": "Privacy considered ad-hoc but not embedded in design processes."},
            {"score": 2, "description": "Privacy requirements included in some projects but no formal by-design methodology."},
            {"score": 3, "description": "Data protection by design and default embedded in project methodology with privacy requirements, default settings minimising data, and DPIA triggers."},
            {"score": 4, "description": "Privacy engineering programme with automated privacy impact screening, privacy patterns library, and continuous privacy testing in CI/CD."},
        ],
        "evidence": [
            {"text": "Data protection by design procedure or methodology", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of privacy requirements in project documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Accuracy ──
    "GDPR-4.1": {
        "title": "Data Accuracy and Currency",
        "guidance": "Personal data shall be accurate and, where necessary, kept up to date. Every reasonable step shall be taken to ensure inaccurate data is erased or rectified without delay (Article 5(1)(d)).",
        "question": "Are processes in place to ensure personal data is accurate and kept up to date?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No data accuracy processes."},
            {"score": 1, "description": "Data entered but no validation or update processes."},
            {"score": 2, "description": "Some validation at entry but no ongoing accuracy reviews."},
            {"score": 3, "description": "Data accuracy processes with validation at entry, periodic reviews, update mechanisms, and procedures to rectify inaccurate data without delay."},
            {"score": 4, "description": "Automated data quality monitoring with accuracy scoring, real-time validation, self-service update portals, and data quality dashboards."},
        ],
        "evidence": [
            {"text": "Data quality and accuracy procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data quality review records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-4.2": {
        "title": "Rectification Processes",
        "guidance": "The organisation shall have processes to rectify inaccurate personal data and complete incomplete data, including notifying recipients of rectified data where feasible.",
        "question": "Are rectification processes in place to correct inaccurate data and notify recipients?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No rectification processes."},
            {"score": 1, "description": "Data corrected on request but no formal process."},
            {"score": 2, "description": "Rectification process exists but recipient notification not addressed."},
            {"score": 3, "description": "Formal rectification process with timely correction, recipient notification where feasible, and records of rectification actions."},
            {"score": 4, "description": "Automated rectification workflows with cascading updates across systems, recipient notification tracking, and data subject confirmation."},
        ],
        "evidence": [
            {"text": "Rectification procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Rectification request and action logs", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "GDPR-4.3": {
        "title": "Data Quality Controls",
        "guidance": "The organisation shall implement technical and organisational measures to maintain data quality including input validation, duplicate detection, and regular data cleansing.",
        "question": "Are technical and organisational data quality controls implemented?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No data quality controls."},
            {"score": 1, "description": "Basic input validation only."},
            {"score": 2, "description": "Some quality controls but not comprehensive or regularly reviewed."},
            {"score": 3, "description": "Comprehensive data quality controls with input validation, duplicate detection, regular cleansing, and quality metrics tracked."},
            {"score": 4, "description": "Enterprise data quality framework with automated profiling, machine learning anomaly detection, and continuous quality improvement."},
        ],
        "evidence": [
            {"text": "Data quality control procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data quality metrics and reports", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Storage Limitation ──
    "GDPR-5.1": {
        "title": "Retention Policies and Schedules",
        "guidance": "Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which it is processed (Article 5(1)(e)).",
        "question": "Are retention policies and schedules defined for all personal data processing activities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No retention policies or schedules."},
            {"score": 1, "description": "Some awareness of retention requirements but no formal schedules."},
            {"score": 2, "description": "Retention schedules exist for some data but not comprehensive."},
            {"score": 3, "description": "Retention policies and schedules defined for all processing activities, justified by purpose, and regularly reviewed."},
            {"score": 4, "description": "Automated retention management with policy-driven deletion, retention analytics, and compliance monitoring dashboards."},
        ],
        "evidence": [
            {"text": "Data retention policy and schedules", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Retention schedule review records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-5.2": {
        "title": "Secure Deletion and Destruction",
        "guidance": "The organisation shall implement secure deletion and destruction processes for personal data that has reached the end of its retention period, including data in backups and archives.",
        "question": "Are secure deletion and destruction processes implemented for expired personal data?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No secure deletion processes."},
            {"score": 1, "description": "Data deleted on request but no systematic process."},
            {"score": 2, "description": "Deletion processes exist but backups and archives not addressed."},
            {"score": 3, "description": "Secure deletion processes for all storage media including backups, with certificates of destruction and audit trails."},
            {"score": 4, "description": "Automated lifecycle management with crypto-shredding, verified deletion across all replicas, and destruction certification."},
        ],
        "evidence": [
            {"text": "Secure deletion and destruction procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Deletion logs or certificates of destruction", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-5.3": {
        "title": "Archiving and Research Exemptions",
        "guidance": "Where personal data is retained for archiving in the public interest, scientific or historical research, or statistical purposes, appropriate safeguards shall be implemented including pseudonymisation.",
        "question": "Where data is retained beyond primary purposes for archiving or research, are appropriate safeguards applied?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "Data retained indefinitely without safeguards."},
            {"score": 1, "description": "Some data archived but no specific safeguards."},
            {"score": 2, "description": "Archiving recognised but pseudonymisation or access controls not applied."},
            {"score": 3, "description": "Archiving and research exemptions documented with pseudonymisation, access controls, and purpose limitation safeguards."},
            {"score": 4, "description": "Privacy-preserving analytics with differential privacy, secure research environments, and ethics board oversight."},
        ],
        "evidence": [
            {"text": "Archiving and research data policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Safeguard implementation records for archived data", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── Integrity and Confidentiality ──
    "GDPR-6.1": {
        "title": "Security of Processing",
        "guidance": "The organisation shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk, including encryption, pseudonymisation, resilience, and regular testing (Article 32).",
        "question": "Are appropriate technical and organisational security measures implemented for personal data processing?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No security measures for personal data."},
            {"score": 1, "description": "Basic security but not risk-assessed or comprehensive."},
            {"score": 2, "description": "Security measures in place but not regularly tested or reviewed."},
            {"score": 3, "description": "Risk-appropriate security measures including encryption, access controls, resilience measures, and regular testing of effectiveness."},
            {"score": 4, "description": "Defence-in-depth with zero-trust architecture, continuous security monitoring, automated threat response, and regular penetration testing."},
        ],
        "evidence": [
            {"text": "Information security policy and risk assessment for personal data", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Security testing and review records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-6.2": {
        "title": "Personal Data Breach Management",
        "guidance": "The organisation shall have processes to detect, report, and investigate personal data breaches. Breaches likely to result in risk to individuals shall be notified to the supervisory authority within 72 hours (Article 33) and to affected individuals where high risk (Article 34).",
        "question": "Are personal data breach detection, notification, and management processes established?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No breach management processes."},
            {"score": 1, "description": "Breaches handled ad-hoc without formal process."},
            {"score": 2, "description": "Breach procedure exists but 72-hour notification timeline not achievable or breach register incomplete."},
            {"score": 3, "description": "Breach management process with detection, assessment, 72-hour authority notification, individual notification for high risk, breach register, and lessons learned."},
            {"score": 4, "description": "Automated breach detection with SIEM integration, pre-drafted notification templates, breach simulation exercises, and real-time risk assessment."},
        ],
        "evidence": [
            {"text": "Personal data breach management procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Breach register and notification records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-6.3": {
        "title": "International Data Transfers",
        "guidance": "Transfers of personal data to third countries shall only take place where adequate safeguards are in place, such as adequacy decisions, standard contractual clauses, binding corporate rules, or derogations under Article 49.",
        "question": "Are international data transfers conducted with appropriate safeguards and transfer mechanisms?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "International transfers without safeguards."},
            {"score": 1, "description": "Awareness of transfer restrictions but mechanisms not implemented."},
            {"score": 2, "description": "Some transfer mechanisms in place but not all transfers assessed or documented."},
            {"score": 3, "description": "All international transfers identified, appropriate transfer mechanisms in place (SCCs, adequacy, BCRs), transfer impact assessments conducted, and documented."},
            {"score": 4, "description": "Automated transfer mapping with real-time monitoring, supplementary measures assessment, and continuous adequacy tracking."},
        ],
        "evidence": [
            {"text": "International transfer register with mechanisms", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Transfer impact assessments and standard contractual clauses", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Accountability ──
    "GDPR-7.1": {
        "title": "Data Protection Officer and Governance",
        "guidance": "The organisation shall designate a DPO where required (Article 37), maintain records of processing activities (Article 30), and implement appropriate governance structures for data protection.",
        "question": "Is a DPO designated where required and are data protection governance structures in place?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No data protection governance or DPO consideration."},
            {"score": 1, "description": "Privacy responsibilities informally assigned but no DPO assessment."},
            {"score": 2, "description": "DPO assessment conducted but governance structures incomplete."},
            {"score": 3, "description": "DPO designated where required with appropriate independence, Article 30 records maintained, and governance structures with clear reporting lines."},
            {"score": 4, "description": "Privacy office with dedicated team, board-level reporting, privacy steering committee, and integrated privacy governance framework."},
        ],
        "evidence": [
            {"text": "DPO designation or assessment of DPO requirement", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data protection governance structure documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-7.2": {
        "title": "Data Protection Impact Assessments",
        "guidance": "The organisation shall carry out DPIAs for processing likely to result in high risk to individuals, including systematic evaluation, necessity and proportionality assessment, risk assessment, and measures to address risks (Article 35).",
        "question": "Are DPIAs conducted for high-risk processing activities with documented risk mitigation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No DPIAs conducted."},
            {"score": 1, "description": "Awareness of DPIA requirement but no formal process."},
            {"score": 2, "description": "DPIAs conducted for some activities but screening criteria not defined or risk mitigation incomplete."},
            {"score": 3, "description": "DPIA screening criteria defined, DPIAs conducted for all high-risk processing, with risk assessment, mitigation measures, and DPO consultation."},
            {"score": 4, "description": "Automated DPIA screening integrated with project management, DPIA templates with risk scoring, supervisory authority consultation where required, and DPIA reviews."},
        ],
        "evidence": [
            {"text": "DPIA procedure and screening criteria", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Completed DPIA records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-7.3": {
        "title": "Processor Management",
        "guidance": "The organisation shall use only processors providing sufficient guarantees. Processing by a processor shall be governed by a contract or legal act setting out subject matter, duration, nature, purpose, data types, and controller obligations (Article 28).",
        "question": "Are data processors managed with appropriate contracts and ongoing oversight?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No processor management or contracts."},
            {"score": 1, "description": "Some processor contracts but not all compliant with Article 28."},
            {"score": 2, "description": "Contracts in place but processor due diligence or ongoing monitoring not conducted."},
            {"score": 3, "description": "All processors under Article 28 compliant contracts, due diligence conducted, sub-processor controls in place, and ongoing monitoring."},
            {"score": 4, "description": "Processor management platform with automated contract tracking, continuous compliance monitoring, audit rights exercised, and risk-based oversight."},
        ],
        "evidence": [
            {"text": "Processor register with contract status", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Data processing agreements (Article 28 contracts)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Data Subject Rights ──
    "GDPR-8.1": {
        "title": "Right of Access and Portability",
        "guidance": "Data subjects have the right to obtain confirmation of processing, access to their data (Article 15), and to receive their data in a structured, commonly used, machine-readable format (Article 20).",
        "question": "Are processes in place to handle data subject access requests and data portability requests?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No process for handling access or portability requests."},
            {"score": 1, "description": "Requests handled ad-hoc without formal process or timelines."},
            {"score": 2, "description": "Process exists but response within one month not consistently achieved or portability format not machine-readable."},
            {"score": 3, "description": "Formal DSAR process with identity verification, one-month response, machine-readable portability format, and exemption assessment."},
            {"score": 4, "description": "Self-service data access portal with automated data compilation, real-time portability export, and request tracking dashboard."},
        ],
        "evidence": [
            {"text": "Data subject access request procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "DSAR response logs and sample responses", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-8.2": {
        "title": "Right to Erasure and Restriction",
        "guidance": "Data subjects have the right to erasure (Article 17) where data is no longer necessary, consent is withdrawn, or processing is unlawful. They also have the right to restrict processing (Article 18) in certain circumstances.",
        "question": "Are processes in place to handle erasure and restriction of processing requests?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No process for erasure or restriction requests."},
            {"score": 1, "description": "Requests handled informally without assessment of grounds."},
            {"score": 2, "description": "Erasure process exists but restriction not addressed or recipient notification missing."},
            {"score": 3, "description": "Formal processes for erasure and restriction with grounds assessment, recipient notification, technical implementation, and exemption documentation."},
            {"score": 4, "description": "Automated erasure workflows with cascading deletion across systems, restriction flags, recipient notification tracking, and compliance verification."},
        ],
        "evidence": [
            {"text": "Erasure and restriction request procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Erasure and restriction request logs", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "GDPR-8.3": {
        "title": "Right to Object and Automated Decision-Making",
        "guidance": "Data subjects have the right to object to processing based on legitimate interests or direct marketing (Article 21). They also have the right not to be subject to solely automated decisions with legal or significant effects (Article 22).",
        "question": "Are processes in place for objection rights and safeguards for automated decision-making?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No process for objection or automated decision-making safeguards."},
            {"score": 1, "description": "Objection requests handled but automated decision-making not assessed."},
            {"score": 2, "description": "Objection process exists but automated decision-making safeguards incomplete."},
            {"score": 3, "description": "Formal objection process with legitimate interests balancing, direct marketing opt-out, automated decision-making identified with human review and safeguards."},
            {"score": 4, "description": "Automated objection handling with real-time processing cessation, AI fairness assessments, explainability tools, and human-in-the-loop governance."},
        ],
        "evidence": [
            {"text": "Objection handling procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Automated decision-making register with safeguards", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
}

SCOPING_QUESTIONS = [
    {
        "identifier": "gdpr-q1",
        "question_text": "Does the organisation process special category data (e.g. health, biometric, racial/ethnic origin, political opinions)?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "gdpr-q2",
        "question_text": "Does the organisation transfer personal data to countries outside the EEA?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "gdpr-q3",
        "question_text": "Does the organisation use automated decision-making or profiling with legal or significant effects on individuals?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
]

SCOPING_RULES = [
    {
        "question_identifier": "gdpr-q1",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "GDPR-1.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "gdpr-q1",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "GDPR-1.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "gdpr-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "GDPR-6.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "gdpr-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "GDPR-6.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "gdpr-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "GDPR-8.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "gdpr-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "GDPR-8.3",
        "applicability_status": "not_applicable",
    },
]
