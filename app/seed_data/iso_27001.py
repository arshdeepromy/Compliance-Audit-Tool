"""ISO 27001:2022 — Information Security Management template seed data.

Contains 4 Annex A control theme sections with 5 criteria each (20 total),
5 scoping questions, and scoping rules for cloud services and physical
data centre environments.
"""

TEMPLATE_NAME = "ISO 27001:2022 \u2014 Information Security Management"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "IT Security",
    "compliance_framework": "ISO 27001:2022",
}

# ---------- Sections (4 Annex A control themes) ----------

SECTIONS = [
    {
        "name": "A.5 Organisational Controls",
        "codes": ["ISO-5.1", "ISO-5.2", "ISO-5.3", "ISO-5.4", "ISO-5.5"],
    },
    {
        "name": "A.6 People Controls",
        "codes": ["ISO-6.1", "ISO-6.2", "ISO-6.3", "ISO-6.4", "ISO-6.5"],
    },
    {
        "name": "A.7 Physical Controls",
        "codes": ["ISO-7.1", "ISO-7.2", "ISO-7.3", "ISO-7.4", "ISO-7.5"],
    },
    {
        "name": "A.8 Technological Controls",
        "codes": ["ISO-8.1", "ISO-8.2", "ISO-8.3", "ISO-8.4", "ISO-8.5"],
    },
]

# ---------- Criteria (5 per section, 20 total) ----------

CRITERIA = {
    # ── A.5 Organisational Controls ──
    "ISO-5.1": {
        "title": "Policies for Information Security",
        "guidance": "An information security policy and topic-specific policies shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel and interested parties, and reviewed at planned intervals or when significant changes occur.",
        "question": "Are information security policies defined, approved by management, and communicated to all relevant personnel?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No information security policies exist."},
            {"score": 1, "description": "Informal policies exist but are not documented or approved."},
            {"score": 2, "description": "Policies documented but not reviewed regularly or communicated to all staff."},
            {"score": 3, "description": "Policies defined, management-approved, communicated to all personnel, and reviewed at planned intervals."},
            {"score": 4, "description": "Policies integrated into governance framework with automated distribution, acknowledgement tracking, and continuous improvement."},
        ],
        "evidence": [
            {"text": "Information security policy document with management approval", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of policy communication and staff acknowledgement", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Policy review schedule and minutes", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "ISO-5.2": {
        "title": "Information Security Roles and Responsibilities",
        "guidance": "Information security roles and responsibilities shall be defined and allocated. Responsibilities for the protection of individual assets and for carrying out specific information security processes shall be clearly assigned.",
        "question": "Are information security roles and responsibilities clearly defined and allocated across the organisation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined information security roles or responsibilities."},
            {"score": 1, "description": "Some roles informally assigned but not documented."},
            {"score": 2, "description": "Roles documented but gaps in coverage or unclear accountability."},
            {"score": 3, "description": "All information security roles defined, documented, assigned to named individuals, and reviewed annually."},
            {"score": 4, "description": "RACI matrix maintained with automated role assignment tracking and regular competency assessments."},
        ],
        "evidence": [
            {"text": "Information security roles and responsibilities matrix", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Organisation chart showing security function reporting lines", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "ISO-5.3": {
        "title": "Segregation of Duties",
        "guidance": "Conflicting duties and conflicting areas of responsibility shall be segregated to reduce opportunities for unauthorised or unintentional modification or misuse of the organisation's assets.",
        "question": "Are conflicting duties and areas of responsibility segregated to prevent unauthorised actions?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No segregation of duties in place."},
            {"score": 1, "description": "Some segregation but significant conflicts remain."},
            {"score": 2, "description": "Segregation applied to critical processes but not comprehensively reviewed."},
            {"score": 3, "description": "Segregation of duties defined for all critical processes, documented, and reviewed annually."},
            {"score": 4, "description": "Automated access controls enforce segregation with continuous conflict detection and alerting."},
        ],
        "evidence": [
            {"text": "Segregation of duties policy and conflict matrix", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Access review report showing segregation compliance", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-5.4": {
        "title": "Management Responsibilities",
        "guidance": "Management shall require all personnel to apply information security in accordance with the established policies and procedures of the organisation.",
        "question": "Does management actively require and verify that all personnel apply information security policies?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "Management does not enforce information security requirements."},
            {"score": 1, "description": "Management awareness exists but no active enforcement."},
            {"score": 2, "description": "Some management oversight but inconsistent across departments."},
            {"score": 3, "description": "Management actively enforces security policies, includes security in performance reviews, and leads by example."},
            {"score": 4, "description": "Security culture programme with management KPIs, regular leadership communications, and measurable compliance metrics."},
        ],
        "evidence": [
            {"text": "Management commitment statement or charter for information security", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of management review meetings covering security performance", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-5.5": {
        "title": "Information Security in Project Management",
        "guidance": "Information security shall be integrated into project management, regardless of the type of project, to ensure that information security risks are identified and addressed as part of project management.",
        "question": "Is information security integrated into the organisation's project management methodology?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No consideration of security in project management."},
            {"score": 1, "description": "Security considered ad-hoc in some projects."},
            {"score": 2, "description": "Security checkpoints exist but not mandatory for all projects."},
            {"score": 3, "description": "Security risk assessment mandatory at project initiation, design, and go-live phases for all projects."},
            {"score": 4, "description": "Automated security gates in project lifecycle with integrated threat modelling and security sign-off requirements."},
        ],
        "evidence": [
            {"text": "Project management methodology showing security integration points", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Sample project security risk assessment", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── A.6 People Controls ──
    "ISO-6.1": {
        "title": "Screening",
        "guidance": "Background verification checks on all candidates to become personnel shall be carried out prior to joining the organisation and on an ongoing basis, taking into account applicable laws, regulations, and ethics.",
        "question": "Are background verification checks performed on all personnel prior to employment and on an ongoing basis?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No background screening performed."},
            {"score": 1, "description": "Screening performed for some roles only."},
            {"score": 2, "description": "Screening at hiring but no ongoing checks."},
            {"score": 3, "description": "Pre-employment screening for all roles proportionate to risk, with periodic re-screening for sensitive positions."},
            {"score": 4, "description": "Automated continuous screening with risk-based frequency and integration with HR systems."},
        ],
        "evidence": [
            {"text": "Personnel screening policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of screening completion for recent hires", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-6.2": {
        "title": "Terms and Conditions of Employment",
        "guidance": "Employment contractual agreements shall state the personnel's and the organisation's responsibilities for information security, including obligations that extend beyond termination.",
        "question": "Do employment contracts include information security responsibilities and post-termination obligations?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No security clauses in employment contracts."},
            {"score": 1, "description": "Generic confidentiality clause only."},
            {"score": 2, "description": "Security clauses exist but do not cover post-termination obligations."},
            {"score": 3, "description": "Contracts include specific security responsibilities, acceptable use, confidentiality, and post-termination obligations."},
            {"score": 4, "description": "Role-specific security obligations with regular acknowledgement renewal and legal review of clauses."},
        ],
        "evidence": [
            {"text": "Standard employment contract template with security clauses", "age_label": "Current", "age_class": "age-na", "required": True},
            {"text": "Signed confidentiality and acceptable use agreements", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "ISO-6.3": {
        "title": "Information Security Awareness, Education and Training",
        "guidance": "Personnel of the organisation and relevant interested parties shall receive appropriate information security awareness education and training, and regular updates of the organisation's information security policies and procedures.",
        "question": "Do all personnel receive regular information security awareness training and education?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No security awareness training programme."},
            {"score": 1, "description": "Ad-hoc training with no formal programme."},
            {"score": 2, "description": "Annual training exists but completion rates are low or content is outdated."},
            {"score": 3, "description": "Mandatory annual training for all staff with role-specific modules, tracked completion, and regular phishing simulations."},
            {"score": 4, "description": "Continuous learning platform with adaptive content, gamification, measured behaviour change, and targeted interventions."},
        ],
        "evidence": [
            {"text": "Security awareness training programme outline and schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Training completion records and metrics", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
            {"text": "Phishing simulation results", "age_label": "< 6 months", "age_class": "age-1y", "required": False},
        ],
    },
    "ISO-6.4": {
        "title": "Disciplinary Process",
        "guidance": "A disciplinary process shall be formalised and communicated to take actions against personnel and other relevant interested parties who have committed an information security policy violation.",
        "question": "Is there a formal and communicated disciplinary process for information security policy violations?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No disciplinary process for security violations."},
            {"score": 1, "description": "Informal handling of violations on a case-by-case basis."},
            {"score": 2, "description": "Process exists but not communicated to all staff."},
            {"score": 3, "description": "Formal disciplinary process documented, communicated to all staff, and applied consistently."},
            {"score": 4, "description": "Graduated response framework integrated with HR processes, with trend analysis and preventive measures."},
        ],
        "evidence": [
            {"text": "Disciplinary process document for security violations", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of communication to staff (e.g. policy acknowledgement)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-6.5": {
        "title": "Responsibilities After Termination or Change of Employment",
        "guidance": "Information security responsibilities and duties that remain valid after termination or change of employment shall be defined, enforced, and communicated to relevant personnel and other interested parties.",
        "question": "Are information security responsibilities that persist after termination or role change defined and enforced?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No post-termination security procedures."},
            {"score": 1, "description": "Ad-hoc access revocation with no formal process."},
            {"score": 2, "description": "Access revocation process exists but not consistently applied."},
            {"score": 3, "description": "Formal offboarding process with timely access revocation, asset return, and NDA enforcement."},
            {"score": 4, "description": "Automated offboarding workflow integrated with IAM, asset management, and legal systems with audit trail."},
        ],
        "evidence": [
            {"text": "Offboarding and termination security procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of access revocation for recent leavers", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── A.7 Physical Controls ──
    "ISO-7.1": {
        "title": "Physical Security Perimeters",
        "guidance": "Security perimeters shall be defined and used to protect areas that contain information and other associated assets. Physical barriers shall be in place where applicable.",
        "question": "Are physical security perimeters defined and implemented to protect areas containing sensitive information and assets?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No defined physical security perimeters."},
            {"score": 1, "description": "Some physical barriers but perimeters not formally defined."},
            {"score": 2, "description": "Perimeters defined but gaps in physical barriers or access points."},
            {"score": 3, "description": "Security perimeters defined, physical barriers in place, all entry points controlled, and regularly inspected."},
            {"score": 4, "description": "Multi-layered perimeter security with intrusion detection, CCTV, and 24/7 monitoring."},
        ],
        "evidence": [
            {"text": "Physical security perimeter definition and site plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Physical security inspection report", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-7.2": {
        "title": "Physical Entry Controls",
        "guidance": "Secure areas shall be protected by appropriate entry controls to ensure that only authorised personnel are allowed access.",
        "question": "Are secure areas protected by entry controls that restrict access to authorised personnel only?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No physical entry controls for secure areas."},
            {"score": 1, "description": "Basic lock-and-key only with no access logging."},
            {"score": 2, "description": "Electronic access control but visitor management is informal."},
            {"score": 3, "description": "Electronic access control with badge readers, visitor registration, escort policy, and access logs reviewed regularly."},
            {"score": 4, "description": "Multi-factor physical access (badge + biometric), automated visitor management, real-time access monitoring."},
        ],
        "evidence": [
            {"text": "Physical access control policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Access log review records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
            {"text": "Visitor management records", "age_label": "< 3 months", "age_class": "age-1y", "required": False},
        ],
    },
    "ISO-7.3": {
        "title": "Securing Offices, Rooms and Facilities",
        "guidance": "Physical security for offices, rooms, and facilities shall be designed and implemented to protect against unauthorised physical access, damage, and interference.",
        "question": "Is physical security designed and implemented for offices, rooms, and facilities containing sensitive information?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No physical security measures for offices and facilities."},
            {"score": 1, "description": "Basic measures in place but not consistently applied."},
            {"score": 2, "description": "Security measures exist but not reviewed or tested."},
            {"score": 3, "description": "Offices and facilities secured with appropriate controls, clean desk policy enforced, and security reviewed annually."},
            {"score": 4, "description": "Comprehensive facility security with environmental monitoring, automated alerts, and regular penetration testing."},
        ],
        "evidence": [
            {"text": "Facility security standards and clean desk policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Facility security assessment report", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-7.4": {
        "title": "Physical Security Monitoring",
        "guidance": "Premises shall be continuously monitored for unauthorised physical access. Surveillance systems shall be implemented where appropriate.",
        "question": "Are premises continuously monitored for unauthorised physical access using surveillance and detection systems?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No physical security monitoring."},
            {"score": 1, "description": "Partial CCTV coverage with no active monitoring."},
            {"score": 2, "description": "CCTV and alarms in place but recordings not regularly reviewed."},
            {"score": 3, "description": "Comprehensive CCTV coverage, intrusion alarms, recordings retained per policy, and incidents investigated."},
            {"score": 4, "description": "AI-assisted video analytics, real-time alerting, integration with security operations centre."},
        ],
        "evidence": [
            {"text": "Physical monitoring and surveillance policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "CCTV coverage map and retention schedule", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },
    "ISO-7.5": {
        "title": "Protecting Against Physical and Environmental Threats",
        "guidance": "Protection against physical and environmental threats such as natural disasters, malicious attacks, and accidents shall be designed and implemented.",
        "question": "Are protections against physical and environmental threats (fire, flood, power failure) designed and implemented?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No environmental protection measures."},
            {"score": 1, "description": "Basic fire suppression only."},
            {"score": 2, "description": "Fire and flood protection but no comprehensive environmental risk assessment."},
            {"score": 3, "description": "Environmental risk assessment completed, fire suppression, UPS, climate control, and flood protection in place."},
            {"score": 4, "description": "Redundant environmental controls with automated failover, continuous monitoring, and regular disaster recovery testing."},
        ],
        "evidence": [
            {"text": "Environmental risk assessment for facilities", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Fire suppression and environmental control maintenance records", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── A.8 Technological Controls ──
    "ISO-8.1": {
        "title": "User Endpoint Devices",
        "guidance": "Information stored on, processed by, or accessible via user endpoint devices shall be protected. Policies and procedures for managing endpoint devices shall be established.",
        "question": "Are user endpoint devices protected with appropriate security controls and managed according to policy?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No endpoint device security controls."},
            {"score": 1, "description": "Basic antivirus only with no device management."},
            {"score": 2, "description": "Endpoint protection deployed but not centrally managed."},
            {"score": 3, "description": "Centrally managed endpoint protection with encryption, patch management, and remote wipe capability."},
            {"score": 4, "description": "EDR/XDR deployed with automated threat response, zero-trust endpoint posture assessment."},
        ],
        "evidence": [
            {"text": "Endpoint device management policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Endpoint management console compliance report", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-8.2": {
        "title": "Privileged Access Rights",
        "guidance": "The allocation and use of privileged access rights shall be restricted and managed. Privileged access shall be granted on a need-to-use basis and time-limited where possible.",
        "question": "Are privileged access rights restricted, managed, and reviewed on a regular basis?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No management of privileged access."},
            {"score": 1, "description": "Privileged accounts exist but no formal management."},
            {"score": 2, "description": "Privileged access managed but not regularly reviewed."},
            {"score": 3, "description": "Privileged access granted on need-to-use basis, separate admin accounts, reviewed quarterly, and logged."},
            {"score": 4, "description": "Privileged access management (PAM) solution with just-in-time access, session recording, and automated review."},
        ],
        "evidence": [
            {"text": "Privileged access management policy", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Privileged account inventory and quarterly review records", "age_label": "< 3 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-8.3": {
        "title": "Information Access Restriction",
        "guidance": "Access to information and other associated assets shall be restricted in accordance with the established topic-specific policy on access control.",
        "question": "Is access to information and systems restricted based on the principle of least privilege and business need?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No access restrictions in place."},
            {"score": 1, "description": "Some access controls but overly permissive."},
            {"score": 2, "description": "Role-based access defined but not consistently enforced."},
            {"score": 3, "description": "Role-based access control enforced, least privilege applied, access reviewed semi-annually."},
            {"score": 4, "description": "Attribute-based access control with automated provisioning, continuous access certification, and anomaly detection."},
        ],
        "evidence": [
            {"text": "Access control policy and role definitions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Access review records showing least privilege compliance", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-8.4": {
        "title": "Secure Development Life Cycle",
        "guidance": "Rules for the secure development of software and systems shall be established and applied. Security shall be integrated throughout the development life cycle.",
        "question": "Are secure development practices established and applied throughout the software development life cycle?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No secure development practices."},
            {"score": 1, "description": "Ad-hoc security reviews during development."},
            {"score": 2, "description": "Some secure coding guidelines but not consistently applied."},
            {"score": 3, "description": "Secure SDLC with threat modelling, code review, SAST/DAST testing, and security sign-off before release."},
            {"score": 4, "description": "DevSecOps pipeline with automated security testing, dependency scanning, and continuous security validation."},
        ],
        "evidence": [
            {"text": "Secure development life cycle policy and procedures", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of security testing in recent releases (SAST/DAST reports)", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "ISO-8.5": {
        "title": "Cloud Services Security",
        "guidance": "Processes for acquisition, use, management, and exit from cloud services shall be established in accordance with the organisation's information security requirements. Cloud service agreements shall address shared responsibilities.",
        "question": "Are cloud services managed securely with documented shared responsibility agreements and exit strategies?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No cloud security management."},
            {"score": 1, "description": "Cloud services used but no formal security management."},
            {"score": 2, "description": "Some cloud security controls but shared responsibility not documented."},
            {"score": 3, "description": "Cloud security policy defined, shared responsibility documented, exit strategy in place, and reviewed annually."},
            {"score": 4, "description": "Cloud security posture management with automated compliance monitoring, multi-cloud governance, and tested exit procedures."},
        ],
        "evidence": [
            {"text": "Cloud services security policy and shared responsibility matrix", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Cloud service inventory with risk assessments", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
            {"text": "Cloud exit strategy document", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
}

# ---------- Scoping Questions (5 per Req 4.3) ----------

SCOPING_QUESTIONS = [
    {
        "identifier": "iso-q1",
        "question_text": "Does the organisation use cloud services?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "iso-q2",
        "question_text": "Does the organisation allow remote working?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "iso-q3",
        "question_text": "Does the organisation develop software in-house?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
    {
        "identifier": "iso-q4",
        "question_text": "Does the organisation process personal data?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 3,
    },
    {
        "identifier": "iso-q5",
        "question_text": "Does the organisation operate physical data centres?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 4,
    },
]

# ---------- Scoping Rules (cloud and physical data centre per Req 4.4, 4.5) ----------

SCOPING_RULES = [
    # Cloud services (iso-q1 = Yes) → cloud security criteria applicable
    # Req 4.4: A.5.23 Cloud Services, cloud configuration, cloud access controls
    {
        "question_identifier": "iso-q1",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "ISO-8.5",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "iso-q1",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "ISO-5.5",
        "applicability_status": "applicable",
    },
    # Cloud services (iso-q1 = No) → cloud security criteria not applicable
    {
        "question_identifier": "iso-q1",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "ISO-8.5",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "iso-q1",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "ISO-5.5",
        "applicability_status": "not_applicable",
    },
    # Remote working (iso-q2 = Yes) → endpoint and access criteria applicable
    {
        "question_identifier": "iso-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "ISO-8.1",
        "applicability_status": "applicable",
    },
    # Remote working (iso-q2 = No) → endpoint criteria not applicable
    {
        "question_identifier": "iso-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "ISO-8.1",
        "applicability_status": "not_applicable",
    },
    # In-house software development (iso-q3 = Yes) → secure SDLC applicable
    {
        "question_identifier": "iso-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "ISO-8.4",
        "applicability_status": "applicable",
    },
    # In-house software development (iso-q3 = No) → secure SDLC not applicable
    {
        "question_identifier": "iso-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "ISO-8.4",
        "applicability_status": "not_applicable",
    },
    # Physical data centres (iso-q5 = Yes) → physical controls section applicable
    # Req 4.5: A.7.1–A.7.14 Physical Controls
    {
        "question_identifier": "iso-q5",
        "trigger_answer": "Yes",
        "target_type": "section",
        "target_code": "A.7 Physical Controls",
        "applicability_status": "applicable",
    },
    # Physical data centres (iso-q5 = No) → physical controls section not applicable
    {
        "question_identifier": "iso-q5",
        "trigger_answer": "No",
        "target_type": "section",
        "target_code": "A.7 Physical Controls",
        "applicability_status": "not_applicable",
    },
]
