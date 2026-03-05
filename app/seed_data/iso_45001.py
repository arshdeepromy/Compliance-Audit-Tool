"""ISO 45001:2018 — Occupational Health and Safety Management System template seed data.

Contains 7 sections (clauses 4–10) with 3 criteria each (21 total),
3 scoping questions, and scoping rules for hazardous work,
contractor management, and remote/lone working.
"""

TEMPLATE_NAME = "ISO 45001:2018 \u2014 Occupational Health and Safety Management System"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "Health & Safety",
    "compliance_framework": "ISO 45001:2018",
}

# ---------- Sections (clauses 4–10) ----------

SECTIONS = [
    {
        "name": "Clause 4: Context of the Organisation",
        "codes": ["OHS-4.1", "OHS-4.2", "OHS-4.3"],
    },
    {
        "name": "Clause 5: Leadership and Worker Participation",
        "codes": ["OHS-5.1", "OHS-5.2", "OHS-5.3"],
    },
    {
        "name": "Clause 6: Planning",
        "codes": ["OHS-6.1", "OHS-6.2", "OHS-6.3"],
    },
    {
        "name": "Clause 7: Support",
        "codes": ["OHS-7.1", "OHS-7.2", "OHS-7.3"],
    },
    {
        "name": "Clause 8: Operation",
        "codes": ["OHS-8.1", "OHS-8.2", "OHS-8.3"],
    },
    {
        "name": "Clause 9: Performance Evaluation",
        "codes": ["OHS-9.1", "OHS-9.2", "OHS-9.3"],
    },
    {
        "name": "Clause 10: Improvement",
        "codes": ["OHS-10.1", "OHS-10.2", "OHS-10.3"],
    },
]

# ---------- Criteria (3 per section, 21 total) ----------

CRITERIA = {
    # ── Clause 4: Context of the Organisation ──
    "OHS-4.1": {
        "title": "Understanding the Organisation and Its Context",
        "guidance": "The organisation shall determine external and internal issues relevant to its purpose that affect its ability to achieve the intended outcomes of its OH&S management system.",
        "question": "Has the organisation identified internal and external issues relevant to the OH&S management system?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identification of OH&S context issues."},
            {"score": 1, "description": "Some OH&S issues informally recognised but not documented."},
            {"score": 2, "description": "Issues documented but not linked to OH&S risks or OHSMS planning."},
            {"score": 3, "description": "Internal and external issues identified, documented, and used as input to OH&S planning including worker health and safety conditions."},
            {"score": 4, "description": "Comprehensive context analysis with industry benchmarking, psychosocial factors, and integration into strategic planning."},
        ],
        "evidence": [
            {"text": "OH&S context analysis document", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Management review minutes referencing OH&S context", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-4.2": {
        "title": "Understanding the Needs and Expectations of Workers and Other Interested Parties",
        "guidance": "The organisation shall determine workers and other interested parties relevant to the OHSMS, their needs and expectations, and which become legal and other requirements.",
        "question": "Has the organisation identified workers and interested parties, their OH&S needs, and resulting legal requirements?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identification of worker or interested party OH&S needs."},
            {"score": 1, "description": "Regulators identified but worker consultation not established."},
            {"score": 2, "description": "Interested parties listed but legal requirements not systematically derived."},
            {"score": 3, "description": "Workers and interested parties identified with documented needs, legal and other requirements determined and monitored."},
            {"score": 4, "description": "Proactive worker engagement programme with health surveillance, psychosocial risk assessment, and supply chain OH&S requirements."},
        ],
        "evidence": [
            {"text": "Interested parties register with OH&S requirements", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Legal and other requirements register for OH&S", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-4.3": {
        "title": "Determining the Scope of the OH&S Management System",
        "guidance": "The organisation shall determine the boundaries and applicability of the OHSMS considering external and internal issues, legal requirements, planned or performed work-related activities, and workers under its control.",
        "question": "Is the scope of the OHSMS clearly defined, documented, and available?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined OHSMS scope."},
            {"score": 1, "description": "Scope exists informally but is not documented."},
            {"score": 2, "description": "Scope documented but does not consider all workplaces, workers, or work-related activities."},
            {"score": 3, "description": "Scope clearly defined considering all workplaces, activities, workers under control, and work performed on behalf of the organisation."},
            {"score": 4, "description": "Scope regularly reviewed with multi-site coverage, contractor inclusion, and clear justification for boundaries."},
        ],
        "evidence": [
            {"text": "OHSMS scope statement", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "OH&S manual or equivalent referencing scope boundaries", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 5: Leadership and Worker Participation ──
    "OHS-5.1": {
        "title": "Leadership and Commitment",
        "guidance": "Top management shall demonstrate leadership and commitment by taking overall responsibility and accountability for prevention of work-related injury and ill health, ensuring the OH&S policy and objectives are established, and ensuring worker participation and consultation.",
        "question": "Does top management demonstrate leadership and commitment to OH&S including prevention of injury and ill health?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No visible management commitment to OH&S."},
            {"score": 1, "description": "Management aware of OH&S obligations but not actively involved."},
            {"score": 2, "description": "Management participates in reviews but does not drive OH&S culture."},
            {"score": 3, "description": "Top management actively leads OH&S, takes accountability, ensures resources, promotes worker participation, and drives continual improvement."},
            {"score": 4, "description": "OH&S leadership embedded in corporate governance with safety KPIs, board-level reporting, visible executive sponsorship, and safety culture programme."},
        ],
        "evidence": [
            {"text": "Management review minutes showing active OH&S leadership", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of resource allocation for OH&S initiatives", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-5.2": {
        "title": "OH&S Policy",
        "guidance": "Top management shall establish an OH&S policy that includes commitments to provide safe and healthy working conditions, elimination of hazards and reduction of OH&S risks, consultation and participation of workers, and continual improvement.",
        "question": "Is an OH&S policy established that includes commitments to safe conditions, hazard elimination, worker participation, and continual improvement?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No OH&S policy exists."},
            {"score": 1, "description": "OH&S policy exists but is outdated or lacks required commitments."},
            {"score": 2, "description": "Policy documented with commitments but not communicated to all workers."},
            {"score": 3, "description": "OH&S policy appropriate to context, includes all required commitments, communicated to workers, and available to interested parties."},
            {"score": 4, "description": "Policy integrated into corporate values, regularly tested for understanding, aligned with Vision Zero or equivalent, and publicly available."},
        ],
        "evidence": [
            {"text": "OH&S policy document signed by top management", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of policy communication to workers and availability to interested parties", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-5.3": {
        "title": "Worker Participation and Consultation",
        "guidance": "The organisation shall establish processes for consultation and participation of workers at all applicable levels and functions, including non-managerial workers, in the development, planning, implementation, performance evaluation, and actions for improvement of the OHSMS.",
        "question": "Are workers consulted and do they participate in OHSMS development, implementation, and improvement?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No worker consultation or participation mechanisms."},
            {"score": 1, "description": "Ad-hoc consultation only, no formal mechanisms."},
            {"score": 2, "description": "Health and safety committee exists but non-managerial worker participation is limited."},
            {"score": 3, "description": "Formal consultation and participation processes for all workers including non-managerial, with mechanisms for hazard reporting, incident investigation input, and OH&S decision-making."},
            {"score": 4, "description": "Empowered safety culture with worker-led safety teams, stop-work authority, behavioural safety observations, and worker representation in all OH&S decisions."},
        ],
        "evidence": [
            {"text": "Worker consultation and participation procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Health and safety committee minutes or worker consultation records", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 6: Planning ──
    "OHS-6.1": {
        "title": "Hazard Identification and Assessment of Risks and Opportunities",
        "guidance": "The organisation shall establish processes for ongoing and proactive hazard identification considering how work is organised, social factors, routine and non-routine activities, past incidents, and potential emergency situations. OH&S risks shall be assessed and opportunities identified.",
        "question": "Are hazard identification and risk assessment processes established, proactive, and ongoing?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No hazard identification or risk assessment process."},
            {"score": 1, "description": "Hazard identification reactive only, triggered by incidents."},
            {"score": 2, "description": "Risk assessments conducted but not proactive or not covering all work activities and non-routine situations."},
            {"score": 3, "description": "Proactive hazard identification covering all activities, risk assessments using hierarchy of controls, opportunities identified, and results used in planning."},
            {"score": 4, "description": "Advanced risk management with predictive analytics, leading indicators, psychosocial risk assessment, and integration with business risk management."},
        ],
        "evidence": [
            {"text": "Hazard identification and risk assessment procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Risk register with current assessments", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-6.2": {
        "title": "OH&S Objectives and Planning to Achieve Them",
        "guidance": "The organisation shall establish OH&S objectives at relevant functions and levels that are consistent with the OH&S policy, measurable, monitored, communicated, and updated as appropriate.",
        "question": "Are measurable OH&S objectives established at relevant levels with plans to achieve them?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No OH&S objectives set."},
            {"score": 1, "description": "Objectives exist but are vague or not measurable."},
            {"score": 2, "description": "Measurable objectives set but not consistently monitored or linked to significant risks."},
            {"score": 3, "description": "SMART OH&S objectives established at relevant levels, linked to significant risks, monitored regularly, with achievement plans and resources."},
            {"score": 4, "description": "Leading and lagging indicator targets with real-time dashboards, automated tracking, and alignment with industry best practice benchmarks."},
        ],
        "evidence": [
            {"text": "OH&S objectives document with targets and timelines", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Objective monitoring and OH&S performance reports", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-6.3": {
        "title": "Determination of Legal and Other Requirements",
        "guidance": "The organisation shall determine and have access to legal and other requirements applicable to its hazards and OH&S risks, determine how they apply, and take them into account in establishing and maintaining the OHSMS.",
        "question": "Are applicable legal and other OH&S requirements identified, accessible, and integrated into the OHSMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identification of legal OH&S requirements."},
            {"score": 1, "description": "Key legislation known but no systematic register."},
            {"score": 2, "description": "Legal register exists but not regularly updated or compliance not evaluated."},
            {"score": 3, "description": "Comprehensive legal register maintained, regularly updated, compliance evaluated at planned intervals, and results communicated."},
            {"score": 4, "description": "Automated legal update service, compliance management system, proactive engagement with regulators, and legal compliance audits."},
        ],
        "evidence": [
            {"text": "Legal and other requirements register for OH&S", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Compliance evaluation records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 7: Support ──
    "OHS-7.1": {
        "title": "Competence, Training and Awareness",
        "guidance": "The organisation shall determine necessary competence of workers that affects OH&S performance, ensure workers are competent on the basis of education, training, or experience, and ensure workers are aware of the OH&S policy, hazards, and their contribution to OHSMS effectiveness.",
        "question": "Are workers competent for their OH&S roles and aware of hazards, risks, and their responsibilities?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No OH&S competence requirements or awareness programme."},
            {"score": 1, "description": "Basic safety induction only, no ongoing training."},
            {"score": 2, "description": "Training provided but not linked to specific hazards or job roles."},
            {"score": 3, "description": "Competence requirements defined for all roles, training needs assessed, awareness programme covers policy, hazards, risks, and emergency procedures."},
            {"score": 4, "description": "OH&S competency framework with skills matrix, behavioural safety training, effectiveness evaluation, and safety champions programme."},
        ],
        "evidence": [
            {"text": "OH&S training records and competence requirements", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Safety awareness programme materials and attendance records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-7.2": {
        "title": "Communication",
        "guidance": "The organisation shall establish processes for internal and external communications relevant to the OHSMS, including what, when, with whom, and how to communicate, ensuring worker views are taken into account.",
        "question": "Are internal and external OH&S communication processes established with worker input?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No OH&S communication processes."},
            {"score": 1, "description": "Ad-hoc safety communication only."},
            {"score": 2, "description": "Some communication processes but worker feedback mechanisms not established."},
            {"score": 3, "description": "Internal and external communication processes defined, worker views taken into account, safety alerts and bulletins distributed, and feedback mechanisms in place."},
            {"score": 4, "description": "Integrated safety communication strategy with toolbox talks, safety moments, digital reporting tools, and transparent incident communication."},
        ],
        "evidence": [
            {"text": "OH&S communication procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Records of safety communications and worker feedback", "age_label": "< 6 months", "age_class": "age-1y", "required": False},
        ],
    },
    "OHS-7.3": {
        "title": "Documented Information",
        "guidance": "The OHSMS shall include documented information required by ISO 45001 and determined by the organisation as necessary for effectiveness. Documented information shall be controlled to ensure availability, suitability, and adequate protection.",
        "question": "Is OHSMS documented information controlled, available, and adequately protected?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No document control for OH&S records."},
            {"score": 1, "description": "Some documents controlled but many OH&S records are informal."},
            {"score": 2, "description": "Document control exists but version management or retention of OH&S records is inconsistent."},
            {"score": 3, "description": "Documented information controlled with version management, approval workflow, distribution control, and retention policy for all OHSMS records."},
            {"score": 4, "description": "Electronic document management system with automated workflows, OH&S data integration, audit trails, and retention automation."},
        ],
        "evidence": [
            {"text": "Document control procedure for OHSMS", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Master document list or document management system for OH&S records", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },

    # ── Clause 8: Operation ──
    "OHS-8.1": {
        "title": "Operational Planning and Control",
        "guidance": "The organisation shall plan, implement, control, and maintain processes needed to meet OHSMS requirements using the hierarchy of controls: elimination, substitution, engineering controls, administrative controls, and PPE.",
        "question": "Are operational controls established using the hierarchy of controls for identified OH&S risks?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No operational controls for OH&S risks."},
            {"score": 1, "description": "Controls rely primarily on PPE and worker behaviour."},
            {"score": 2, "description": "Some engineering and administrative controls but hierarchy of controls not systematically applied."},
            {"score": 3, "description": "Operational controls established using hierarchy of controls, safe work procedures documented, and controls verified for effectiveness."},
            {"score": 4, "description": "Integrated safety-in-design approach with elimination prioritised, engineering controls automated, and continuous control effectiveness monitoring."},
        ],
        "evidence": [
            {"text": "Safe work procedures and operational control documents", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of hierarchy of controls application in risk assessments", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-8.2": {
        "title": "Emergency Preparedness and Response",
        "guidance": "The organisation shall establish, implement, and maintain processes to prepare for and respond to potential emergency situations including provision of first aid, training, and periodic testing of planned response.",
        "question": "Are emergency preparedness and response procedures established, tested, and reviewed?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No emergency preparedness for OH&S emergencies."},
            {"score": 1, "description": "Basic emergency contacts and evacuation plan only."},
            {"score": 2, "description": "Emergency procedures exist but not regularly tested or first aid provisions inadequate."},
            {"score": 3, "description": "Emergency procedures established for all potential OH&S emergencies, first aid provisions adequate, drills conducted periodically, and procedures reviewed after incidents."},
            {"score": 4, "description": "Comprehensive emergency management with scenario-based exercises, mutual aid agreements, trauma response capability, and post-incident psychological support."},
        ],
        "evidence": [
            {"text": "Emergency response plan covering OH&S emergencies", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Emergency drill records and post-drill review reports", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-8.3": {
        "title": "Management of Contractors and Outsourced Processes",
        "guidance": "The organisation shall ensure that outsourced processes and contractor activities are controlled, that OH&S requirements are communicated to contractors, and that contractor OH&S performance is monitored.",
        "question": "Are contractor OH&S requirements defined, communicated, and monitored?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No contractor OH&S management."},
            {"score": 1, "description": "Basic contractor induction but no ongoing monitoring."},
            {"score": 2, "description": "Contractor requirements defined but monitoring and performance evaluation inconsistent."},
            {"score": 3, "description": "Contractor OH&S requirements defined, pre-qualification process in place, site induction provided, and contractor performance monitored and reviewed."},
            {"score": 4, "description": "Integrated contractor management system with pre-qualification scoring, real-time permit-to-work, joint safety inspections, and performance-based contracts."},
        ],
        "evidence": [
            {"text": "Contractor OH&S management procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Contractor pre-qualification records and performance reviews", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 9: Performance Evaluation ──
    "OHS-9.1": {
        "title": "Monitoring, Measurement, Analysis and Evaluation",
        "guidance": "The organisation shall monitor, measure, analyse, and evaluate OH&S performance including the extent to which legal requirements are fulfilled, activities and operations related to identified hazards and risks, and progress toward OH&S objectives.",
        "question": "Is OH&S performance monitored, measured, and evaluated including compliance evaluation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No OH&S monitoring or measurement."},
            {"score": 1, "description": "Incident data collected but not systematically analysed."},
            {"score": 2, "description": "Monitoring in place for lagging indicators but leading indicators and compliance evaluation not formalised."},
            {"score": 3, "description": "OH&S performance monitored with leading and lagging indicators, compliance evaluated at planned intervals, and results used for improvement decisions."},
            {"score": 4, "description": "Real-time safety monitoring with IoT sensors, predictive analytics, automated compliance tracking, and industry benchmarking."},
        ],
        "evidence": [
            {"text": "OH&S monitoring and measurement plan with KPIs", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Compliance evaluation records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-9.2": {
        "title": "Internal Audit",
        "guidance": "The organisation shall conduct internal audits at planned intervals to provide information on whether the OHSMS conforms to the organisation's own requirements and ISO 45001, and is effectively implemented and maintained.",
        "question": "Are internal OH&S audits conducted at planned intervals by competent auditors?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No internal OH&S audit programme."},
            {"score": 1, "description": "Audits conducted sporadically without a programme."},
            {"score": 2, "description": "Audit programme exists but coverage is incomplete or auditors lack OH&S competence."},
            {"score": 3, "description": "Internal audit programme with planned schedule, competent independent auditors, documented findings, and corrective actions tracked."},
            {"score": 4, "description": "Risk-based audit programme with OH&S specialist auditors, behavioural safety audits, continuous auditing techniques, and trend analysis."},
        ],
        "evidence": [
            {"text": "Internal OH&S audit programme and schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Internal audit reports with findings and corrective actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-9.3": {
        "title": "Management Review",
        "guidance": "Top management shall review the OHSMS at planned intervals to ensure its continuing suitability, adequacy, and effectiveness, with inputs including OH&S performance, worker consultation results, and incident trends.",
        "question": "Does top management review the OHSMS at planned intervals with appropriate OH&S inputs and outputs?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No management review of the OHSMS."},
            {"score": 1, "description": "Informal reviews without structured agenda or records."},
            {"score": 2, "description": "Reviews conducted but OH&S performance data or incident trends not included."},
            {"score": 3, "description": "Management reviews at planned intervals with all required inputs including OH&S performance, incident data, worker consultation results, and documented outputs."},
            {"score": 4, "description": "Strategic OH&S reviews with data-driven insights, predictive safety analysis, worker representation, and integration with corporate strategy."},
        ],
        "evidence": [
            {"text": "Management review meeting minutes with OH&S agenda and actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of action item completion from previous reviews", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 10: Improvement ──
    "OHS-10.1": {
        "title": "Incident Investigation and Nonconformity",
        "guidance": "The organisation shall establish processes to report, investigate, and take action on incidents and nonconformities. Investigation shall identify underlying causes, determine corrective actions using the hierarchy of controls, and review effectiveness.",
        "question": "Are incidents investigated with root cause analysis and corrective actions using the hierarchy of controls?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No incident investigation process."},
            {"score": 1, "description": "Incidents recorded but not investigated for root causes."},
            {"score": 2, "description": "Investigation conducted but root cause analysis superficial or hierarchy of controls not applied to corrective actions."},
            {"score": 3, "description": "Incidents and nonconformities investigated with root cause analysis, corrective actions using hierarchy of controls, effectiveness verified, and lessons shared."},
            {"score": 4, "description": "Advanced investigation methodology with human factors analysis, systemic cause identification, predictive incident modelling, and organisation-wide learning."},
        ],
        "evidence": [
            {"text": "Incident investigation procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Incident investigation reports with root cause analysis and corrective actions", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-10.2": {
        "title": "Continual Improvement",
        "guidance": "The organisation shall continually improve the suitability, adequacy, and effectiveness of the OHSMS by enhancing OH&S performance, promoting a culture that supports the OHSMS, and promoting worker participation.",
        "question": "Does the organisation actively pursue continual improvement of OH&S performance and the OHSMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No continual improvement activities for OH&S."},
            {"score": 1, "description": "Improvement occurs reactively only in response to incidents."},
            {"score": 2, "description": "Some improvement initiatives but not systematic or linked to OH&S performance data."},
            {"score": 3, "description": "Continual improvement programme with defined methodology, projects linked to OH&S objectives, worker involvement, and results measured."},
            {"score": 4, "description": "Culture of safety excellence with innovation programmes, behavioural safety initiatives, benchmarking, and measurable improvement trends."},
        ],
        "evidence": [
            {"text": "OH&S improvement programme or plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of completed OH&S improvement projects and results", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "OHS-10.3": {
        "title": "Hazardous Work and High-Risk Activities",
        "guidance": "The organisation shall establish specific controls for hazardous work activities including permit-to-work systems, lockout/tagout, confined space entry, working at height, and hot work, ensuring workers are trained and authorised.",
        "question": "Are specific controls established for hazardous work activities with permit-to-work systems where required?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No specific controls for hazardous work activities."},
            {"score": 1, "description": "Some awareness of hazardous work but no formal permit systems."},
            {"score": 2, "description": "Permit-to-work exists for some activities but not all high-risk work covered."},
            {"score": 3, "description": "Comprehensive permit-to-work system covering all hazardous activities, workers trained and authorised, and controls verified before work commences."},
            {"score": 4, "description": "Digital permit-to-work system with real-time monitoring, automated isolation verification, competency-linked authorisation, and continuous risk reassessment."},
        ],
        "evidence": [
            {"text": "Permit-to-work procedures for hazardous activities", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Completed permit-to-work records and worker authorisation registers", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
}

SCOPING_QUESTIONS = [
    {
        "identifier": "ohs-q1",
        "question_text": "Does the organisation perform hazardous work activities (e.g. confined spaces, working at height, hot work)?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "ohs-q2",
        "question_text": "Does the organisation engage contractors or outsourced workers on site?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "ohs-q3",
        "question_text": "Does the organisation have remote or lone workers?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
]

SCOPING_RULES = [
    {
        "question_identifier": "ohs-q1",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "OHS-10.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "ohs-q1",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "OHS-10.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "ohs-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "OHS-8.3",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "ohs-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "OHS-8.3",
        "applicability_status": "not_applicable",
    },
    {
        "question_identifier": "ohs-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "OHS-7.2",
        "applicability_status": "applicable",
    },
    {
        "question_identifier": "ohs-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "OHS-7.2",
        "applicability_status": "not_applicable",
    },
]
