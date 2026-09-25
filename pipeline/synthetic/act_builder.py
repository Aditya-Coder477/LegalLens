"""
pipeline/synthetic/act_builder.py
=================================
Generates 25+ realistic, structured synthetic Indian Acts (15–40 sections each).
Includes multi-version evolution for versioning evaluation.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from pipeline.core.metadata import DocumentType, LegalDomain, SourceAuthority, DocumentStatus
from pipeline.versioning.version_tracker import generate_version_group_id

# Definition of the 25 base synthetic Acts
ACT_DEFINITIONS = [
    {
        "id": "SYN-ACT-001",
        "title": "Digital Services Accountability Act, 2025 (Synthetic)",
        "year": 2025,
        "act_num": "4",
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "secondary": [LegalDomain.DATA_PROTECTION_PRIVACY.value, LegalDomain.CONSUMER_LAW.value],
        "authority": "Digital Services Regulatory Authority of Bharat (Synthetic)",
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to establish mandatory accountability, algorithmic transparency, and consumer safety standards for digital platforms and automated intermediary services in Bharat.",
        "topics": ["intermediary due diligence", "content moderation appeal", "dark patterns prohibition", "algorithmic audit"],
    },
    {
        "id": "SYN-ACT-002",
        "title": "Renewable Energy Grid Integration and Open Access Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "18",
        "domain": LegalDomain.ELECTRICITY_ENERGY.value,
        "secondary": [LegalDomain.ENVIRONMENTAL_LAW.value, LegalDomain.COMMERCIAL_CORPORATE.value],
        "authority": "National Clean Energy Grid Council (Synthetic)",
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to accelerate the integration of utility-scale renewable energy, battery storage systems, and non-discriminatory open access transmission.",
        "topics": ["renewable purchase obligation", "wheeling charges exemption", "grid reliability standards", "smart metering mandate"],
    },
    {
        "id": "SYN-ACT-003",
        "title": "Consumer Credit Transparency and Fair Lending Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "12",
        "domain": LegalDomain.BANKING_FINANCIAL.value,
        "secondary": [LegalDomain.CONSUMER_LAW.value, LegalDomain.CONTRACT_LAW.value],
        "authority": "National Fair Lending and Credit Commission (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to prevent predatory lending practices, enforce key fact statement disclosures, and regulate digital recovery agent conduct.",
        "topics": ["key fact statement", "cooling off period", "recovery agent licensing", "interest cap on microloans"],
    },
    {
        "id": "SYN-ACT-004",
        "title": "Medical Devices Quality and Traceability Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "22",
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "secondary": [LegalDomain.PHARMACEUTICAL.value, LegalDomain.CONSUMER_LAW.value],
        "authority": "Medical Devices Quality and Traceability Board (Synthetic)",
        "ministry": "Ministry of Health Technologies and Biosecurity (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to provide uniform quality standards, unique device identification, and recall mechanisms for medical implants and diagnostics.",
        "topics": ["unique device identification", "clinical investigation permit", "adverse event reporting", "mandatory product recall"],
    },
    {
        "id": "SYN-ACT-005",
        "title": "Artificial Intelligence System Safety and Risk Governance Act, 2025 (Synthetic)",
        "year": 2025,
        "act_num": "7",
        "domain": LegalDomain.EMERGING_TECHNOLOGY_AI.value,
        "secondary": [LegalDomain.IT_CYBER_LAW.value, LegalDomain.HUMAN_RIGHTS.value],
        "authority": "Digital Services Regulatory Authority of Bharat (Synthetic)",
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to categorize artificial intelligence models by risk tier, mandate model safety assessments, and protect citizens against biased automated decision-making.",
        "topics": ["high risk AI registration", "bias testing audit", "synthetic media watermarking", "whistleblower protection"],
    },
    {
        "id": "SYN-ACT-006",
        "title": "Workplace Safety and Remote Employee Welfare Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "15",
        "domain": LegalDomain.EMPLOYMENT_LABOUR.value,
        "secondary": [LegalDomain.CONTRACT_LAW.value, LegalDomain.HEALTH_MEDICAL.value],
        "authority": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to establish ergonomic safety guidelines, the right to disconnect after working hours, and mental health assistance for hybrid and remote workers.",
        "topics": ["right to disconnect", "workstation ergonomic subsidy", "remote overtime calculation", "internal complaints committee"],
    },
    {
        "id": "SYN-ACT-007",
        "title": "Urban Ground Water Conservation and Recharge Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "9",
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "secondary": [LegalDomain.PROPERTY_REAL_ESTATE.value, LegalDomain.ADMINISTRATIVE_LAW.value],
        "authority": "Environmental Redressal Tribunal of Dakshin Pradesh (Synthetic)",
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "jurisdiction": "State of Dakshin Pradesh (Synthetic)",
        "preamble": "An Act to mandate rainwater harvesting in commercial establishments, regulate deep borehole drilling, and protect aquifer replenishment zones.",
        "topics": ["rainwater harvesting mandate", "groundwater extraction cess", "borewell registration", "aquifer protection zoning"],
    },
    {
        "id": "SYN-ACT-008",
        "title": "Commercial Mediation and Fast-Track Arbitration Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "29",
        "domain": LegalDomain.ARBITRATION_ADR.value,
        "secondary": [LegalDomain.COMMERCIAL_CORPORATE.value, LegalDomain.CIVIL_PROCEDURE.value],
        "authority": "National Commercial Appellate Tribunal of Bharat (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to foster pre-litigation commercial mediation, establish institutional fast-track arbitral tribunals, and limit frivolous court interventions.",
        "topics": ["pre litigation mediation mandate", "six month fast track award", "mediator accreditation", "interim relief by tribunal"],
    },
    {
        "id": "SYN-ACT-009",
        "title": "Cross-Border E-Commerce Consumer Redressal Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "14",
        "domain": LegalDomain.CONSUMER_LAW.value,
        "secondary": [LegalDomain.IT_CYBER_LAW.value, LegalDomain.CONTRACT_LAW.value],
        "authority": "Consumer Protection and Redressal Council (Synthetic)",
        "ministry": "Department of Consumer Empowerment (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to safeguard consumers purchasing goods from overseas digital marketplaces, enforce warranty claims, and simplify dispute filing.",
        "topics": ["mandatory local nodal officer", "foreign seller liability", "currency conversion disclosure", "chargeback protection mechanism"],
    },
    {
        "id": "SYN-ACT-010",
        "title": "Micro-Enterprise Insolvency Resolution Framework Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "31",
        "domain": LegalDomain.INSOLVENCY_BANKRUPTCY.value,
        "secondary": [LegalDomain.COMMERCIAL_CORPORATE.value, LegalDomain.BANKING_FINANCIAL.value],
        "authority": "National Commercial Appellate Tribunal of Bharat (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to provide a debtor-in-possession pre-packaged insolvency resolution framework for micro, small, and medium commercial enterprises.",
        "topics": ["pre packaged resolution plan", "creditor consent threshold", "moratorium on asset recovery", "debtor in possession management"],
    },
    {
        "id": "SYN-ACT-011",
        "title": "Biometric Privacy and Citizen Data Rights Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "11",
        "domain": LegalDomain.DATA_PROTECTION_PRIVACY.value,
        "secondary": [LegalDomain.HUMAN_RIGHTS.value, LegalDomain.CONSTITUTIONAL_LAW.value],
        "authority": "Digital Services Regulatory Authority of Bharat (Synthetic)",
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to prohibit non-consensual facial recognition scanning in public spaces and secure citizen biometric templates from surveillance.",
        "topics": ["prohibition of biometric scraping", "right to erasure of iris data", "statutory data breach notice", "criminal penalty for identity theft"],
    },
    {
        "id": "SYN-ACT-012",
        "title": "Civil Cyber Liability and Digital Harassment Redressal Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "19",
        "domain": LegalDomain.CRIMINAL_LAW.value,
        "secondary": [LegalDomain.IT_CYBER_LAW.value, LegalDomain.CIVIL_PROCEDURE.value],
        "authority": "Central Cybersecurity Emergency Coordination Cell (Synthetic)",
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to provide swift civil compensation and injunctive orders against online harassment, deepfake defamation, and non-consensual image distribution.",
        "topics": ["twenty four hour takedown order", "statutory compensation ceiling", "fictional forensic verification", "interim civil restraining order"],
    },
    {
        "id": "SYN-ACT-013",
        "title": "Public Procurement Transparency and Integrity Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "5",
        "domain": LegalDomain.ADMINISTRATIVE_LAW.value,
        "secondary": [LegalDomain.COMMERCIAL_CORPORATE.value, LegalDomain.PUBLIC_PROCUREMENT.value],
        "authority": "Ministry of Commerce and Fair Competition (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to mandate open electronic bidding, ban collusive tender ring practices, and guarantee prompt payment to public works vendors.",
        "topics": ["electronic tender portal", "mandatory reverse bidding", "vendor debarment protocol", "statutory late payment interest"],
    },
    {
        "id": "SYN-ACT-014",
        "title": "Electric Vehicle Charging Infrastructure and Battery Swapping Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "27",
        "domain": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
        "secondary": [LegalDomain.ELECTRICITY_ENERGY.value, LegalDomain.ENVIRONMENTAL_LAW.value],
        "authority": "National Electronic Toll and Highway Safety Directorate (Synthetic)",
        "ministry": "Ministry of Urban Infrastructure and Transport (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to standardize battery swapping connectors, provide open access tariffs for charging hubs, and ensure safety in high-voltage charging.",
        "topics": ["interoperable charging plug", "battery thermal runaway standards", "subsidized commercial tariff", "highway spacing mandate"],
    },
    {
        "id": "SYN-ACT-015",
        "title": "Telecommunications Tower Radiation and Spectrum Leasing Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "8",
        "domain": LegalDomain.TELECOMMUNICATIONS.value,
        "secondary": [LegalDomain.ENVIRONMENTAL_LAW.value, LegalDomain.ADMINISTRATIVE_LAW.value],
        "authority": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to regulate non-ionizing electromagnetic radiation emissions from cellular base stations and facilitate private network spectrum leasing.",
        "topics": ["electromagnetic emission limits", "annual radiation audit", "private spectrum sub lease", "municipal right of way dispute"],
    },
    {
        "id": "SYN-ACT-016",
        "title": "University Innovation and Academic Patent Licensing Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "16",
        "domain": LegalDomain.INTELLECTUAL_PROPERTY.value,
        "secondary": [LegalDomain.EDUCATION_LAW.value, LegalDomain.COMMERCIAL_CORPORATE.value],
        "authority": "Ministry of Commerce and Fair Competition (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to grant universities ownership of publicly funded research inventions and streamline royalty sharing with faculty inventors.",
        "topics": ["faculty inventor royalty share", "university technology transfer office", "march in licensing rights", "open access publication waiver"],
    },
    {
        "id": "SYN-ACT-017",
        "title": "Fair Agricultural Contracting and Farmer Price Assurance Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "21",
        "domain": LegalDomain.AGRICULTURAL_LAW.value,
        "secondary": [LegalDomain.CONTRACT_LAW.value, LegalDomain.ARBITRATION_ADR.value],
        "authority": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "jurisdiction": "State of Paschim Rashtra (Synthetic)",
        "preamble": "An Act to mandate written farming contracts, guarantee floor purchase prices, and prohibit land alienation for debt recovery.",
        "topics": ["prohibition of land mortgage for seed", "minimum floor price guarantee", "sub divisional dispute board", "mandatory crop insurance escrow"],
    },
    {
        "id": "SYN-ACT-018",
        "title": "Fair Market Competition and Digital Dominance Monitoring Act, 2025 (Synthetic)",
        "year": 2025,
        "act_num": "2",
        "domain": LegalDomain.COMPETITION_LAW.value,
        "secondary": [LegalDomain.COMMERCIAL_CORPORATE.value, LegalDomain.IT_CYBER_LAW.value],
        "authority": "National Fair Lending and Credit Commission (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to prevent self-preferencing by systemically important digital gatekeepers, ensure app store interoperability, and review digital mergers.",
        "topics": ["gatekeeper designation criteria", "anti self preferencing clause", "third party billing choice", "pre merger notification threshold"],
    },
    {
        "id": "SYN-ACT-019",
        "title": "Senior Citizens Health Care and Assisted Living Standards Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "33",
        "domain": LegalDomain.SENIOR_CITIZEN.value,
        "secondary": [LegalDomain.HEALTH_MEDICAL.value, LegalDomain.HUMAN_RIGHTS.value],
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "jurisdiction": "State of Dakshin Pradesh (Synthetic)",
        "preamble": "An Act to establish licensing norms for elder care homes, prevent abandonment, and provide free geriatric telehealth services.",
        "topics": ["assisted living home licensing", "mandatory caregiver nurse ratio", "district maintenance tribunal", "emergency geriatric ambulance fund"],
    },
    {
        "id": "SYN-ACT-020",
        "title": "Transboundary River Basin Management and Pollution Control Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "25",
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "secondary": [LegalDomain.CONSTITUTIONAL_LAW.value, LegalDomain.ADMINISTRATIVE_LAW.value],
        "authority": "Environmental Redressal Tribunal of Dakshin Pradesh (Synthetic)",
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to establish joint river basin authorities, monitor continuous industrial effluent discharge, and protect perennial river flows.",
        "topics": ["continuous effluent telemetry", "polluter pays restoration fund", "river buffer zone easement", "inter state water council"],
    },
    {
        "id": "SYN-ACT-021",
        "title": "Digital Evidence Integrity and Electronic Chain of Custody Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "17",
        "domain": LegalDomain.CRIMINAL_LAW.value,
        "secondary": [LegalDomain.CIVIL_PROCEDURE.value, LegalDomain.IT_CYBER_LAW.value],
        "authority": "Central Cybersecurity Emergency Coordination Cell (Synthetic)",
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to standardize cryptographic hash verification for forensic seizures, cloud server imaging, and courtroom admissibility.",
        "topics": ["cryptographic hash seizure receipt", "cloud storage preservation order", "certified forensic examiner report", "hash tamper evidence exclusion"],
    },
    {
        "id": "SYN-ACT-022",
        "title": "Urban Rental Housing and Tenancy Security Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "28",
        "domain": LegalDomain.PROPERTY_REAL_ESTATE.value,
        "secondary": [LegalDomain.CONTRACT_LAW.value, LegalDomain.CIVIL_PROCEDURE.value],
        "authority": "Consumer Protection and Redressal Council (Synthetic)",
        "ministry": "Ministry of Urban Infrastructure and Transport (Synthetic)",
        "jurisdiction": "State of Uttaraanchal (Synthetic)",
        "preamble": "An Act to balance tenant rights with landlord property protections, regulate security deposits, and establish fast-track rent courts.",
        "topics": ["maximum two month security deposit", "written tenancy registration", "unlawful eviction prohibition", "rent authority dispute resolution"],
    },
    {
        "id": "SYN-ACT-023",
        "title": "Community Legal Aid and Village Paralegal Services Act, 2024 (Synthetic)",
        "year": 2024,
        "act_num": "13",
        "domain": LegalDomain.HUMAN_RIGHTS.value,
        "secondary": [LegalDomain.CONSTITUTIONAL_LAW.value, LegalDomain.CIVIL_PROCEDURE.value],
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "jurisdiction": "State of Dakshin Pradesh (Synthetic)",
        "preamble": "An Act to deploy trained community paralegals in rural panchayats, provide free legal representation, and operate mobile legal clinics.",
        "topics": ["paralegal volunteer certification", "mobile legal clinic schedule", "free counsel income ceiling", "lok adalat mediation integration"],
    },
    {
        "id": "SYN-ACT-024",
        "title": "Securities Tokenization and Digital Assets Regulatory Act, 2025 (Synthetic)",
        "year": 2025,
        "act_num": "6",
        "domain": LegalDomain.SECURITIES_CAPITAL_MARKETS.value,
        "secondary": [LegalDomain.BANKING_FINANCIAL.value, LegalDomain.COMMERCIAL_CORPORATE.value],
        "authority": "National Fair Lending and Credit Commission (Synthetic)",
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to recognize asset-backed security tokens on licensed distributed ledgers, establish custodian standards, and prevent market fraud.",
        "topics": ["licensed ledger operator", "smart contract security audit", "investor suitability assessment", "reserve backing ratio mandate"],
    },
    {
        "id": "SYN-ACT-025",
        "title": "Emergency Medical Care and Good Samaritan Protection Act, 2023 (Synthetic)",
        "year": 2023,
        "act_num": "10",
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "secondary": [LegalDomain.HUMAN_RIGHTS.value, LegalDomain.CRIMINAL_LAW.value],
        "authority": "Medical Devices Quality and Traceability Board (Synthetic)",
        "ministry": "Ministry of Health Technologies and Biosecurity (Synthetic)",
        "jurisdiction": "Union of Bharat (Synthetic)",
        "preamble": "An Act to mandate immediate stabilization of trauma victims by all hospitals without advance payment and shield good samaritans from legal coercion.",
        "topics": ["golden hour stabilization mandate", "prohibition of advance payment demand", "good samaritan civil immunity", "state trauma reimbursement fund"],
    },
]


def generate_act_sections(act_def: dict, rng: random.Random) -> List[Dict[str, Any]]:
    """
    Generate 18 to 28 realistic statutory sections for an Act.
    Includes subsections, clauses, definitions, obligations, provisos, and penalties.
    """
    sections: List[Dict[str, Any]] = []
    topics = act_def["topics"]
    act_title = act_def["title"]
    act_id = act_def["id"]

    # 1. Section 1: Short title, extent and commencement
    sec1_text = (
        f"(1) This Act may be called the {act_title}.\n"
        f"(2) It extends to the whole of the {act_def['jurisdiction']}.\n"
        f"(3) It shall come into force on such date as the Central Government or State Government "
        f"may, by notification in the Official Gazette, appoint: Provided that different dates may be "
        f"appointed for different provisions of this Act."
    )
    sections.append({
        "section_number": "1",
        "heading": "Short title, extent and commencement",
        "chapter": "Chapter I: Preliminary",
        "text": sec1_text,
        "provisions": ["Short title and territorial extent", "Commencement by official notification"],
        "explanations": ["Different dates may be appointed for different chapters."],
    })

    # 2. Section 2: Definitions
    def_items = [
        ('appropriate government', f'the Central Government in relation to Union territories and the State Government in relation to states within {act_def["jurisdiction"]}'),
        ('authority', f'the {act_def["authority"]} established under this Act'),
        ('person', 'includes an individual, a Hindu Undivided Family, a company, a firm, an association of persons, or a body of individuals, whether incorporated or not'),
        ('prescribed', 'prescribed by rules made under this Act'),
        ('compliance officer', 'a senior officer designated by a regulated entity to ensure adherence to statutory mandates'),
        ('notification', 'a notification published in the Official Gazette of Bharat (Synthetic)'),
        ('aggrieved person', 'any citizen, consumer, employee, or corporate body suffering prejudice or loss due to non-compliance with this Act'),
        ('digital system', 'any electronic computer, algorithm, network, database, or automated processing facility'),
    ]
    def_lines = ["In this Act, unless the context otherwise requires,—"]
    for idx, (term, meaning) in enumerate(def_items):
        letter = chr(ord('a') + idx)
        def_lines.append(f'({letter}) "{term}" means {meaning};')
    sec2_text = "\n".join(def_lines)
    sections.append({
        "section_number": "2",
        "heading": "Definitions",
        "chapter": "Chapter I: Preliminary",
        "text": sec2_text,
        "provisions": [f"Defines {term}" for term, _ in def_items],
        "explanations": ["Contextual interpretation applies across all chapters."],
    })

    # 3. Chapter II: Institutional Architecture & Regulators
    sections.append({
        "section_number": "3",
        "heading": f"Establishment and Constitution of {act_def['authority']}",
        "chapter": "Chapter II: Regulatory Framework and Authorities",
        "text": (
            f"(1) The Government shall, within ninety days from the commencement of this Act, by notification, "
            f"establish an authority to be known as the {act_def['authority']}.\n"
            f"(2) The Authority shall be a body corporate by the aforesaid name, having perpetual succession and a common seal, "
            f"with power to acquire, hold, and dispose of property, and shall by the said name sue or be sued.\n"
            f"(3) The head office of the Authority shall be situated at such place as may be notified."
        ),
        "provisions": ["Perpetual succession and corporate identity", "Power to contract and hold property"],
        "explanations": ["Headquarters determined by official notification."],
    })

    sections.append({
        "section_number": "4",
        "heading": "Composition and Qualifications of Chairperson and Members",
        "chapter": "Chapter II: Regulatory Framework and Authorities",
        "text": (
            f"(1) The Authority shall consist of a Chairperson and not less than four, but not exceeding six, whole-time Members.\n"
            f"(2) The Chairperson and Members shall be persons of ability, integrity, and standing who have special knowledge "
            f"of, and professional experience of not less than fifteen years in, law, public administration, or technical domains.\n"
            f"(3) The Chairperson and every Member shall hold office for a term of five years from the date on which they enter office "
            f"or until they attain the age of sixty-five years, whichever is earlier."
        ),
        "provisions": ["Composition of 1 Chairperson and 4 to 6 members", "Term limit: 5 years or 65 years of age"],
        "explanations": ["Members must satisfy 15-year domain experience requirement."],
    })

    # 4. Chapter III: Core Substantive Obligations (Topic-driven)
    ch_num = 5
    for topic_idx, topic in enumerate(topics):
        topic_title = topic.replace("_", " ").title()
        sections.append({
            "section_number": str(ch_num),
            "heading": f"Statutory Mandate regarding {topic_title}",
            "chapter": "Chapter III: Substantive Obligations and Standards",
            "text": (
                f"(1) Every entity subject to this Act shall implement measures to ensure {topic}.\n"
                f"(2) The measures referred to in subsection (1) shall comply with technical benchmarks and timelines "
                f"prescribed by the Authority within sixty days of commencement.\n"
                f"(3) Provided that the Authority may, for reasons recorded in writing, grant an extension not exceeding thirty days "
                f"to small enterprises upon satisfactory demonstration of technical hardship.\n"
                f"Explanation.—For the purposes of this section, compliance shall be audited by an independent certified auditor annually."
            ),
            "provisions": [f"Mandatory implementation of {topic}", "Thirty-day extension window upon proven hardship"],
            "explanations": ["Annual certified audit required for verification."],
        })
        ch_num += 1

        sections.append({
            "section_number": str(ch_num),
            "heading": f"Reporting and Disclosure Requirements for {topic_title}",
            "chapter": "Chapter III: Substantive Obligations and Standards",
            "text": (
                f"(1) Every regulated organization shall file a quarterly compliance return detailing all actions taken under Section {ch_num - 1}.\n"
                f"(2) The compliance return shall be submitted in electronic form on or before the fifteenth day of the month following the quarter.\n"
                f"(3) Failure to file the return within the prescribed timeline shall attract a late fee of rupees five thousand for each day of default."
            ),
            "provisions": ["Quarterly compliance return due by 15th of subsequent month", "Late fee of Rs. 5,000 per day"],
            "explanations": ["Electronic filing is mandatory."],
        })
        ch_num += 1

    # 5. Chapter IV: Citizen & Consumer Rights
    sections.append({
        "section_number": str(ch_num),
        "heading": "Right of Citizens to Information and Redressal",
        "chapter": "Chapter IV: Rights and Grievance Redressal",
        "text": (
            f"(1) Any citizen or consumer aggrieved by a contravention of this Act may lodge a formal complaint before the Grievance Officer.\n"
            f"(2) The Grievance Officer shall acknowledge receipt of the complaint within forty-eight hours and resolve the same within thirty days.\n"
            f"(3) Where the complainant is dissatisfied with the resolution, an appeal may be preferred to the Appellate Authority within forty-five days."
        ),
        "provisions": ["48-hour acknowledgment guarantee", "30-day resolution mandate", "45-day appellate window"],
        "explanations": ["Appellate Authority holds summary hearing jurisdiction."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Protection of Whistleblowers and Informants",
        "chapter": "Chapter IV: Rights and Grievance Redressal",
        "text": (
            f"(1) No employer or regulated entity shall discharge, demote, suspend, threaten, or harass an employee who submits information "
            f"regarding a violation of this Act to the Authority in good faith.\n"
            f"(2) Any person who retaliates against a whistleblower in violation of subsection (1) shall be liable to civil compensation "
            f"and fine as prescribed under Chapter V."
        ),
        "provisions": ["Strict whistleblower non-retaliation protection", "Civil damages for retaliatory termination"],
        "explanations": ["Good faith requirement is presumed unless proven otherwise."],
    })
    ch_num += 1

    # 6. Chapter V: Penalties, Adjudication, and Appeals
    sections.append({
        "section_number": str(ch_num),
        "heading": "Penalties for General Non-Compliance",
        "chapter": "Chapter V: Penalties and Adjudication",
        "text": (
            f"(1) Whoever contravenes any provision of this Act or any rule or regulation made thereunder for which no specific penalty is provided, "
            f"shall be punishable with a fine which may extend to rupees ten lakhs.\n"
            f"(2) In the case of a continuing contravention, an additional fine which may extend to rupees fifty thousand for every day "
            f"during which such contravention continues after conviction for the first such contravention may be imposed.\n"
            f"(3) All penalties recovered under this section shall be credited to the Citizen Welfare Fund."
        ),
        "provisions": ["General penalty up to Rs. 10,00,000", "Daily continuing fine up to Rs. 50,000"],
        "explanations": ["Proceeds credited to Citizen Welfare Fund."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Offences by Companies and Corporate Liability",
        "chapter": "Chapter V: Penalties and Adjudication",
        "text": (
            f"(1) Where an offence under this Act has been committed by a company, every person who at the time the offence was committed "
            f"was in charge of, and was responsible to, the company for the conduct of the business of the company, as well as the company, "
            f"shall be deemed to be guilty of the offence.\n"
            f"(2) Provided that nothing contained in subsection (1) shall render any such person liable to any punishment, if they prove "
            f"that the offence was committed without their knowledge or that they exercised all due diligence to prevent the commission of such offence."
        ),
        "provisions": ["Corporate officer joint liability", "Due diligence defence available to directors"],
        "explanations": ["Burden of proof on director to establish due diligence."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Establishment of Appellate Tribunal and Jurisdiction",
        "chapter": "Chapter V: Penalties and Adjudication",
        "text": (
            f"(1) The Central Government shall, by notification, confer appellate jurisdiction under this Act upon the "
            f"National Commercial Appellate Tribunal of Bharat (Synthetic).\n"
            f"(2) Any person aggrieved by an order of the Adjudicating Officer may file an appeal before the Appellate Tribunal "
            f"within sixty days from the date on which a copy of the order is received.\n"
            f"(3) The Appellate Tribunal shall endeavor to dispose of the appeal finally within six months."
        ),
        "provisions": ["60-day window to file appeal", "Target 6-month disposal timeline"],
        "explanations": ["Appellate Tribunal powers equivalent to a Civil Court under the Code of Civil Procedure."],
    })
    ch_num += 1

    # 7. Chapter VI: Miscellaneous
    sections.append({
        "section_number": str(ch_num),
        "heading": "Power of Central Government to make Rules",
        "chapter": "Chapter VI: Miscellaneous",
        "text": (
            f"(1) The Central Government may, by notification, make rules for carrying out the provisions of this Act.\n"
            f"(2) In particular, and without prejudice to the generality of the foregoing power, such rules may provide for—\n"
            f"  (a) the terms and conditions of appointment of the Chairperson and Members under Section 4;\n"
            f"  (b) the format and procedure for filing quarterly compliance returns under Section 6;\n"
            f"  (c) the standards and procedure for conducting algorithmic audits under Section 7;\n"
            f"  (d) any other matter which is required to be, or may be, prescribed."
        ),
        "provisions": ["Rule-making power delegated to Government", "Specific subjects for rule notification"],
        "explanations": ["Every rule made under this section shall be laid before Parliament."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Power of Authority to make Regulations",
        "chapter": "Chapter VI: Miscellaneous",
        "text": (
            f"(1) The Authority may, by notification, make regulations consistent with this Act and the rules made thereunder "
            f"to carry out the purposes of this Act.\n"
            f"(2) Regulations made under subsection (1) shall be published in the Official Gazette and on the official website."
        ),
        "provisions": ["Subordinate regulation-making power vested in Authority", "Mandatory gazette and website publication"],
        "explanations": ["Regulations cannot contradict central rules."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Protection of Action Taken in Good Faith",
        "chapter": "Chapter VI: Miscellaneous",
        "text": (
            f"No suit, prosecution, or other legal proceedings shall lie against the Central Government, the State Government, "
            f"the Authority, or any Chairperson, Member, officer, or other employee of the Authority for anything which is in good faith "
            f"done or intended to be done in pursuance of this Act or of any rule or regulation made thereunder."
        ),
        "provisions": ["Immunity for statutory officers acting in good faith", "Bar of civil suits against public servants"],
        "explanations": ["Malice or corrupt intent defeats immunity."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Act to have Overriding Effect",
        "chapter": "Chapter VI: Miscellaneous",
        "text": (
            f"The provisions of this Act shall have effect notwithstanding anything inconsistent therewith contained in any other law "
            f"for the time being in force, or in any instrument having effect by virtue of any law other than this Act."
        ),
        "provisions": ["Non-obstante clause establishing statutory supremacy", "Prevails over inconsistent pre-existing laws"],
        "explanations": ["Special law prevails over general laws."],
    })
    ch_num += 1

    sections.append({
        "section_number": str(ch_num),
        "heading": "Power to Remove Difficulties",
        "chapter": "Chapter VI: Miscellaneous",
        "text": (
            f"(1) If any difficulty arises in giving effect to the provisions of this Act, the Central Government may, by order published in the "
            f"Official Gazette, make such provisions not inconsistent with the provisions of this Act as appear to it to be necessary or expedient "
            f"for removing the difficulty: Provided that no such order shall be made after the expiry of a period of three years from the date of commencement.\n"
            f"(2) Every order made under this section shall be laid, as soon as may be after it is made, before each House of Parliament."
        ),
        "provisions": ["3-year sunset period for removal of difficulties orders", "Mandatory parliamentary laying requirement"],
        "explanations": ["Orders cannot amend the fundamental structure of the Act."],
    })

    return sections


def generate_all_acts(rng: Optional[random.Random] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generate all 25 base Acts plus multi-version amendments.
    Returns:
        (documents_list, all_sections_list)
    """
    if rng is None:
        rng = random.Random(20260925)

    documents: List[Dict[str, Any]] = []
    all_sections: List[Dict[str, Any]] = []

    for act_def in ACT_DEFINITIONS:
        doc_id = act_def["id"]
        vgroup_id = generate_version_group_id(act_def["title"], jurisdiction=act_def["jurisdiction"])

        # Generate base sections
        sections = generate_act_sections(act_def, rng)

        # Assemble full act raw text
        raw_text_parts = [
            f"# {act_def['title']}",
            f"[ACT NO. {act_def['act_num']} OF {act_def['year']}]",
            f"Jurisdiction: {act_def['jurisdiction']}",
            f"Ministry: {act_def['ministry']}",
            f"Authority: {act_def['authority']}",
            f"Status: SYNTHETIC-ONLY (Fictional legal instrument for software testing)",
            "\n## PREAMBLE\n",
            act_def["preamble"],
            "\n" + "=" * 60 + "\n",
        ]

        curr_chapter = ""
        for sec in sections:
            if sec["chapter"] != curr_chapter:
                curr_chapter = sec["chapter"]
                raw_text_parts.append(f"\n## {curr_chapter}\n")
            raw_text_parts.append(f"### Section {sec['section_number']}. {sec['heading']}")
            raw_text_parts.append(sec["text"] + "\n")

        full_raw_text = "\n".join(raw_text_parts)

        # Build Document record
        doc_meta = {
            "document_id": doc_id,
            "title": act_def["title"],
            "document_type": DocumentType.ACT.value,
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "source_name": "LegalLens Synthetic Corpus",
            "source_url": None,
            "synthetic": True,
            "legal_domain": act_def["domain"],
            "secondary_domains": act_def["secondary"],
            "act_year": act_def["year"],
            "act_number": act_def["act_num"],
            "jurisdiction": act_def["jurisdiction"],
            "ministry": act_def["ministry"],
            "document_version_group_id": vgroup_id,
            "version_label": "v1.0-original",
            "publication_date": f"{act_def['year']}-03-15",
            "effective_date": f"{act_def['year']}-05-01",
            "status": DocumentStatus.ACTIVE.value,
            "section_count": len(sections),
            "raw_text": full_raw_text,
        }
        documents.append(doc_meta)

        # Store section records
        for sec in sections:
            all_sections.append({
                "section_id": f"{doc_id}-SEC-{sec['section_number']}",
                "document_id": doc_id,
                "version_group_id": vgroup_id,
                "version_id": "v1.0-original",
                "title": f"Section {sec['section_number']} - {sec['heading']}",
                "domain": act_def["domain"],
                "chapter": sec["chapter"],
                "section": sec["section_number"],
                "section_number": sec["section_number"],
                "heading": sec["heading"],
                "text": sec["text"],
                "provisions": sec["provisions"],
                "explanations": sec["explanations"],
                "source_authority": SourceAuthority.SYNTHETIC.value,
                "synthetic": True,
                "page_start": int(sec["section_number"]),
                "page_end": int(sec["section_number"]),
            })

    # ── Additional Versions for Versioning Testing (SYN-ACT-010) ──
    # SYN-ACT-010 is Micro-Enterprise Insolvency Resolution Framework Act
    base_10 = next(a for a in ACT_DEFINITIONS if a["id"] == "SYN-ACT-010")
    vgroup_10 = generate_version_group_id(base_10["title"], jurisdiction=base_10["jurisdiction"])

    # Version 2: 2024 Amendment (Lowers creditor consent from 66% to 51%)
    doc_10_v2_id = "SYN-ACT-010-v2"
    v2_text = (
        f"# Micro-Enterprise Insolvency Resolution Framework (Amendment) Act, 2024 (Synthetic)\n"
        f"[ACT NO. 14 OF 2024]\n"
        f"An Act to amend the Micro-Enterprise Insolvency Resolution Framework Act, 2023.\n\n"
        f"Section 1. Short title: This Act may be called the Micro-Enterprise Insolvency Resolution Framework (Amendment) Act, 2024 (Synthetic).\n"
        f"Section 2. Amendment of Section 10: In Section 10 of the principal Act, for the words 'sixty-six percent of creditors', the words 'fifty-one percent of creditors' shall be substituted.\n"
        f"Section 3. Extension of Moratorium: The initial moratorium period under Section 11 is extended from 90 days to 120 days."
    )
    documents.append({
        "document_id": doc_10_v2_id,
        "title": "Micro-Enterprise Insolvency Resolution Framework (Amendment) Act, 2024 (Synthetic)",
        "document_type": DocumentType.AMENDMENT.value,
        "source_authority": SourceAuthority.SYNTHETIC.value,
        "source_name": "LegalLens Synthetic Corpus",
        "source_url": None,
        "synthetic": True,
        "legal_domain": base_10["domain"],
        "secondary_domains": base_10["secondary"],
        "act_year": 2024,
        "act_number": "14",
        "jurisdiction": base_10["jurisdiction"],
        "ministry": base_10["ministry"],
        "document_version_group_id": vgroup_10,
        "version_label": "v2.0-amendment",
        "publication_date": "2024-06-15",
        "effective_date": "2024-07-01",
        "supersedes_document_id": "SYN-ACT-010",
        "amendment_description": "Reduced creditor consent threshold to 51% and extended moratorium to 120 days.",
        "status": DocumentStatus.AMENDED.value,
        "section_count": 3,
        "raw_text": v2_text,
    })
    all_sections.extend([
        {
            "section_id": f"{doc_10_v2_id}-SEC-1",
            "document_id": doc_10_v2_id,
            "section_number": "1",
            "title": "Short title",
            "text": "This Act may be called the Micro-Enterprise Insolvency Resolution Framework (Amendment) Act, 2024 (Synthetic).",
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
        {
            "section_id": f"{doc_10_v2_id}-SEC-2",
            "document_id": doc_10_v2_id,
            "section_number": "2",
            "title": "Amendment of Section 10",
            "text": "In Section 10 of the principal Act, for the words 'sixty-six percent of creditors', the words 'fifty-one percent of creditors' shall be substituted.",
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
        {
            "section_id": f"{doc_10_v2_id}-SEC-3",
            "document_id": doc_10_v2_id,
            "section_number": "3",
            "title": "Extension of Moratorium",
            "text": "The initial moratorium period under Section 11 is extended from 90 days to 120 days.",
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
    ])

    # Version 3: 2025 Second Amendment
    doc_10_v3_id = "SYN-ACT-010-v3"
    v3_text = (
        f"# Micro-Enterprise Insolvency Resolution Framework (Second Amendment) Act, 2025 (Synthetic)\n"
        f"[ACT NO. 3 OF 2025]\n"
        f"An Act further to amend the Micro-Enterprise Insolvency Resolution Framework Act, 2023.\n\n"
        f"Section 1. Short title: This Act may be called the Micro-Enterprise Insolvency Resolution Framework (Second Amendment) Act, 2025 (Synthetic).\n"
        f"Section 2. Digital Submission Mandate: All pre-packaged resolution applications must be submitted via the National Insolvency Portal within 48 hours of board approval."
    )
    documents.append({
        "document_id": doc_10_v3_id,
        "title": "Micro-Enterprise Insolvency Resolution Framework (Second Amendment) Act, 2025 (Synthetic)",
        "document_type": DocumentType.AMENDMENT.value,
        "source_authority": SourceAuthority.SYNTHETIC.value,
        "source_name": "LegalLens Synthetic Corpus",
        "source_url": None,
        "synthetic": True,
        "legal_domain": base_10["domain"],
        "secondary_domains": base_10["secondary"],
        "act_year": 2025,
        "act_number": "3",
        "jurisdiction": base_10["jurisdiction"],
        "ministry": base_10["ministry"],
        "document_version_group_id": vgroup_10,
        "version_label": "v3.0-amendment",
        "publication_date": "2025-01-10",
        "effective_date": "2025-02-01",
        "supersedes_document_id": "SYN-ACT-010-v2",
        "amendment_description": "Added mandatory electronic filing within 48 hours.",
        "status": DocumentStatus.AMENDED.value,
        "section_count": 2,
        "raw_text": v3_text,
    })
    all_sections.extend([
        {
            "section_id": f"{doc_10_v3_id}-SEC-1",
            "document_id": doc_10_v3_id,
            "section_number": "1",
            "title": "Short title",
            "text": "This Act may be called the Micro-Enterprise Insolvency Resolution Framework (Second Amendment) Act, 2025 (Synthetic).",
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
        {
            "section_id": f"{doc_10_v3_id}-SEC-2",
            "document_id": doc_10_v3_id,
            "section_number": "2",
            "title": "Digital Submission Mandate",
            "text": "All pre-packaged resolution applications must be submitted via the National Insolvency Portal within 48 hours of board approval.",
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": 1,
            "page_end": 1,
        },
    ])

    # Version 4: 2026 Consolidated Act
    doc_10_v4_id = "SYN-ACT-010-v4"
    # Build consolidated sections based on base sections
    base_10_sections = [s for s in all_sections if s["document_id"] == "SYN-ACT-010"]
    v4_sections = []
    v4_lines = [
        "# Micro-Enterprise Insolvency Resolution Framework Act, 2026 (Consolidated) (Synthetic)",
        "[ACT NO. 31-C OF 2026]",
        "An Act to provide a simplified, pre-packaged insolvency resolution framework for micro, small, and medium enterprises, as amended up to 2026.",
        ""
    ]
    for bs in base_10_sections:
        s_num = bs["section_number"]
        s_title = bs["title"]
        s_text = bs["text"]
        if s_num == "10":
            s_text = "The committee of creditors may approve a pre-packaged resolution plan with the affirmative vote of not less than fifty-one percent of voting share of financial creditors."
        elif s_num == "11":
            s_text = "An initial moratorium period of one hundred and twenty days shall take effect upon admission of the resolution application."
        v4_sections.append({
            "section_id": f"{doc_10_v4_id}-SEC-{s_num}",
            "document_id": doc_10_v4_id,
            "section_number": s_num,
            "title": s_title,
            "text": s_text,
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "synthetic": True,
            "page_start": bs["page_start"],
            "page_end": bs["page_end"],
        })
        v4_lines.append(f"Section {s_num}. {s_title}: {s_text}\n")
    all_sections.extend(v4_sections)

    documents.append({
        "document_id": doc_10_v4_id,
        "title": "Micro-Enterprise Insolvency Resolution Framework Act, 2026 (Consolidated) (Synthetic)",
        "document_type": DocumentType.ACT.value,
        "source_authority": SourceAuthority.SYNTHETIC.value,
        "source_name": "LegalLens Synthetic Corpus",
        "source_url": None,
        "synthetic": True,
        "legal_domain": base_10["domain"],
        "secondary_domains": base_10["secondary"],
        "act_year": 2026,
        "act_number": "31-C",
        "jurisdiction": base_10["jurisdiction"],
        "ministry": base_10["ministry"],
        "document_version_group_id": vgroup_10,
        "version_label": "v4.0-consolidated",
        "publication_date": "2026-03-31",
        "effective_date": "2026-04-01",
        "supersedes_document_id": "SYN-ACT-010-v3",
        "amendment_description": "Consolidated text incorporating 2024 and 2025 amendments into a single official enactment.",
        "status": DocumentStatus.ACTIVE.value,
        "section_count": len(v4_sections),
        "raw_text": "\n".join(v4_lines),
    })

    return documents, all_sections
    
generate_synthetic_acts = generate_all_acts
