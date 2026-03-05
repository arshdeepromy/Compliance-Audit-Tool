"""NIST CSF 2.0 — Cybersecurity Framework template seed data.

Contains 6 core function sections with 5 criteria each (30 total),
5 scoping questions, and scoping rules for OT/ICS and cloud
environments.
"""

TEMPLATE_NAME = "NIST CSF 2.0 \u2014 Cybersecurity Framework"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "IT Security",
    "compliance_framework": "NIST CSF 2.0",
}

# ---------- Sections (6 core functions) ----------

SECTIONS = [
    {
        "name": "GV: Govern",
        "codes": ["NIST-GV.1", "NIST-GV.2", "NIST-GV.3", "NIST-GV.4", "NIST-GV.5"],
    },
    {
        "name": "ID: Identify",
        "codes": ["NIST-ID.1", "NIST-ID.2", "NIST-ID.3", "NIST-ID.4", "NIST-ID.5"],
    },
    {
        "name": "PR: Protect",
        "codes": ["NIST-PR.1", "NIST-PR.2", "NIST-PR.3", "NIST-PR.4", "NIST-PR.5"],
    },
    {
        "name": "DE: Detect",
        "codes": ["NIST-DE.1", "NIST-DE.2", "NIST-DE.3", "NIST-DE.4", "NIST-DE.5"],
    },
    {
        "name": "RS: Respond",
        "codes": ["NIST-RS.1", "NIST-RS.2", "NIST-RS.3", "NIST-RS.4", "NIST-RS.5"],
    },
    {
        "name": "RC: Recover",
        "codes": ["NIST-RC.1", "NIST-RC.2", "NIST-RC.3", "NIST-RC.4", "NIST-RC.5"],
    },
]

# ---------- Criteria (5 per section, 30 total) ----------

CRITERIA = {
    # ── GV: Govern ──
    "NIST-GV.1": {
        "title": "Organisational Context",
        "guidance": "The organisational mission, stakeholder expectations, and legal/regulatory requirements relevant to cybersecurity risk are understood and inform risk management decisions.",
        "question": "Has the organisation documented its mission, stakeholder expectations, and legal/regulatory cybersecurity obligations?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No documented organisational context for cybersecurity."},
            {"score": 1, "description": "Some awareness of obligations but not formally documented."},
            {"score": 2, "description": "Context documented but not integrated into risk decisions."},
            {"score": 3, "description": "Organisational context documented, reviewed annually, and used to inform cybersecurity strategy."},
            {"score": 4, "description": "Context continuously updated with automated regulatory change tracking and board-level reporting."},
        ],
        "evidence": [
            {"text": "Cybersecurity strategy document referencing organisational mission", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Legal and regulatory obligations register", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-GV.2": {
        "title": "Risk Management Strategy",
        "guidance": "The organisation's risk management strategy is established, communicated, and used to support cybersecurity decisions.",
        "question": "Is there a documented cybersecurity risk management strategy approved by senior leadership?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No risk management strategy."},
            {"score": 1, "description": "Informal risk management with no documented strategy."},
            {"score": 2, "description": "Strategy documented but not communicated or consistently applied."},
            {"score": 3, "description": "Strategy approved by leadership, communicated to stakeholders, and reviewed annually."},
            {"score": 4, "description": "Strategy integrated with enterprise risk management, with quantitative risk analysis and continuous review."},
        ],
        "evidence": [
            {"text": "Cybersecurity risk management strategy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of senior leadership approval and communication", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-GV.3": {
        "title": "Roles, Responsibilities, and Authorities",
        "guidance": "Cybersecurity roles, responsibilities, and authorities are established and communicated to foster accountability.",
        "question": "Are cybersecurity roles, responsibilities, and authorities clearly defined and communicated?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined cybersecurity roles or responsibilities."},
            {"score": 1, "description": "Some roles informally assigned but not documented."},
            {"score": 2, "description": "Roles documented but not communicated or enforced."},
            {"score": 3, "description": "Roles and responsibilities documented, assigned to named individuals, and communicated across the organisation."},
            {"score": 4, "description": "RACI matrix maintained, integrated with HR processes, and reviewed with each organisational change."},
        ],
        "evidence": [
            {"text": "Cybersecurity RACI or roles and responsibilities matrix", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Evidence of communication to relevant personnel", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "NIST-GV.4": {
        "title": "Cybersecurity Policy",
        "guidance": "Cybersecurity policy is established, communicated, and enforced to provide a framework for managing cybersecurity risk.",
        "question": "Is there a comprehensive cybersecurity policy that is communicated and enforced?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No cybersecurity policy."},
            {"score": 1, "description": "Policy exists but is outdated or incomplete."},
            {"score": 2, "description": "Policy documented but not consistently enforced."},
            {"score": 3, "description": "Comprehensive policy reviewed annually, communicated to all staff, with enforcement mechanisms."},
            {"score": 4, "description": "Policy automated where possible, with continuous compliance monitoring and exception management."},
        ],
        "evidence": [
            {"text": "Cybersecurity policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Staff acknowledgement records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-GV.5": {
        "title": "Oversight and Governance",
        "guidance": "Senior leadership provides oversight of cybersecurity risk management, ensuring alignment with organisational objectives.",
        "question": "Does senior leadership actively oversee cybersecurity risk management activities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No senior leadership oversight of cybersecurity."},
            {"score": 1, "description": "Ad-hoc reporting to leadership with no regular cadence."},
            {"score": 2, "description": "Periodic reporting but leadership not actively engaged."},
            {"score": 3, "description": "Regular board/executive reporting, cybersecurity on risk committee agenda, metrics tracked."},
            {"score": 4, "description": "Real-time cybersecurity dashboard for leadership, integrated with business risk reporting and strategic planning."},
        ],
        "evidence": [
            {"text": "Board or executive committee meeting minutes covering cybersecurity", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Cybersecurity metrics and KPI report for leadership", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── ID: Identify ──
    "NIST-ID.1": {
        "title": "Asset Management",
        "guidance": "Physical and software assets within the organisation are inventoried and managed consistent with their relative importance to business objectives and risk strategy.",
        "question": "Does the organisation maintain a comprehensive inventory of all hardware and software assets?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No asset inventory."},
            {"score": 1, "description": "Partial inventory with significant gaps."},
            {"score": 2, "description": "Inventory exists but not regularly updated or classified."},
            {"score": 3, "description": "Complete asset inventory with classification, ownership, and quarterly review cycle."},
            {"score": 4, "description": "Automated asset discovery with real-time CMDB integration and risk-based classification."},
        ],
        "evidence": [
            {"text": "Hardware and software asset inventory", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Asset classification and ownership records", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "NIST-ID.2": {
        "title": "Cloud Asset Inventory",
        "guidance": "Cloud-based assets, services, and configurations are identified, inventoried, and managed alongside on-premises assets.",
        "question": "Are cloud-based assets and services inventoried and managed with the same rigour as on-premises assets?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud asset inventory."},
            {"score": 1, "description": "Some cloud assets tracked but inventory is incomplete."},
            {"score": 2, "description": "Cloud inventory exists but not integrated with overall asset management."},
            {"score": 3, "description": "Cloud assets fully inventoried, tagged, and integrated with enterprise CMDB; reviewed quarterly."},
            {"score": 4, "description": "Cloud asset management automated via API with real-time drift detection and cost optimisation."},
        ],
        "evidence": [
            {"text": "Cloud asset inventory or cloud management platform export", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of integration with enterprise asset management", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },
    "NIST-ID.3": {
        "title": "Risk Assessment",
        "guidance": "The organisation understands cybersecurity risks to operations, assets, and individuals through formal risk assessment processes.",
        "question": "Does the organisation conduct formal cybersecurity risk assessments at least annually?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No risk assessment performed."},
            {"score": 1, "description": "Ad-hoc risk identification with no formal methodology."},
            {"score": 2, "description": "Risk assessment performed but methodology inconsistent or outdated."},
            {"score": 3, "description": "Annual risk assessment using a recognised methodology, with risk register maintained and reviewed."},
            {"score": 4, "description": "Continuous risk assessment with threat intelligence integration and automated risk scoring."},
        ],
        "evidence": [
            {"text": "Most recent cybersecurity risk assessment report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Risk register with treatment plans", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-ID.4": {
        "title": "Supply Chain Risk Management",
        "guidance": "The organisation identifies, assesses, and manages cybersecurity risks associated with its supply chain and third-party relationships.",
        "question": "Are cybersecurity risks from suppliers and third-party service providers identified and managed?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No supply chain risk management."},
            {"score": 1, "description": "Some awareness of third-party risks but no formal process."},
            {"score": 2, "description": "Third-party risk assessments performed but not comprehensive."},
            {"score": 3, "description": "Formal supply chain risk management programme with vendor assessments, contractual requirements, and monitoring."},
            {"score": 4, "description": "Automated third-party risk monitoring with continuous assessment and real-time risk scoring."},
        ],
        "evidence": [
            {"text": "Supply chain risk management policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Third-party risk assessment records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-ID.5": {
        "title": "Improvement and Lessons Learned",
        "guidance": "Improvements to organisational cybersecurity risk management processes are identified from assessments, audits, and operational experience.",
        "question": "Does the organisation systematically identify and implement improvements to its cybersecurity programme?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No improvement process."},
            {"score": 1, "description": "Improvements made reactively after incidents only."},
            {"score": 2, "description": "Some lessons learned captured but not systematically applied."},
            {"score": 3, "description": "Formal improvement process with lessons learned from audits, incidents, and assessments tracked and implemented."},
            {"score": 4, "description": "Continuous improvement programme with maturity benchmarking and automated tracking of improvement actions."},
        ],
        "evidence": [
            {"text": "Improvement action log or corrective action register", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Lessons learned reports from recent incidents or audits", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── PR: Protect ──
    "NIST-PR.1": {
        "title": "Identity Management and Access Control",
        "guidance": "Access to physical and logical assets is limited to authorised users, processes, and devices, managed consistent with the assessed risk.",
        "question": "Are identity management and access control policies implemented to restrict access to authorised entities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identity or access management controls."},
            {"score": 1, "description": "Basic user accounts exist but no formal access control policy."},
            {"score": 2, "description": "Access control policy exists but not consistently enforced."},
            {"score": 3, "description": "Role-based access control implemented, least privilege enforced, access reviews conducted quarterly."},
            {"score": 4, "description": "Zero-trust architecture with continuous authentication, adaptive access controls, and automated provisioning/deprovisioning."},
        ],
        "evidence": [
            {"text": "Access control policy document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of quarterly access reviews", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-PR.2": {
        "title": "Awareness and Training",
        "guidance": "Personnel and partners are provided cybersecurity awareness education and training to perform their duties consistent with related policies and agreements.",
        "question": "Do all personnel receive cybersecurity awareness training appropriate to their roles?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No cybersecurity awareness training."},
            {"score": 1, "description": "Ad-hoc training with no formal programme."},
            {"score": 2, "description": "Annual training exists but not role-specific."},
            {"score": 3, "description": "Role-based training programme with annual completion tracking and phishing simulations."},
            {"score": 4, "description": "Continuous training with adaptive content, gamification, and measured behaviour change metrics."},
        ],
        "evidence": [
            {"text": "Security awareness training programme description", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Training completion records for current period", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-PR.3": {
        "title": "Data Security",
        "guidance": "Data is managed consistent with the organisation's risk strategy to protect the confidentiality, integrity, and availability of information.",
        "question": "Are data protection controls implemented to safeguard data at rest, in transit, and in use?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No data protection controls."},
            {"score": 1, "description": "Some encryption in use but no comprehensive data protection strategy."},
            {"score": 2, "description": "Data protection measures exist but gaps in coverage."},
            {"score": 3, "description": "Data classified, encryption applied at rest and in transit, DLP controls in place, retention policies enforced."},
            {"score": 4, "description": "Automated data discovery and classification, end-to-end encryption, and real-time DLP with machine learning."},
        ],
        "evidence": [
            {"text": "Data classification and protection policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Encryption standards and implementation evidence", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "NIST-PR.4": {
        "title": "OT Network Segmentation",
        "guidance": "Operational technology (OT) networks are segmented from IT networks to limit the blast radius of cyber incidents and protect industrial control systems.",
        "question": "Are OT/ICS networks segmented from corporate IT networks with appropriate boundary controls?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No OT network segmentation."},
            {"score": 1, "description": "Partial segmentation with significant gaps."},
            {"score": 2, "description": "Segmentation in place but not validated or monitored."},
            {"score": 3, "description": "OT networks fully segmented with DMZ, validated by testing, and monitored for cross-boundary traffic."},
            {"score": 4, "description": "Micro-segmentation with OT-specific firewalls, unidirectional gateways, and continuous monitoring."},
        ],
        "evidence": [
            {"text": "OT/IT network segmentation architecture diagram", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Segmentation validation test results", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-PR.5": {
        "title": "Cloud Identity Management",
        "guidance": "Cloud identity and access management controls ensure that access to cloud resources is governed with the same rigour as on-premises systems.",
        "question": "Are cloud identity and access management controls implemented with MFA and least-privilege principles?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud-specific identity management."},
            {"score": 1, "description": "Basic cloud accounts but no formal IAM policy."},
            {"score": 2, "description": "Cloud IAM configured but MFA not enforced or roles overly permissive."},
            {"score": 3, "description": "Cloud IAM with MFA enforced, least-privilege roles, service account management, and regular access reviews."},
            {"score": 4, "description": "Cloud-native identity governance with just-in-time access, automated anomaly detection, and federated identity."},
        ],
        "evidence": [
            {"text": "Cloud IAM policy and configuration documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Cloud access review records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── DE: Detect ──
    "NIST-DE.1": {
        "title": "Continuous Monitoring",
        "guidance": "The information system and assets are monitored to identify cybersecurity events and verify the effectiveness of protective measures.",
        "question": "Is continuous monitoring implemented to detect cybersecurity events across the environment?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No monitoring capabilities."},
            {"score": 1, "description": "Basic logging but no active monitoring or alerting."},
            {"score": 2, "description": "Monitoring in place for some systems but gaps in coverage."},
            {"score": 3, "description": "SIEM deployed with log aggregation from all critical systems, alerting rules defined, and 24/7 monitoring."},
            {"score": 4, "description": "Advanced SOAR platform with automated triage, threat hunting, and machine learning-based anomaly detection."},
        ],
        "evidence": [
            {"text": "Monitoring architecture and SIEM configuration documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Log source inventory showing coverage", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-DE.2": {
        "title": "Anomaly and Event Analysis",
        "guidance": "Detected events are analysed to understand attack targets and methods, and anomalies are correlated to identify potential incidents.",
        "question": "Are detected security events analysed and correlated to identify potential incidents?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No event analysis capability."},
            {"score": 1, "description": "Events logged but not analysed."},
            {"score": 2, "description": "Basic analysis performed but no correlation or trending."},
            {"score": 3, "description": "Events correlated using SIEM rules, analysed by trained analysts, with documented escalation procedures."},
            {"score": 4, "description": "AI-driven event correlation with automated threat intelligence enrichment and predictive analytics."},
        ],
        "evidence": [
            {"text": "Event analysis and correlation procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Sample event analysis reports from recent period", "age_label": "< 3 months", "age_class": "age-1y", "required": False},
        ],
    },
    "NIST-DE.3": {
        "title": "OT Monitoring",
        "guidance": "Operational technology environments are monitored for anomalous activity using OT-aware detection tools and protocols.",
        "question": "Are OT/ICS environments monitored for anomalous activity using OT-specific detection capabilities?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No OT-specific monitoring."},
            {"score": 1, "description": "Basic network monitoring but not OT-protocol aware."},
            {"score": 2, "description": "Some OT monitoring but limited protocol coverage."},
            {"score": 3, "description": "OT-aware monitoring deployed covering major protocols (Modbus, DNP3, OPC), with baseline behaviour established."},
            {"score": 4, "description": "Passive OT monitoring with deep packet inspection, asset discovery, and integration with IT SIEM."},
        ],
        "evidence": [
            {"text": "OT monitoring architecture and tool documentation", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "OT baseline behaviour documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-DE.4": {
        "title": "Vulnerability Management",
        "guidance": "Vulnerability scans and assessments are performed regularly to identify and remediate weaknesses before they can be exploited.",
        "question": "Are regular vulnerability scans and assessments performed across all in-scope systems?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No vulnerability scanning."},
            {"score": 1, "description": "Ad-hoc scanning with no regular schedule."},
            {"score": 2, "description": "Regular scans performed but remediation is slow or inconsistent."},
            {"score": 3, "description": "Authenticated scans performed monthly, critical vulnerabilities remediated within SLA, risk-based prioritisation."},
            {"score": 4, "description": "Continuous vulnerability scanning with automated patching, risk-based prioritisation, and integration with threat intelligence."},
        ],
        "evidence": [
            {"text": "Vulnerability management policy and scan schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Most recent vulnerability scan report with remediation status", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-DE.5": {
        "title": "Cloud Configuration Monitoring",
        "guidance": "Cloud service configurations are continuously monitored for drift, misconfigurations, and compliance violations.",
        "question": "Are cloud configurations monitored for drift and misconfigurations using automated tools?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud configuration monitoring."},
            {"score": 1, "description": "Manual periodic reviews of cloud configurations."},
            {"score": 2, "description": "Some automated checks but coverage is incomplete."},
            {"score": 3, "description": "CSPM tool deployed covering all cloud accounts, with alerting for misconfigurations and compliance violations."},
            {"score": 4, "description": "Infrastructure-as-code with automated drift detection, auto-remediation, and compliance-as-code pipelines."},
        ],
        "evidence": [
            {"text": "Cloud security posture management tool configuration", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Recent cloud configuration compliance report", "age_label": "< 1 month", "age_class": "age-1y", "required": True},
        ],
    },

    # ── RS: Respond ──
    "NIST-RS.1": {
        "title": "Incident Response Planning",
        "guidance": "Response processes and procedures are established and maintained to ensure timely response to detected cybersecurity incidents.",
        "question": "Is there a documented incident response plan that is tested and maintained?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No incident response plan."},
            {"score": 1, "description": "Informal response procedures with no documented plan."},
            {"score": 2, "description": "Plan documented but not tested or outdated."},
            {"score": 3, "description": "Incident response plan documented, tested annually via tabletop exercises, and updated based on lessons learned."},
            {"score": 4, "description": "Automated incident response playbooks with SOAR integration, regular red team exercises, and continuous improvement."},
        ],
        "evidence": [
            {"text": "Incident response plan document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Most recent incident response test or exercise report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-RS.2": {
        "title": "Incident Communications",
        "guidance": "Response activities are coordinated with internal and external stakeholders, including law enforcement and regulatory bodies as required.",
        "question": "Are incident communication procedures defined for internal and external stakeholders?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No incident communication procedures."},
            {"score": 1, "description": "Ad-hoc communication during incidents."},
            {"score": 2, "description": "Communication procedures exist but contact lists are outdated."},
            {"score": 3, "description": "Communication plan with defined escalation paths, stakeholder contact lists, and regulatory notification procedures."},
            {"score": 4, "description": "Automated notification workflows with pre-approved templates, regulatory deadline tracking, and crisis communication platform."},
        ],
        "evidence": [
            {"text": "Incident communication plan with escalation paths", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Stakeholder and regulatory contact list", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-RS.3": {
        "title": "Incident Analysis",
        "guidance": "Analysis is conducted to ensure effective response and support forensic investigation and recovery activities.",
        "question": "Are incidents analysed to determine root cause, impact, and scope?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No incident analysis capability."},
            {"score": 1, "description": "Basic incident logging but no root cause analysis."},
            {"score": 2, "description": "Some analysis performed but not consistently or thoroughly."},
            {"score": 3, "description": "Formal incident analysis process with root cause analysis, impact assessment, and forensic capability."},
            {"score": 4, "description": "Advanced forensic capability with automated evidence collection, timeline reconstruction, and threat intelligence correlation."},
        ],
        "evidence": [
            {"text": "Incident analysis procedures document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Sample post-incident analysis report", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "NIST-RS.4": {
        "title": "OT Incident Response",
        "guidance": "Incident response procedures address OT/ICS-specific scenarios including safety implications and operational continuity requirements.",
        "question": "Are OT/ICS-specific incident response procedures defined that address safety and operational continuity?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No OT-specific incident response procedures."},
            {"score": 1, "description": "General IT incident response applied to OT without adaptation."},
            {"score": 2, "description": "Some OT considerations but not comprehensive."},
            {"score": 3, "description": "OT-specific incident response procedures addressing safety, operational continuity, and coordination with plant operations."},
            {"score": 4, "description": "Integrated IT/OT incident response with automated safety interlocks, tested via joint exercises, and vendor coordination."},
        ],
        "evidence": [
            {"text": "OT-specific incident response procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "OT incident response exercise report", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "NIST-RS.5": {
        "title": "Incident Mitigation",
        "guidance": "Activities are performed to prevent expansion of an event, mitigate its effects, and resolve the incident.",
        "question": "Are containment and mitigation procedures defined and executed during incidents?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No containment or mitigation procedures."},
            {"score": 1, "description": "Ad-hoc containment with no predefined procedures."},
            {"score": 2, "description": "Some containment procedures but not comprehensive."},
            {"score": 3, "description": "Documented containment strategies for common incident types, with predefined isolation and mitigation actions."},
            {"score": 4, "description": "Automated containment with network isolation, endpoint quarantine, and orchestrated mitigation playbooks."},
        ],
        "evidence": [
            {"text": "Containment and mitigation procedures by incident type", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of containment actions from recent incidents or exercises", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── RC: Recover ──
    "NIST-RC.1": {
        "title": "Recovery Planning",
        "guidance": "Recovery processes and procedures are established and maintained to ensure timely restoration of systems and assets affected by cybersecurity incidents.",
        "question": "Is there a documented recovery plan for restoring systems and services after a cybersecurity incident?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No recovery plan."},
            {"score": 1, "description": "Informal recovery procedures with no documented plan."},
            {"score": 2, "description": "Recovery plan exists but not tested or outdated."},
            {"score": 3, "description": "Recovery plan documented, tested annually, with defined RTOs and RPOs for critical systems."},
            {"score": 4, "description": "Automated recovery orchestration with tested failover, immutable backups, and sub-hour RTO for critical systems."},
        ],
        "evidence": [
            {"text": "Disaster recovery and business continuity plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Recovery test results with RTO/RPO measurements", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-RC.2": {
        "title": "Recovery Improvements",
        "guidance": "Recovery planning and processes are improved by incorporating lessons learned into future activities.",
        "question": "Are recovery plans updated based on lessons learned from incidents and tests?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No improvement process for recovery plans."},
            {"score": 1, "description": "Improvements made reactively but not documented."},
            {"score": 2, "description": "Some lessons captured but not systematically applied to recovery plans."},
            {"score": 3, "description": "Formal post-incident and post-test review process with documented improvements applied to recovery plans."},
            {"score": 4, "description": "Continuous improvement with automated gap analysis, benchmarking against industry standards, and proactive updates."},
        ],
        "evidence": [
            {"text": "Post-incident or post-test review reports with improvement actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Recovery plan change log showing improvements applied", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "NIST-RC.3": {
        "title": "Recovery Communications",
        "guidance": "Restoration activities are coordinated with internal and external parties, including coordinating centres, ISPs, and system owners.",
        "question": "Are recovery communication procedures defined for coordinating restoration activities with stakeholders?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No recovery communication procedures."},
            {"score": 1, "description": "Ad-hoc communication during recovery."},
            {"score": 2, "description": "Some communication procedures but stakeholder lists incomplete."},
            {"score": 3, "description": "Recovery communication plan with stakeholder notification procedures, status reporting templates, and coordination protocols."},
            {"score": 4, "description": "Automated recovery status dashboards, stakeholder notification workflows, and integrated crisis communication platform."},
        ],
        "evidence": [
            {"text": "Recovery communication plan and stakeholder contact list", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Status reporting templates for recovery activities", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },
    "NIST-RC.4": {
        "title": "Backup and Restoration",
        "guidance": "Backups of data and system configurations are maintained, tested, and protected to support timely recovery.",
        "question": "Are backups performed regularly, tested for integrity, and stored securely including off-site copies?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No backup procedures."},
            {"score": 1, "description": "Some backups taken but not regularly or comprehensively."},
            {"score": 2, "description": "Regular backups but restoration not tested."},
            {"score": 3, "description": "Automated backups with regular restoration testing, off-site storage, and encryption of backup media."},
            {"score": 4, "description": "Immutable backups with air-gapped copies, automated restoration testing, and ransomware-resistant backup architecture."},
        ],
        "evidence": [
            {"text": "Backup policy and schedule documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Backup restoration test results", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "NIST-RC.5": {
        "title": "Reputation Recovery",
        "guidance": "Public relations and reputation management activities are conducted to restore confidence after a cybersecurity incident.",
        "question": "Are reputation management and public communication procedures defined for post-incident recovery?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No reputation recovery procedures."},
            {"score": 1, "description": "Ad-hoc public communication after incidents."},
            {"score": 2, "description": "Some PR procedures but not integrated with incident response."},
            {"score": 3, "description": "Reputation management plan integrated with incident response, with pre-approved messaging and designated spokespersons."},
            {"score": 4, "description": "Proactive reputation management with media monitoring, pre-positioned holding statements, and crisis PR retainer."},
        ],
        "evidence": [
            {"text": "Crisis communication and reputation management plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Designated spokesperson and media contact list", "age_label": "Current", "age_class": "age-na", "required": False},
        ],
    },
}


# ---------- Scoping Questions (5 per Req 5.3) ----------

SCOPING_QUESTIONS = [
    {
        "identifier": "nist-q1",
        "question_text": "Does the organisation operate critical infrastructure?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "nist-q2",
        "question_text": "Is the IT environment primarily cloud-based?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "nist-q3",
        "question_text": "Does the organisation have an operational technology (OT) environment?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
    {
        "identifier": "nist-q4",
        "question_text": "Does the organisation use third-party managed security services?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 3,
    },
    {
        "identifier": "nist-q5",
        "question_text": "Does the organisation process regulated data (PII, PHI, financial)?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 4,
    },
]

# ---------- Scoping Rules (OT and cloud per Req 5.4, 5.5) ----------

SCOPING_RULES = [
    # OT environment (nist-q3 = Yes) → OT-specific criteria applicable
    # Req 5.4: OT network segmentation, OT monitoring, OT incident response
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-PR.4",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-DE.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-RS.4",
        "applicability_status": "applicable",
    },
    # OT environment (nist-q3 = No) → OT-specific criteria not applicable
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-PR.4",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-DE.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "nist-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-RS.4",
        "applicability_status": "not_applicable",
    },
    # Cloud-based environment (nist-q2 = Yes) → cloud-specific criteria applicable
    # Req 5.5: cloud asset inventory, cloud configuration management, cloud identity management
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-ID.2",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-DE.5",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "NIST-PR.5",
        "applicability_status": "applicable",
    },
    # Cloud-based environment (nist-q2 = No) → cloud-specific criteria not applicable
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-ID.2",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-DE.5",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "nist-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "NIST-PR.5",
        "applicability_status": "not_applicable",
    },
]
