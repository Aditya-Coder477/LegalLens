"""
pipeline/synthetic/guidance_builder.py
======================================
Generates 20 synthetic legal-aid manuals, citizen handbooks, and compliance checklists.
Emphasizes plain-language legal guidance, eligibility thresholds, and actionable step-by-step instructions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pipeline.core.metadata import DocumentType, LegalDomain, SourceAuthority, DocumentStatus
from pipeline.synthetic.taxonomy import SYNTHETIC_AUTHORITIES

GUIDANCE_SPECS = [
    {
        "id": "SYN-GUIDE-001",
        "title": "Citizen Handbook on Digital Privacy and Data Breach Remedies (Synthetic)",
        "domain": LegalDomain.DATA_PROTECTION_PRIVACY.value,
        "parent_act_id": "SYN-ACT-001",
        "year": 2025,
        "authority": "Digital Services Regulatory Authority of Bharat (Synthetic)",
        "topic": "Filing data breach complaints and seeking compensation for leaked personal identifiers",
    },
    {
        "id": "SYN-GUIDE-002",
        "title": "Rooftop Solar Grid Interconnection: Practical Consumer Manual (Synthetic)",
        "domain": LegalDomain.ELECTRICITY_ENERGY.value,
        "parent_act_id": "SYN-ACT-002",
        "year": 2024,
        "authority": "National Clean Energy Grid Council (Synthetic)",
        "topic": "Net-metering application process, subsidy claims, and dispute escalation with local DISCOMs",
    },
    {
        "id": "SYN-GUIDE-003",
        "title": "Borrower Defense Manual: Protection Against Unfair Digital Lending (Synthetic)",
        "domain": LegalDomain.BANKING_FINANCIAL.value,
        "parent_act_id": "SYN-ACT-003",
        "year": 2023,
        "authority": "National Fair Lending and Credit Commission (Synthetic)",
        "topic": "Remedies against illegal interest rates, recovery harassment, and unauthorized contact scraping",
    },
    {
        "id": "SYN-GUIDE-004",
        "title": "Patient Guide to Medical Implant Registries and Adverse Incident Redressal (Synthetic)",
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "parent_act_id": "SYN-ACT-004",
        "year": 2024,
        "authority": "Medical Devices Quality and Traceability Board (Synthetic)",
        "topic": "Tracking unique device identifiers for implants and applying for compensation for defective prosthetics",
    },
    {
        "id": "SYN-GUIDE-005",
        "title": "Workplace Rights Handbook for Hybrid and Remote Employees (Synthetic)",
        "domain": LegalDomain.EMPLOYMENT_LABOUR.value,
        "parent_act_id": "SYN-ACT-006",
        "year": 2023,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Enforcing the right to disconnect, claiming ergonomic allowances, and overtime rules",
    },
    {
        "id": "SYN-GUIDE-006",
        "title": "Residential Rainwater Harvesting Compliance and Subsidy Checklist (Synthetic)",
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "parent_act_id": "SYN-ACT-007",
        "year": 2024,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Technical checklist for housing societies to obtain mandatory groundwater recharge clearance",
    },
    {
        "id": "SYN-GUIDE-007",
        "title": "Step-by-Step Guide to Online Dispute Resolution for E-Commerce Buyers (Synthetic)",
        "domain": LegalDomain.ARBITRATION_ADR.value,
        "parent_act_id": "SYN-ACT-008",
        "year": 2023,
        "authority": "Consumer Protection and Redressal Council (Synthetic)",
        "topic": "How to initiate free online conciliation for delayed deliveries, fake goods, and refund refusals",
    },
    {
        "id": "SYN-GUIDE-008",
        "title": "Small Business Cybersecurity Incident Response and Reporting Playbook (Synthetic)",
        "domain": LegalDomain.IT_CYBER_LAW.value,
        "parent_act_id": "SYN-ACT-009",
        "year": 2024,
        "authority": "Central Cybersecurity Emergency Coordination Cell (Synthetic)",
        "topic": "Actionable 6-hour incident reporting checklist and ransomware extortion legal dos-and-don'ts",
    },
    {
        "id": "SYN-GUIDE-009",
        "title": "MSME Entrepreneur Handbook on Pre-Packaged Insolvency Workouts (Synthetic)",
        "domain": LegalDomain.INSOLVENCY_BANKRUPTCY.value,
        "parent_act_id": "SYN-ACT-010",
        "year": 2023,
        "authority": "National Fair Lending and Credit Commission (Synthetic)",
        "topic": "Preparing a turnaround plan, negotiating with creditors, and maintaining promoter control",
    },
    {
        "id": "SYN-GUIDE-010",
        "title": "Consumer Guide to Dark Pattern Identification and Complaint Lodging (Synthetic)",
        "domain": LegalDomain.CONSUMER_LAW.value,
        "parent_act_id": "SYN-ACT-011",
        "year": 2024,
        "authority": "Consumer Protection and Redressal Council (Synthetic)",
        "topic": "Recognizing sneak-in baskets, forced subscriptions, fake countdowns, and reporting to the council",
    },
    {
        "id": "SYN-GUIDE-011",
        "title": "Right to Repair Electronics: Consumer Toolkit and Authorized Service Rights (Synthetic)",
        "domain": LegalDomain.CONSUMER_LAW.value,
        "parent_act_id": "SYN-ACT-011",
        "year": 2024,
        "authority": "Consumer Protection and Redressal Council (Synthetic)",
        "topic": "Securing genuine parts, schematic diagrams, and defeating warranty-void stickers",
    },
    {
        "id": "SYN-GUIDE-012",
        "title": "Commercial Fleet Transition: Electric Vehicle Subsidies and Battery Safety Manual (Synthetic)",
        "domain": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
        "parent_act_id": "SYN-ACT-012",
        "year": 2025,
        "authority": "National Electronic Toll and Highway Safety Directorate (Synthetic)",
        "topic": "Claiming EV incentives, installing certified chargers, and complying with thermal safety standards",
    },
    {
        "id": "SYN-GUIDE-013",
        "title": "Agricultural Cold Storage Entrepreneur Setup and Grant Application Manual (Synthetic)",
        "domain": LegalDomain.COMMERCIAL_CORPORATE.value,
        "parent_act_id": "SYN-ACT-013",
        "year": 2023,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Step-by-step guidance for farmer collectives to obtain 35% capital subsidy and clean energy credits",
    },
    {
        "id": "SYN-GUIDE-014",
        "title": "Patient Rights to Electronic Health Records Portability and Correction (Synthetic)",
        "domain": LegalDomain.HEALTH_MEDICAL.value,
        "parent_act_id": "SYN-ACT-014",
        "year": 2024,
        "authority": "Medical Devices Quality and Traceability Board (Synthetic)",
        "topic": "Accessing digital hospital discharge records, withdrawing consent, and disputing billing errors",
    },
    {
        "id": "SYN-GUIDE-015",
        "title": "Homebuyer Guide: Verifying RERA Escrow Accounts and Construction Progress (Synthetic)",
        "domain": LegalDomain.PROPERTY_REAL_ESTATE.value,
        "parent_act_id": "SYN-ACT-015",
        "year": 2023,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Checking certified architect certificates, tracking escrow deposits, and filing delay claims",
    },
    {
        "id": "SYN-GUIDE-016",
        "title": "Commercial Drone Operator Compliance and Green Zone Navigation Guide (Synthetic)",
        "domain": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
        "parent_act_id": "SYN-ACT-020",
        "year": 2024,
        "authority": "National Electronic Toll and Highway Safety Directorate (Synthetic)",
        "topic": "Obtaining pilot UIN, logging autonomous delivery routes, and third-party insurance mandates",
    },
    {
        "id": "SYN-GUIDE-017",
        "title": "Industrial Packaging Extended Producer Responsibility (EPR) Filing Handbook (Synthetic)",
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "parent_act_id": "SYN-ACT-018",
        "year": 2024,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Annual return filing for plastic waste recyclers, brand owners, and credit trading mechanism",
    },
    {
        "id": "SYN-GUIDE-018",
        "title": "Student and Worker Guide to Digital Skill Accreditation and ABC Credit Bank (Synthetic)",
        "domain": LegalDomain.EDUCATION_LAW.value,
        "parent_act_id": "SYN-ACT-019",
        "year": 2023,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Accumulating and transferring online vocational credits towards recognized university degrees",
    },
    {
        "id": "SYN-GUIDE-019",
        "title": "Citizen Guide to Free Legal Services and Lok Adalat Conciliation (Synthetic)",
        "domain": LegalDomain.HUMAN_RIGHTS.value,
        "parent_act_id": "SYN-ACT-024",
        "year": 2023,
        "authority": "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
        "topic": "Eligibility criteria, income limits, appointing free defense counsel, and Lok Adalat finality",
    },
    {
        "id": "SYN-GUIDE-020",
        "title": "Community Biogas Waste-to-Energy Project Developer Guide (Synthetic)",
        "domain": LegalDomain.ENVIRONMENTAL_LAW.value,
        "parent_act_id": "SYN-ACT-025",
        "year": 2024,
        "authority": "National Clean Energy Grid Council (Synthetic)",
        "topic": "Feedstock supply contracts, pipeline interconnection clearance, and environmental subsidies",
    },
]

def generate_synthetic_guidance() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generates 20 synthetic guidance handbooks and citizen checklists."""
    documents: List[Dict[str, Any]] = []
    all_sections: List[Dict[str, Any]] = []

    for item in GUIDANCE_SPECS:
        doc_id = item["id"]
        title = item["title"]

        sections = [
            ("1", "Executive Overview & Plain Language Summary", f"This handbook provides practical guidance on {item['topic']}. It explains rights, timelines, and relief under {item['parent_act_id']} in simple, non-technical terms."),
            ("2", "Who Is Eligible & Scope of Protection", f"Any citizen, small enterprise, or affected party residing within the Union of Bharat is eligible to invoke these protections if they have suffered pecuniary loss or operational disruption under {item['parent_act_id']}."),
            ("3", "Mandatory Documentation Checklist", f"Before lodging a formal grievance or application, gather: (a) Valid proof of identification, (b) Transaction or contract records, (c) Communication history with the counterparty, (d) Certified loss estimation or diagnostic log."),
            ("4", "Step-by-Step Action Procedure", f"Step 1: Serve a 15-day formal notice to the service provider. Step 2: If unresolved, register a ticket on the centralized redressal portal. Step 3: Attend the scheduled digital conciliation session. Step 4: Obtain a binding settlement agreement or escalate to the Appellate Authority."),
            ("5", "Common Traps and What to Avoid", f"Do not sign blanket waiver forms or accept informal oral promises. Always preserve digital timestamps and hash verifications for submitted materials."),
            ("6", "Frequently Asked Questions (FAQs)", f"Q: How much does it cost to file? A: Filing through the official portal is free of cost for individual consumers and subsidized for MSMEs.\nQ: What is the average resolution time? A: Standard proceedings conclude within 30 to 45 business days."),
        ]

        text_lines = [
            f"# {title}",
            f"Issued by: {item['authority']}",
            f"Subject: {item['topic']}",
            f"Reference Enactment: {item['parent_act_id']}\n",
        ]

        for s_num, s_title, s_text in sections:
            sec_id = f"{doc_id}-SEC-{s_num}"
            all_sections.append({
                "section_id": sec_id,
                "document_id": doc_id,
                "section_number": s_num,
                "title": s_title,
                "text": s_text,
                "source_authority": SourceAuthority.SYNTHETIC.value,
                "synthetic": True,
                "page_start": int(s_num),
                "page_end": int(s_num),
            })
            text_lines.append(f"Section {s_num}. {s_title}\n{s_text}\n")

        raw_text = "\n".join(text_lines)

        documents.append({
            "document_id": doc_id,
            "title": title,
            "document_type": DocumentType.GUIDELINES.value,
            "source_authority": SourceAuthority.SYNTHETIC.value,
            "source_name": "LegalLens Synthetic Corpus",
            "source_url": None,
            "synthetic": True,
            "legal_domain": item["domain"],
            "secondary_domains": [],
            "act_year": item["year"],
            "act_number": None,
            "jurisdiction": "Union of Bharat (Synthetic)",
            "ministry": item["authority"],
            "parent_act_id": item["parent_act_id"],
            "document_version_group_id": f"vg-{doc_id.lower()}",
            "version_label": "v1.0",
            "publication_date": f"{item['year']}-08-20",
            "effective_date": f"{item['year']}-08-20",
            "status": DocumentStatus.ACTIVE.value,
            "section_count": len(sections),
            "raw_text": raw_text,
        })

    return documents, all_sections
