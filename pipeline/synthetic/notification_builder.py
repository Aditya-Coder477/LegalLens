"""
pipeline/synthetic/notification_builder.py
==========================================
Generates 30 synthetic Government Notifications and Circulars.
Includes effective dates, compliance thresholds, fee revisions, and enforcement directives.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from pipeline.core.metadata import DocumentType, LegalDomain, SourceAuthority, DocumentStatus
from pipeline.synthetic.taxonomy import SYNTHETIC_MINISTRIES, SYNTHETIC_AUTHORITIES

NOTIFICATION_SPECS = [
    {
        "id": "SYN-NOTIF-001",
        "parent_act_id": "SYN-ACT-001",
        "title": "Mandatory Registration Threshold for Social Media Intermediaries Notification, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "notif_no": "S.O. 412(E)",
        "summary": "Fixes 5,00,000 registered users in Bharat as threshold for Significant Social Media Intermediary status.",
    },
    {
        "id": "SYN-NOTIF-002",
        "parent_act_id": "SYN-ACT-001",
        "title": "Establishment of Digital Redressal Appeal Benches Notification, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "notif_no": "S.O. 504(E)",
        "summary": "Establishes three specialized online benches for speedy consumer grievance adjudications.",
    },
    {
        "id": "SYN-NOTIF-003",
        "parent_act_id": "SYN-ACT-002",
        "title": "Annual Renewable Purchase Obligation Targets Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ELECTRICITY_ENERGY.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "F. No. CE-2024/09",
        "summary": "Mandates 28.5% renewable power purchase trajectory for state distribution utilities for FY 2024-25.",
    },
    {
        "id": "SYN-NOTIF-004",
        "parent_act_id": "SYN-ACT-002",
        "title": "Open Access Wheeling Charge Waiver Guidelines Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ELECTRICITY_ENERGY.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "CIRCULAR-RPO-04",
        "summary": "Clarifies 100% waiver of wheeling charges for green hydrogen production units.",
    },
    {
        "id": "SYN-NOTIF-005",
        "parent_act_id": "SYN-ACT-003",
        "title": "Maximum Permissible APR on Short-Term Microcredits Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.BANKING_FINANCIAL.value,
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "notif_no": "S.O. 883(E)",
        "summary": "Caps total annualized percentage rate including processing fees at 24% per annum.",
    },
    {
        "id": "SYN-NOTIF-006",
        "parent_act_id": "SYN-ACT-003",
        "title": "Prohibition of Coercive Recovery Practices Advisory Circular, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.BANKING_FINANCIAL.value,
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "notif_no": "CIRCULAR-LEND-12",
        "summary": "Bars recovery calls between 7:00 PM and 8:00 AM and mandates registration of agency employees.",
    },
    {
        "id": "SYN-NOTIF-007",
        "parent_act_id": "SYN-ACT-004",
        "title": "Classification of High-Risk Cardiovascular Stents Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "ministry": "Ministry of Health Technologies and Biosecurity (Synthetic)",
        "notif_no": "S.O. 1290(E)",
        "summary": "Upgrades Class C coronary stents to Class D high-risk requiring batch-wise laboratory pre-clearance.",
    },
    {
        "id": "SYN-NOTIF-008",
        "parent_act_id": "SYN-ACT-004",
        "title": "Unique Device Identifier (UDI) Phase II Implementation Schedule Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "ministry": "Ministry of Health Technologies and Biosecurity (Synthetic)",
        "notif_no": "CIRCULAR-MED-08",
        "summary": "Requires all orthopedic implant manufacturers to affix GS1 barcodes by 1st October 2024.",
    },
    {
        "id": "SYN-NOTIF-009",
        "parent_act_id": "SYN-ACT-005",
        "title": "Designation of Critical Infrastructure AI Systems Notification, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.EMERGING_TECHNOLOGY_AI.value,
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "notif_no": "S.O. 312(E)",
        "summary": "Designates power grid management and air traffic flow AI models as Tier-1 Critical Systems.",
    },
    {
        "id": "SYN-NOTIF-010",
        "parent_act_id": "SYN-ACT-005",
        "title": "Watermarking Compliance Timeline for Generative Audio Circular, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.EMERGING_TECHNOLOGY_AI.value,
        "ministry": "Ministry of Digital Economy and Innovation (Synthetic)",
        "notif_no": "CIRCULAR-AI-02",
        "summary": "Directs all synthetic voice generators to embed inaudible acoustic watermarks within 60 days.",
    },
    {
        "id": "SYN-NOTIF-011",
        "parent_act_id": "SYN-ACT-006",
        "title": "Mandatory Ergonomic Audit Frequency Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.EMPLOYMENT_LABOUR.value,
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "notif_no": "S.O. 671(E)",
        "summary": "Mandates annual ergonomic evaluations for companies employing more than 50 remote personnel.",
    },
    {
        "id": "SYN-NOTIF-012",
        "parent_act_id": "SYN-ACT-006",
        "title": "Guidance on Right to Disconnect Exemption Criteria Circular, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.EMPLOYMENT_LABOUR.value,
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "notif_no": "CIRCULAR-LAB-15",
        "summary": "Restricts emergency call exceptions to critical cyber defense and life-safety operations only.",
    },
    {
        "id": "SYN-NOTIF-013",
        "parent_act_id": "SYN-ACT-007",
        "title": "Critical Groundwater Over-Exploited Zones Declaration Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "S.O. 1102(E)",
        "summary": "Declares 14 industrial clusters in Dakshin Pradesh as severely stressed critical groundwater basins.",
    },
    {
        "id": "SYN-NOTIF-014",
        "parent_act_id": "SYN-ACT-007",
        "title": "Mandatory Telemetric Flow Meter Installation Deadlines Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "CIRCULAR-ENV-09",
        "summary": "Requires all extraction units pumping exceeding 50,000 liters/day to install live IoT flow meters.",
    },
    {
        "id": "SYN-NOTIF-015",
        "parent_act_id": "SYN-ACT-008",
        "title": "Accreditation Fees for Commercial ODR Portals Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.ARBITRATION_ADR.value,
        "ministry": "Department of Consumer Empowerment (Synthetic)",
        "notif_no": "S.O. 589(E)",
        "summary": "Fixes annual licensing and inspection fee for certified dispute platforms at ₹50,000.",
    },
    {
        "id": "SYN-NOTIF-016",
        "parent_act_id": "SYN-ACT-009",
        "title": "List of Mandatory Reportable Cyber Incidents Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "notif_no": "S.O. 945(E)",
        "summary": "Expands reportable cyber threats to include ransomware extortion, credential stuffing, and DNS tampering.",
    },
    {
        "id": "SYN-NOTIF-017",
        "parent_act_id": "SYN-ACT-009",
        "title": "Preservation Period for Server System Logs Advisory Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "notif_no": "CIRCULAR-CYBER-03",
        "summary": "Mandates rolling 180-day secure encrypted archival of network traffic, login logs, and firewall logs.",
    },
    {
        "id": "SYN-NOTIF-018",
        "parent_act_id": "SYN-ACT-010",
        "title": "Default Threshold for Micro-Enterprise Insolvency Initiation Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.INSOLVENCY_BANKRUPTCY.value,
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "notif_no": "S.O. 221(E)",
        "summary": "Sets minimum default amount at ₹10,00,000 for triggering pre-packaged resolution.",
    },
    {
        "id": "SYN-NOTIF-019",
        "parent_act_id": "SYN-ACT-011",
        "title": "Prohibition of Drip Pricing on Airline and Event Booking Sites Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.CONSUMER_LAW.value,
        "ministry": "Department of Consumer Empowerment (Synthetic)",
        "notif_no": "S.O. 1432(E)",
        "summary": "Explicitly declares non-disclosure of final convenience fees until checkout as an illegal dark pattern.",
    },
    {
        "id": "SYN-NOTIF-020",
        "parent_act_id": "SYN-ACT-011",
        "title": "Mandatory Spare Parts Availability for Consumer Electronics Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.CONSUMER_LAW.value,
        "ministry": "Department of Consumer Empowerment (Synthetic)",
        "notif_no": "CIRCULAR-CONS-07",
        "summary": "Requires smartphone manufacturers to supply replacement screens and batteries to third-party shops.",
    },
    {
        "id": "SYN-NOTIF-021",
        "parent_act_id": "SYN-ACT-012",
        "title": "Autonomous Vehicle Public Highway Pilot Corridor Declaration Notification, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
        "ministry": "Ministry of Urban Infrastructure and Transport (Synthetic)",
        "notif_no": "S.O. 805(E)",
        "summary": "Notifies 120km section of National Express Highway 4 for supervised Level-3 automated truck trials.",
    },
    {
        "id": "SYN-NOTIF-022",
        "parent_act_id": "SYN-ACT-013",
        "title": "Capital Subsidy Rates for Solar Cold Storage Facilities Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.COMMERCIAL_CORPORATE.value,
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "notif_no": "S.O. 390(E)",
        "summary": "Authorizes 35% capital subsidy for farmer-producer cooperatives installing solar chillers.",
    },
    {
        "id": "SYN-NOTIF-023",
        "parent_act_id": "SYN-ACT-014",
        "title": "Diagnostic Center Lab Report API Interoperability Directive Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "ministry": "Ministry of Health Technologies and Biosecurity (Synthetic)",
        "notif_no": "CIRCULAR-EHR-05",
        "summary": "Directs private diagnostic networks to issue patient reports via FHIR RESTful endpoints.",
    },
    {
        "id": "SYN-NOTIF-024",
        "parent_act_id": "SYN-ACT-015",
        "title": "RERA Escrow Account Quarterly Architect Certification Mandate Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.PROPERTY_REAL_ESTATE.value,
        "ministry": "Ministry of Urban Infrastructure and Transport (Synthetic)",
        "notif_no": "S.O. 981(E)",
        "summary": "Mandates co-signature of chartered accountant and structural engineer for withdrawals over ₹50 lakh.",
    },
    {
        "id": "SYN-NOTIF-025",
        "parent_act_id": "SYN-ACT-017",
        "title": "Dynamic 6 GHz Spectrum Shared Band Access Rules Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.TELECOMMUNICATIONS.value,
        "ministry": "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
        "notif_no": "CIRCULAR-TEL-11",
        "summary": "Permits unlicensed low-power indoor Wi-Fi 7 operation across 5925-6425 MHz sub-band.",
    },
    {
        "id": "SYN-NOTIF-026",
        "parent_act_id": "SYN-ACT-018",
        "title": "EPR Targets for Multi-Layered Plastic Packaging Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "S.O. 1150(E)",
        "summary": "Increases mandatory minimum post-consumer recycling percentage to 60% for brand owners.",
    },
    {
        "id": "SYN-NOTIF-027",
        "parent_act_id": "SYN-ACT-020",
        "title": "Commercial Drone Flight Corridor Speed and Altitude Boundaries Notification, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
        "ministry": "Ministry of Urban Infrastructure and Transport (Synthetic)",
        "notif_no": "S.O. 620(E)",
        "summary": "Caps commercial logistics drone maximum altitude at 120 meters and cruise speed at 80 km/h.",
    },
    {
        "id": "SYN-NOTIF-028",
        "parent_act_id": "SYN-ACT-021",
        "title": "Market Dominance Presumption Threshold in Digital Search Markets Notification, 2025 (Synthetic)",
        "year": 2025,
        "domain": LegalDomain.COMPETITION_LAW.value,
        "ministry": "Ministry of Commerce and Fair Competition (Synthetic)",
        "notif_no": "S.O. 248(E)",
        "summary": "Establishes statutory rebuttable presumption of dominance where search market share exceeds 40%.",
    },
    {
        "id": "SYN-NOTIF-029",
        "parent_act_id": "SYN-ACT-022",
        "title": "Carbon Intensity Calculation Methodology for Green Ammonia Circular, 2024 (Synthetic)",
        "year": 2024,
        "domain": LegalDomain.ELECTRICITY_ENERGY.value,
        "ministry": "Ministry of Clean Energy and Climate Transition (Synthetic)",
        "notif_no": "CIRCULAR-HYDRO-01",
        "summary": "Publishes lifecycle greenhouse gas emission accounting formulas for certified export credits.",
    },
    {
        "id": "SYN-NOTIF-030",
        "parent_act_id": "SYN-ACT-024",
        "title": "Annual Income Ceiling Revision for Free Legal Aid Eligibility Notification, 2023 (Synthetic)",
        "year": 2023,
        "domain": LegalDomain.HUMAN_RIGHTS.value,
        "ministry": "Ministry of Citizen Welfare and Legal Services (Synthetic)",
        "notif_no": "S.O. 715(E)",
        "summary": "Revises maximum annual income ceiling from ₹1,50,000 to ₹3,00,000 for indigent litigants.",
    },
]

def generate_synthetic_notifications() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generates 30 synthetic notifications and circulars with structured clauses."""
    documents: List[Dict[str, Any]] = []
    all_sections: List[Dict[str, Any]] = []

    for item in NOTIFICATION_SPECS:
        doc_id = item["id"]
        title = item["title"]
        notif_no = item["notif_no"]
        is_circular = "Circular" in title
        doc_type = DocumentType.CIRCULAR.value if is_circular else DocumentType.NOTIFICATION.value

        clauses = [
            ("1", "Subject and Statutory Authority", f"In exercise of powers conferred under Section 18 of {item['parent_act_id']}, the Central Government hereby issues the following directive regarding {title}."),
            ("2", "Scope of Application", f"This directive shall be applicable to all entities, commercial establishments, and authorities operating under the purview of {item['parent_act_id']}."),
            ("3", "Operative Mandate and Compliance Thresholds", item["summary"]),
            ("4", "Timelines and Effective Date", f"The provisions of this directive shall come into force with effect from thirty days following its publication in the Official Gazette, unless an earlier date is specifically notified."),
            ("5", "Enforcement and Penal Consequences", f"Failure to comply with the mandates herein shall attract penal proceedings under the general penalty provisions of {item['parent_act_id']} and may result in suspension of operating licenses."),
        ]

        text_lines = [
            f"# {title}",
            f"Notification No: {notif_no}",
            f"Authority: {item['ministry']}",
            f"Published under parent Act: {item['parent_act_id']}\n",
        ]

        for c_num, c_title, c_text in clauses:
            sec_id = f"{doc_id}-CLAUSE-{c_num}"
            all_sections.append({
                "section_id": sec_id,
                "document_id": doc_id,
                "section_number": c_num,
                "title": c_title,
                "text": c_text,
                "source_authority": SourceAuthority.SYNTHETIC.value,
                "synthetic": True,
                "page_start": 1,
                "page_end": 1,
            })
            text_lines.append(f"Paragraph {c_num}. {c_title}: {c_text}\n")

        raw_text = "\n".join(text_lines)

        documents.append({
            "document_id": doc_id,
            "title": title,
            "document_type": doc_type,
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "source_name": "LegalLens Synthetic Corpus",
            "source_url": None,
            "synthetic": True,
            "legal_domain": item["domain"],
            "secondary_domains": [],
            "act_year": item["year"],
            "act_number": notif_no,
            "jurisdiction": "Union of Bharat (Synthetic)",
            "ministry": item["ministry"],
            "parent_act_id": item["parent_act_id"],
            "document_version_group_id": f"vg-{doc_id.lower()}",
            "version_label": "v1.0",
            "publication_date": f"{item['year']}-07-10",
            "effective_date": f"{item['year']}-08-01",
            "status": DocumentStatus.ACTIVE.value,
            "section_count": len(clauses),
            "raw_text": raw_text,
        })

    return documents, all_sections
