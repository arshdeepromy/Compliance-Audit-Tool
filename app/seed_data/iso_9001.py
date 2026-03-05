"""ISO 9001:2015 — Quality Management System template seed data.

Contains 7 sections (clauses 4–10) with 3 criteria each (21 total),
3 scoping questions, and scoping rules for design/development,
outsourced processes, and monitoring/measuring equipment.
"""

TEMPLATE_NAME = "ISO 9001:2015 \u2014 Quality Management System"
TEMPLATE_VERSION = "1.0"

TEMPLATE_METADATA = {
    "domain_type": "Management Systems",
    "compliance_framework": "ISO 9001:2015",
}

# ---------- Sections (clauses 4–10) ----------

SECTIONS = [
    {
        "name": "Clause 4: Context of the Organisation",
        "codes": ["QMS-4.1", "QMS-4.2", "QMS-4.3"],
    },
    {
        "name": "Clause 5: Leadership",
        "codes": ["QMS-5.1", "QMS-5.2", "QMS-5.3"],
    },
    {
        "name": "Clause 6: Planning",
        "codes": ["QMS-6.1", "QMS-6.2", "QMS-6.3"],
    },
    {
        "name": "Clause 7: Support",
        "codes": ["QMS-7.1", "QMS-7.2", "QMS-7.3"],
    },
    {
        "name": "Clause 8: Operation",
        "codes": ["QMS-8.1", "QMS-8.2", "QMS-8.3"],
    },
    {
        "name": "Clause 9: Performance Evaluation",
        "codes": ["QMS-9.1", "QMS-9.2", "QMS-9.3"],
    },
    {
        "name": "Clause 10: Improvement",
        "codes": ["QMS-10.1", "QMS-10.2", "QMS-10.3"],
    },
]

# ---------- Criteria (3 per section, 21 total) ----------

CRITERIA = {
    # ── Clause 4: Context of the Organisation ──
    "QMS-4.1": {
        "title": "Understanding the Organisation and Its Context",
        "guidance": "The organisation shall determine external and internal issues that are relevant to its purpose and strategic direction and that affect its ability to achieve the intended results of its quality management system.",
        "question": "Has the organisation identified the external and internal issues relevant to its purpose and QMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identification of internal or external issues."},
            {"score": 1, "description": "Some issues informally recognised but not documented."},
            {"score": 2, "description": "Issues documented but not systematically reviewed or linked to QMS planning."},
            {"score": 3, "description": "Internal and external issues identified, documented, reviewed at planned intervals, and used as input to QMS planning."},
            {"score": 4, "description": "Comprehensive environmental scanning with SWOT/PESTLE analysis integrated into strategic and QMS planning cycles."},
        ],
        "evidence": [
            {"text": "Context analysis document (e.g. SWOT, PESTLE)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Management review minutes referencing context analysis", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-4.2": {
        "title": "Understanding the Needs and Expectations of Interested Parties",
        "guidance": "The organisation shall determine the interested parties relevant to the QMS and their requirements, and monitor and review this information.",
        "question": "Has the organisation identified relevant interested parties and their requirements?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No identification of interested parties."},
            {"score": 1, "description": "Key customers identified but other stakeholders not considered."},
            {"score": 2, "description": "Interested parties listed but their requirements not systematically captured."},
            {"score": 3, "description": "All relevant interested parties identified with documented requirements, monitored and reviewed regularly."},
            {"score": 4, "description": "Stakeholder engagement programme with feedback loops, satisfaction tracking, and proactive requirement anticipation."},
        ],
        "evidence": [
            {"text": "Interested parties register with requirements", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of stakeholder review and monitoring", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "QMS-4.3": {
        "title": "Determining the Scope of the QMS",
        "guidance": "The organisation shall determine the boundaries and applicability of the QMS to establish its scope, considering external and internal issues, interested party requirements, and products and services.",
        "question": "Is the scope of the QMS clearly defined, documented, and available?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined QMS scope."},
            {"score": 1, "description": "Scope exists informally but is not documented."},
            {"score": 2, "description": "Scope documented but does not reference context or interested party requirements."},
            {"score": 3, "description": "Scope clearly defined, documented, considers context and interested parties, and is available as documented information."},
            {"score": 4, "description": "Scope regularly reviewed against strategic changes, with clear justification for any exclusions and traceability to context analysis."},
        ],
        "evidence": [
            {"text": "QMS scope statement", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Quality manual or equivalent document referencing scope", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 5: Leadership ──
    "QMS-5.1": {
        "title": "Leadership and Commitment",
        "guidance": "Top management shall demonstrate leadership and commitment with respect to the QMS by taking accountability, ensuring quality policy and objectives are established, ensuring integration into business processes, and promoting the process approach and risk-based thinking.",
        "question": "Does top management demonstrate leadership and commitment to the QMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No visible management commitment to quality."},
            {"score": 1, "description": "Management aware of QMS but not actively involved."},
            {"score": 2, "description": "Management participates in reviews but does not drive quality culture."},
            {"score": 3, "description": "Top management actively leads QMS, takes accountability, promotes process approach, and ensures resources are available."},
            {"score": 4, "description": "Quality leadership embedded in corporate governance with management KPIs, visible sponsorship, and continuous improvement culture."},
        ],
        "evidence": [
            {"text": "Management review meeting minutes showing active leadership", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of resource allocation for QMS", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-5.2": {
        "title": "Quality Policy",
        "guidance": "Top management shall establish, implement, and maintain a quality policy that is appropriate to the purpose and context of the organisation, provides a framework for setting quality objectives, and includes a commitment to continual improvement.",
        "question": "Is a quality policy established, communicated, and understood within the organisation?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No quality policy exists."},
            {"score": 1, "description": "Quality policy exists but is outdated or not communicated."},
            {"score": 2, "description": "Policy documented and communicated but not well understood by staff."},
            {"score": 3, "description": "Quality policy appropriate to context, communicated to all personnel, understood, and reviewed at planned intervals."},
            {"score": 4, "description": "Policy integrated into onboarding, displayed prominently, regularly tested for staff understanding, and aligned with strategic objectives."},
        ],
        "evidence": [
            {"text": "Quality policy document signed by top management", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of policy communication (e.g. notice boards, intranet, training)", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-5.3": {
        "title": "Organisational Roles, Responsibilities and Authorities",
        "guidance": "Top management shall ensure that responsibilities and authorities for relevant roles are assigned, communicated, and understood within the organisation.",
        "question": "Are QMS roles, responsibilities, and authorities clearly assigned and communicated?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No defined QMS roles or responsibilities."},
            {"score": 1, "description": "Some roles informally assigned but not documented."},
            {"score": 2, "description": "Roles documented but not communicated to all relevant personnel."},
            {"score": 3, "description": "All QMS roles and responsibilities defined, documented, assigned to named individuals, and communicated."},
            {"score": 4, "description": "RACI matrix maintained with competency mapping, regular role reviews, and succession planning for key QMS positions."},
        ],
        "evidence": [
            {"text": "QMS roles and responsibilities matrix or organisation chart", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Job descriptions referencing QMS responsibilities", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── Clause 6: Planning ──
    "QMS-6.1": {
        "title": "Actions to Address Risks and Opportunities",
        "guidance": "When planning for the QMS, the organisation shall consider context issues and interested party requirements, and determine risks and opportunities that need to be addressed to give assurance the QMS can achieve its intended results, enhance desirable effects, prevent or reduce undesired effects, and achieve improvement.",
        "question": "Has the organisation identified and planned actions to address risks and opportunities affecting the QMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No risk or opportunity identification for the QMS."},
            {"score": 1, "description": "Some risks informally recognised but no structured approach."},
            {"score": 2, "description": "Risk register exists but actions are not planned or tracked."},
            {"score": 3, "description": "Risks and opportunities systematically identified, actions planned and integrated into QMS processes, and effectiveness evaluated."},
            {"score": 4, "description": "Enterprise risk management integrated with QMS, quantitative risk analysis, automated risk monitoring, and proactive opportunity exploitation."},
        ],
        "evidence": [
            {"text": "Risk and opportunity register with planned actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of risk action implementation and effectiveness review", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-6.2": {
        "title": "Quality Objectives and Planning to Achieve Them",
        "guidance": "The organisation shall establish quality objectives at relevant functions, levels, and processes. Objectives shall be consistent with the quality policy, measurable, monitored, communicated, and updated as appropriate.",
        "question": "Are measurable quality objectives established and monitored at relevant functions and levels?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No quality objectives established."},
            {"score": 1, "description": "Objectives exist but are vague or not measurable."},
            {"score": 2, "description": "Measurable objectives set but not consistently monitored or cascaded to all levels."},
            {"score": 3, "description": "SMART quality objectives established at relevant levels, monitored regularly, and achievement plans documented."},
            {"score": 4, "description": "Objectives cascaded through balanced scorecard, real-time dashboards, and automated performance tracking with trend analysis."},
        ],
        "evidence": [
            {"text": "Quality objectives document with targets and timelines", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Objective monitoring and performance reports", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-6.3": {
        "title": "Planning of Changes",
        "guidance": "When the organisation determines the need for changes to the QMS, the changes shall be carried out in a planned manner considering the purpose of the changes, potential consequences, resource availability, and allocation of responsibilities.",
        "question": "Are changes to the QMS planned and managed in a controlled manner?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No change management for the QMS."},
            {"score": 1, "description": "Changes made ad-hoc without planning."},
            {"score": 2, "description": "Some change planning but not consistently applied."},
            {"score": 3, "description": "All QMS changes planned with impact assessment, resource consideration, responsibility assignment, and documented approval."},
            {"score": 4, "description": "Formal change management process with impact analysis, stakeholder consultation, pilot testing, and post-implementation review."},
        ],
        "evidence": [
            {"text": "Change management procedure for QMS", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Records of recent QMS changes with planning documentation", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },

    # ── Clause 7: Support ──
    "QMS-7.1": {
        "title": "Resources",
        "guidance": "The organisation shall determine and provide the resources needed for the establishment, implementation, maintenance, and continual improvement of the QMS, including people, infrastructure, environment for operation, monitoring and measuring resources, and organisational knowledge.",
        "question": "Are adequate resources determined and provided for the QMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No resource planning for the QMS."},
            {"score": 1, "description": "Resources allocated reactively with frequent shortages."},
            {"score": 2, "description": "Resource planning exists but gaps in infrastructure or competency."},
            {"score": 3, "description": "Resources systematically determined and provided including people, infrastructure, environment, and monitoring equipment."},
            {"score": 4, "description": "Resource planning integrated with strategic budgeting, capacity modelling, and proactive investment in QMS capability."},
        ],
        "evidence": [
            {"text": "Resource plan or budget allocation for QMS activities", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Infrastructure and equipment maintenance records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-7.2": {
        "title": "Competence",
        "guidance": "The organisation shall determine the necessary competence of persons doing work that affects QMS performance, ensure they are competent on the basis of education, training, or experience, take actions to acquire competence where needed, and retain documented information as evidence.",
        "question": "Are personnel competent for their QMS roles based on education, training, or experience?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No competence requirements defined for QMS roles."},
            {"score": 1, "description": "Competence requirements exist for some roles only."},
            {"score": 2, "description": "Competence defined but training gaps not systematically addressed."},
            {"score": 3, "description": "Competence requirements defined for all QMS roles, training needs assessed, actions taken, and effectiveness evaluated."},
            {"score": 4, "description": "Competency framework with skills matrix, individual development plans, mentoring programmes, and competence verification."},
        ],
        "evidence": [
            {"text": "Competence requirements and training records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Training needs analysis and effectiveness evaluation", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-7.3": {
        "title": "Documented Information",
        "guidance": "The QMS shall include documented information required by ISO 9001 and determined by the organisation as necessary for QMS effectiveness. Documented information shall be controlled to ensure it is available, suitable, and adequately protected.",
        "question": "Is documented information controlled, available, and adequately protected?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No document control system."},
            {"score": 1, "description": "Some documents controlled but many are informal or uncontrolled."},
            {"score": 2, "description": "Document control exists but version management or access control is inconsistent."},
            {"score": 3, "description": "Documented information controlled with version management, approval workflow, distribution control, and retention policy."},
            {"score": 4, "description": "Electronic document management system with automated workflows, access controls, audit trails, and retention automation."},
        ],
        "evidence": [
            {"text": "Document control procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Master document list or document management system", "age_label": "Current", "age_class": "age-na", "required": True},
        ],
    },

    # ── Clause 8: Operation ──
    "QMS-8.1": {
        "title": "Operational Planning and Control",
        "guidance": "The organisation shall plan, implement, and control the processes needed to meet requirements for the provision of products and services, including establishing criteria for processes, implementing control of processes, and maintaining documented information.",
        "question": "Are operational processes planned, implemented, and controlled to meet product and service requirements?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No operational planning or process control."},
            {"score": 1, "description": "Some processes defined but not consistently controlled."},
            {"score": 2, "description": "Process controls exist but criteria are not clearly established or monitored."},
            {"score": 3, "description": "Operational processes planned with defined criteria, controlled outputs, and documented information maintained."},
            {"score": 4, "description": "Process management system with real-time monitoring, statistical process control, and automated deviation alerting."},
        ],
        "evidence": [
            {"text": "Process maps or procedures for key operational processes", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Process control records and monitoring data", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-8.2": {
        "title": "Design and Development of Products and Services",
        "guidance": "The organisation shall establish, implement, and maintain a design and development process that is appropriate to ensure the subsequent provision of products and services, including planning, inputs, controls, outputs, and changes.",
        "question": "Is a design and development process established with appropriate planning, reviews, and verification?",
        "na_allowed": True,
        "scoring": [
            {"score": 0, "description": "No design and development process."},
            {"score": 1, "description": "Design activities occur but without formal process."},
            {"score": 2, "description": "Design process exists but reviews and verification are inconsistent."},
            {"score": 3, "description": "Design and development process with defined stages, reviews, verification, validation, and change control."},
            {"score": 4, "description": "Stage-gate process with cross-functional reviews, design FMEA, simulation tools, and lessons-learned integration."},
        ],
        "evidence": [
            {"text": "Design and development procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Design review, verification, and validation records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-8.3": {
        "title": "Control of Externally Provided Processes, Products and Services",
        "guidance": "The organisation shall ensure that externally provided processes, products, and services conform to requirements. Controls shall be applied based on the potential impact on the organisation's ability to consistently deliver conforming products and services.",
        "question": "Are externally provided processes, products, and services controlled to ensure conformity?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No control of external providers."},
            {"score": 1, "description": "Some supplier checks but no formal evaluation process."},
            {"score": 2, "description": "Supplier evaluation exists but ongoing monitoring is limited."},
            {"score": 3, "description": "External providers evaluated, selected, monitored, and re-evaluated based on defined criteria with documented results."},
            {"score": 4, "description": "Supplier relationship management with scorecards, joint improvement programmes, and integrated supply chain quality monitoring."},
        ],
        "evidence": [
            {"text": "Approved supplier list with evaluation criteria", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Supplier evaluation and re-evaluation records", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 9: Performance Evaluation ──
    "QMS-9.1": {
        "title": "Monitoring, Measurement, Analysis and Evaluation",
        "guidance": "The organisation shall determine what needs to be monitored and measured, the methods for monitoring, measurement, analysis, and evaluation, when monitoring and measuring shall be performed, and when results shall be analysed and evaluated.",
        "question": "Are QMS processes monitored, measured, analysed, and evaluated at planned intervals?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No monitoring or measurement of QMS performance."},
            {"score": 1, "description": "Some metrics collected but not systematically analysed."},
            {"score": 2, "description": "Monitoring in place but analysis is infrequent or incomplete."},
            {"score": 3, "description": "Monitoring and measurement defined for key processes, data analysed at planned intervals, and results used for decision-making."},
            {"score": 4, "description": "Real-time dashboards with automated data collection, trend analysis, predictive analytics, and benchmarking."},
        ],
        "evidence": [
            {"text": "Monitoring and measurement plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Performance analysis reports and trend data", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-9.2": {
        "title": "Internal Audit",
        "guidance": "The organisation shall conduct internal audits at planned intervals to provide information on whether the QMS conforms to the organisation's own requirements and ISO 9001, and is effectively implemented and maintained.",
        "question": "Are internal audits conducted at planned intervals by competent auditors?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No internal audit programme."},
            {"score": 1, "description": "Audits conducted sporadically without a programme."},
            {"score": 2, "description": "Audit programme exists but coverage is incomplete or auditors lack independence."},
            {"score": 3, "description": "Internal audit programme with planned schedule, competent independent auditors, documented findings, and corrective actions tracked."},
            {"score": 4, "description": "Risk-based audit programme with continuous auditing techniques, automated finding tracking, and root cause trend analysis."},
        ],
        "evidence": [
            {"text": "Internal audit programme and schedule", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Internal audit reports with findings and corrective actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Auditor competence records", "age_label": "< 12 months", "age_class": "age-1y", "required": False},
        ],
    },
    "QMS-9.3": {
        "title": "Management Review",
        "guidance": "Top management shall review the QMS at planned intervals to ensure its continuing suitability, adequacy, effectiveness, and alignment with strategic direction. Review inputs shall include status of actions, changes in context, performance and effectiveness data, resource adequacy, and improvement opportunities.",
        "question": "Does top management review the QMS at planned intervals with appropriate inputs and outputs?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No management review of the QMS."},
            {"score": 1, "description": "Informal reviews without structured agenda or records."},
            {"score": 2, "description": "Reviews conducted but inputs are incomplete or outputs lack action items."},
            {"score": 3, "description": "Management reviews at planned intervals with all required inputs, documented outputs, and tracked action items."},
            {"score": 4, "description": "Strategic management reviews with data-driven insights, forward-looking analysis, and integration with business planning cycle."},
        ],
        "evidence": [
            {"text": "Management review meeting minutes with agenda and actions", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of action item completion from previous reviews", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },

    # ── Clause 10: Improvement ──
    "QMS-10.1": {
        "title": "Nonconformity and Corrective Action",
        "guidance": "When a nonconformity occurs, the organisation shall react to the nonconformity, evaluate the need for action to eliminate causes, implement any action needed, review the effectiveness of corrective action, and update risks and opportunities if necessary.",
        "question": "Are nonconformities managed with root cause analysis and effective corrective actions?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No nonconformity management process."},
            {"score": 1, "description": "Nonconformities addressed reactively without root cause analysis."},
            {"score": 2, "description": "Corrective actions taken but effectiveness not verified."},
            {"score": 3, "description": "Nonconformities documented, root cause analysis performed, corrective actions implemented, and effectiveness verified."},
            {"score": 4, "description": "Integrated CAPA system with automated escalation, trend analysis, preventive action triggers, and lessons-learned sharing."},
        ],
        "evidence": [
            {"text": "Nonconformity and corrective action procedure", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "CAPA log with root cause analysis and effectiveness verification", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-10.2": {
        "title": "Continual Improvement",
        "guidance": "The organisation shall continually improve the suitability, adequacy, and effectiveness of the QMS, considering the results of analysis and evaluation and the outputs from management review.",
        "question": "Does the organisation actively pursue continual improvement of the QMS?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No continual improvement activities."},
            {"score": 1, "description": "Improvement occurs reactively only in response to problems."},
            {"score": 2, "description": "Some improvement initiatives but not systematic or sustained."},
            {"score": 3, "description": "Continual improvement programme with defined methodology, improvement projects tracked, and results measured."},
            {"score": 4, "description": "Culture of excellence with Lean/Six Sigma programmes, innovation initiatives, benchmarking, and measurable improvement trends."},
        ],
        "evidence": [
            {"text": "Continual improvement programme or plan", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Evidence of completed improvement projects and results", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
        ],
    },
    "QMS-10.3": {
        "title": "Customer Satisfaction",
        "guidance": "The organisation shall monitor customers' perceptions of the degree to which their needs and expectations have been fulfilled. The organisation shall determine the methods for obtaining, monitoring, and reviewing this information.",
        "question": "Is customer satisfaction monitored and used as input for improvement?",
        "na_allowed": False,
        "scoring": [
            {"score": 0, "description": "No customer satisfaction monitoring."},
            {"score": 1, "description": "Informal feedback collected but not systematically analysed."},
            {"score": 2, "description": "Customer surveys conducted but results not acted upon consistently."},
            {"score": 3, "description": "Customer satisfaction systematically monitored through multiple channels, analysed, and used as input for improvement."},
            {"score": 4, "description": "Voice-of-customer programme with real-time feedback, NPS tracking, sentiment analysis, and closed-loop action management."},
        ],
        "evidence": [
            {"text": "Customer satisfaction survey results and analysis", "age_label": "< 12 months", "age_class": "age-1y", "required": True},
            {"text": "Customer complaint and feedback log with actions taken", "age_label": "< 6 months", "age_class": "age-1y", "required": True},
        ],
    },
}

# ---------- Scoping Questions (min 3) ----------

SCOPING_QUESTIONS = [
    {
        "identifier": "qms-q1",
        "question_text": "Does the organisation perform design and development of products or services?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 0,
    },
    {
        "identifier": "qms-q2",
        "question_text": "Does the organisation use outsourced processes that affect product or service conformity?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 1,
    },
    {
        "identifier": "qms-q3",
        "question_text": "Does the organisation use monitoring and measuring equipment requiring calibration?",
        "answer_type": "yes_no",
        "options": None,
        "sort_order": 2,
    },
]

# ---------- Scoping Rules ----------

SCOPING_RULES = [
    # Design and development (qms-q1 = Yes) → design criteria applicable
    {
        "question_identifier": "qms-q1",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "QMS-8.2",
        "applicability_status": "applicable",
    },
    # Design and development (qms-q1 = No) → design criteria not applicable
    {
        "question_identifier": "qms-q1",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "QMS-8.2",
        "applicability_status": "not_applicable",
    },
    # Outsourced processes (qms-q2 = Yes) → external provider control applicable
    {
        "question_identifier": "qms-q2",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "QMS-8.3",
        "applicability_status": "applicable",
    },
    # Outsourced processes (qms-q2 = No) → external provider control not applicable
    {
        "question_identifier": "qms-q2",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "QMS-8.3",
        "applicability_status": "not_applicable",
    },
    # Monitoring equipment (qms-q3 = Yes) → monitoring resources applicable
    {
        "question_identifier": "qms-q3",
        "trigger_answer": "Yes",
        "target_type": "criterion",
        "target_code": "QMS-9.1",
        "applicability_status": "applicable",
    },
    # Monitoring equipment (qms-q3 = No) → monitoring resources not applicable
    {
        "question_identifier": "qms-q3",
        "trigger_answer": "No",
        "target_type": "criterion",
        "target_code": "QMS-9.1",
        "applicability_status": "not_applicable",
    },
]
