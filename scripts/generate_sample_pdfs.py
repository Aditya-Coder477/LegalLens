"""
scripts/generate_sample_pdfs.py
===============================
Generates realistic Indian legal PDF documents in the `sample_documents/` folder.
These documents can be uploaded to LegalLens to test:
- Non-compete clause enforceability under S.27 Indian Contract Act
- Notice periods and buyout terms
- Obligations and conditions extraction
- Deadlines, lock-in periods, and cure timelines
- Executive summaries and document-scoped Q&A
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "sample_documents"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "DocTitle",
    parent=styles["Heading1"],
    fontSize=16,
    leading=20,
    textColor=colors.HexColor("#0f172a"),
    alignment=1, # Center
    spaceAfter=10,
    fontName="Helvetica-Bold",
)

subtitle_style = ParagraphStyle(
    "DocSubtitle",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#475569"),
    alignment=1,
    spaceAfter=15,
    fontName="Helvetica-Oblique",
)

section_heading = ParagraphStyle(
    "SectionHeading",
    parent=styles["Heading2"],
    fontSize=11,
    leading=15,
    textColor=colors.HexColor("#1e3a8a"),
    spaceBefore=10,
    spaceAfter=4,
    fontName="Helvetica-Bold",
)

body_style = ParagraphStyle(
    "BodyDark",
    parent=styles["BodyText"],
    fontSize=9.5,
    leading=14,
    textColor=colors.HexColor("#1e293b"),
    spaceAfter=8,
    fontName="Helvetica",
)

disclaimer_style = ParagraphStyle(
    "DisclaimerBox",
    parent=styles["Normal"],
    fontSize=8,
    leading=11,
    textColor=colors.HexColor("#64748b"),
    alignment=1,
    spaceBefore=12,
    fontName="Helvetica-Oblique",
)


def create_employment_agreement():
    path = OUTPUT_DIR / "Executive_Employment_Agreement.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("EXECUTIVE EMPLOYMENT AGREEMENT", title_style))
    story.append(Paragraph("This Agreement is executed at Bengaluru, Karnataka, India on 15th October 2024", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    story.append(Paragraph("<b>PARTIES:</b>", section_heading))
    story.append(Paragraph("1. <b>TECHNOVA SOLUTIONS INDIA PRIVATE LIMITED</b>, a company incorporated under the Companies Act, 2013, having its registered office at Electronic City, Phase 1, Bengaluru, Karnataka - 560100 (hereinafter referred to as the <i>'Employer'</i> or <i>'Company'</i>); and", body_style))
    story.append(Paragraph("2. <b>MR. ARJUN SHARMA</b>, an Indian citizen residing at Indiranagar, Bengaluru - 560038 (hereinafter referred to as the <i>'Executive'</i>).", body_style))

    story.append(Paragraph("<b>SECTION 1: POSITION AND SCOPE OF EMPLOYMENT</b>", section_heading))
    story.append(Paragraph("1.1 The Company hereby employs the Executive as Vice President of Engineering. The Executive shall report directly to the Chief Technology Officer and devote full business time and best efforts to the performance of duties.", body_style))

    story.append(Paragraph("<b>SECTION 2: REMUNERATION AND BENEFITS</b>", section_heading))
    story.append(Paragraph("2.1 The Company shall pay the Executive an aggregate annual cost-to-company (CTC) of INR 36,00,000 (Rupees Thirty-Six Lakhs only), payable in monthly installments subject to statutory tax deductions at source (TDS).", body_style))
    story.append(Paragraph("2.2 The Executive shall be entitled to performance incentives, comprehensive medical insurance, and 24 days paid annual leave.", body_style))

    story.append(Paragraph("<b>SECTION 3: TERMINATION AND NOTICE PERIOD</b>", section_heading))
    story.append(Paragraph("3.1 <b>Termination for Convenience:</b> Either party may terminate this Agreement at any time by providing not less than thirty (30) days prior written notice to the other party.", body_style))
    story.append(Paragraph("3.2 <b>Payment in Lieu of Notice:</b> The Company reserves the right, at its sole discretion, to terminate employment immediately upon tendering thirty (30) days basic salary in lieu of serving the notice period.", body_style))
    story.append(Paragraph("3.3 <b>Summary Termination:</b> The Company may terminate employment immediately without notice or severance in the event of gross misconduct, fraud, criminal conviction, or material breach of company policy.", body_style))

    story.append(Paragraph("<b>SECTION 4: NON-COMPETE RESTRICTION & POST-TERMINATION RESTRAINTS</b>", section_heading))
    story.append(Paragraph("4.1 <b>Non-Compete Covenant:</b> The Executive expressly covenants and agrees that for a period of twenty-four (24) months following termination of employment for any reason whatsoever, the Executive shall not directly or indirectly engage in, manage, operate, consult for, or establish any commercial venture competing with the Company within the territory of India.", body_style))
    story.append(Paragraph("4.2 <b>Non-Solicitation:</b> For a period of twelve (12) months following termination, the Executive shall not solicit, recruit, or entice away any employee, client, or vendor of the Company.", body_style))

    story.append(Paragraph("<b>SECTION 5: CONFIDENTIALITY AND INTELLECTUAL PROPERTY</b>", section_heading))
    story.append(Paragraph("5.1 All proprietary algorithms, customer lists, financial data, and code created during the term of employment shall constitute work-for-hire and remain the sole exclusive property of the Company.", body_style))
    story.append(Paragraph("5.2 The Executive's confidentiality obligations shall survive termination of employment for a period of three (3) years.", body_style))

    story.append(Paragraph("<b>SECTION 6: DISPUTE RESOLUTION AND GOVERNING LAW</b>", section_heading))
    story.append(Paragraph("6.1 This Agreement shall be governed by and construed in accordance with the substantive laws of the Republic of India.", body_style))
    story.append(Paragraph("6.2 Any dispute arising out of or in connection with this Agreement shall be referred to arbitration by a sole arbitrator in Bengaluru, in accordance with the Arbitration and Conciliation Act, 1996. The language of arbitration shall be English.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("IN WITNESS WHEREOF, the parties have executed this Executive Employment Agreement on the day and year first written above.", disclaimer_style))

    doc.build(story)
    print(f"Created: {path}")


def create_lease_agreement():
    path = OUTPUT_DIR / "Commercial_Lease_Agreement_Mumbai.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("COMMERCIAL LEASE AND LICENSE AGREEMENT", title_style))
    story.append(Paragraph("Executed at Mumbai, Maharashtra, India on 1st November 2024", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    story.append(Paragraph("<b>PARTIES:</b>", section_heading))
    story.append(Paragraph("1. <b>PREMIER REALTY HOLDINGS LIMITED</b>, having its registered office at Nariman Point, Mumbai - 400021 (the <i>'Lessor'</i>); and", body_style))
    story.append(Paragraph("2. <b>ZENITH DATA ANALYTICS INDIA PRIVATE LIMITED</b>, having its principal office at Bandra Kurla Complex, Mumbai - 400051 (the <i>'Lessee'</i>).", body_style))

    story.append(Paragraph("<b>CLAUSE 1: DEMISED PREMISES AND USE</b>", section_heading))
    story.append(Paragraph("1.1 The Lessor hereby demises unto the Lessee commercial office premises situated at Unit 402, 4th Floor, Platinum Trade Tower, Bandra Kurla Complex (BKC), Mumbai - 400051, admeasuring approximately 3,200 square feet carpet area.", body_style))
    story.append(Paragraph("1.2 The Demised Premises shall be utilized strictly for lawful commercial IT and consultancy operations.", body_style))

    story.append(Paragraph("<b>CLAUSE 2: LEASE TERM AND MANDATORY LOCK-IN PERIOD</b>", section_heading))
    story.append(Paragraph("2.1 The lease shall be for a term of thirty-six (36) months commencing 1st December 2024.", body_style))
    story.append(Paragraph("2.2 <b>Lock-in Period:</b> Both the Lessor and the Lessee agree to a mandatory lock-in period of twelve (12) months. Neither party shall be entitled to terminate this Lease without cause during the Lock-in Period. In the event the Lessee vacates the premises prior to expiry of the Lock-in Period, the Lessee shall remain liable to pay rent for the unexpired portion of the Lock-in Period.", body_style))

    story.append(Paragraph("<b>CLAUSE 3: RENT, ESCALATION, AND MAINTENANCE</b>", section_heading))
    story.append(Paragraph("3.1 The monthly rent for the Demised Premises shall be INR 2,50,000 (Rupees Two Lakhs Fifty Thousand only), payable on or before the 5th day of each English calendar month in advance.", body_style))
    story.append(Paragraph("3.2 The monthly rent shall escalate by five percent (5%) compound annually upon the completion of every 12 months.", body_style))

    story.append(Paragraph("<b>CLAUSE 4: INTEREST-FREE REFUNDABLE SECURITY DEPOSIT</b>", section_heading))
    story.append(Paragraph("4.1 The Lessee has deposited with the Lessor an interest-free refundable security deposit of INR 15,00,000 (Rupees Fifteen Lakhs only), equivalent to six (6) months rent.", body_style))
    story.append(Paragraph("4.2 The Lessor covenants to refund the entire security deposit within fifteen (15) days of the Lessee peacefully handing over vacant possession of the premises, subject only to legitimate deductions for unpaid utility charges or physical damage.", body_style))

    story.append(Paragraph("<b>CLAUSE 5: TERMINATION AND CURE NOTICE</b>", section_heading))
    story.append(Paragraph("5.1 Following expiry of the 12-month Lock-in Period, either party may terminate this Lease by providing sixty (60) days prior written notice.", body_style))
    story.append(Paragraph("5.2 In case of default in payment of rent exceeding fifteen (15) days, the Lessor shall issue a 15-day Cure Notice. If the breach remains uncured, the Lessor shall be entitled to terminate the Lease and re-enter premises.", body_style))

    story.append(Paragraph("<b>CLAUSE 6: JURISDICTION</b>", section_heading))
    story.append(Paragraph("6.1 This Lease shall be governed by the laws of India and the courts of Mumbai, Maharashtra shall have exclusive jurisdiction.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("REGISTERED AND EXECUTED BY AUTHORIZED SIGNATORIES OF LESSOR AND LESSEE.", disclaimer_style))

    doc.build(story)
    print(f"Created: {path}")


def create_nda_agreement():
    path = OUTPUT_DIR / "Mutual_Non_Disclosure_Agreement.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("MUTUAL NON-DISCLOSURE AND PROPRIETARY INFORMATION AGREEMENT", title_style))
    story.append(Paragraph("Effective as of 20th November 2024 between the Disclosing and Receiving Parties", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    story.append(Paragraph("<b>1. PURPOSE:</b>", section_heading))
    story.append(Paragraph("The parties wish to explore a potential strategic technology collaboration regarding cross-border payment gateway integrations. In connection with this purpose, each party may disclose valuable proprietary and confidential information.", body_style))

    story.append(Paragraph("<b>2. DEFINITION OF CONFIDENTIAL INFORMATION:</b>", section_heading))
    story.append(Paragraph("'Confidential Information' includes all non-public technical, commercial, financial, customer, source code, and design information disclosed orally, visually, or in tangible form marked 'Confidential' or that reasonably ought to be understood as confidential.", body_style))

    story.append(Paragraph("<b>3. EXCLUSIONS FROM CONFIDENTIALITY:</b>", section_heading))
    story.append(Paragraph("Confidential Information does not include information that: (a) is or becomes publicly known through no breach of this Agreement; (b) was already in the receiving party's possession prior to disclosure; (c) is independently developed without reference to the disclosed information; or (d) is required to be disclosed pursuant to judicial decree or statutory authority, provided prompt written notice is given.", body_style))

    story.append(Paragraph("<b>4. CONFIDENTIALITY DUTIES AND RESTRICTIONS:</b>", section_heading))
    story.append(Paragraph("4.1 Each receiving party agrees to hold the disclosing party's confidential data in strict confidence, applying at least a reasonable standard of care.", body_style))
    story.append(Paragraph("4.2 Neither party shall disclose information to any third party except to its officers, legal counsel, and engineers who have a need-to-know and are bound by written non-disclosure obligations no less restrictive than this Agreement.", body_style))

    story.append(Paragraph("<b>5. RETURN OR DESTRUCTION OF CONFIDENTIAL MATERIALS:</b>", section_heading))
    story.append(Paragraph("5.1 <b>Mandatory Return Timeline:</b> Within seven (7) business days of receiving a written request from the Disclosing Party, the Receiving Party shall return or destroy all physical documents, electronic files, recordings, and backups containing Confidential Information.", body_style))
    story.append(Paragraph("5.2 An authorized officer of the Receiving Party shall certify in writing that all materials have been destroyed or returned within the 7-day period.", body_style))

    story.append(Paragraph("<b>6. TERM AND SURVIVAL:</b>", section_heading))
    story.append(Paragraph("This Agreement shall remain in effect for two (2) years from the Effective Date. The confidentiality and non-use obligations shall survive for a period of five (5) years following the termination or expiration of this Agreement.", body_style))

    story.append(Paragraph("<b>7. GOVERNING LAW AND VENUE:</b>", section_heading))
    story.append(Paragraph("This Agreement shall be governed by the laws of India. Any legal dispute shall be instituted exclusively in the competent civil courts of New Delhi.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("EXECUTED BY AUTHORIZED SIGNATORIES OF BOTH PARTIES.", disclaimer_style))

    doc.build(story)
    print(f"Created: {path}")


def create_services_contract():
    path = OUTPUT_DIR / "Master_Software_Services_Contract.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("MASTER SOFTWARE SERVICES & CLOUD SLA AGREEMENT", title_style))
    story.append(Paragraph("Governing Enterprise Cloud Deployment and SaaS Operations", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    story.append(Paragraph("<b>SECTION 1: SCOPE OF SERVICES AND SOWs</b>", section_heading))
    story.append(Paragraph("1.1 The Vendor agrees to deliver cloud enterprise architecture, API integration, and automated monitoring services as specified in Statements of Work (SOWs) executed from time to time.", body_style))

    story.append(Paragraph("<b>SECTION 2: SERVICE LEVEL AGREEMENT (SLA) & UPTIME GUARANTEE</b>", section_heading))
    story.append(Paragraph("2.1 <b>Uptime Target:</b> The Vendor guarantees a monthly Service Availability of not less than 99.9% uptime (excluding scheduled maintenance).", body_style))
    story.append(Paragraph("2.2 <b>Service Credits:</b> If monthly availability falls below 99.9%, the Client shall be entitled to a 10% credit against monthly fees. If availability falls below 99.0%, the Client shall receive a 25% credit and retain the right to terminate for material default.", body_style))

    story.append(Paragraph("<b>SECTION 3: INVOICING AND PAYMENT TERMS</b>", section_heading))
    story.append(Paragraph("3.1 Invoices shall be raised monthly. Client shall pay all undisputed invoice amounts within thirty (30) days of receipt.", body_style))
    story.append(Paragraph("3.2 Overdue payments shall accrue interest at 1% per month following a 7-day written reminder.", body_style))

    story.append(Paragraph("<b>SECTION 4: LIMITATION OF LIABILITY</b>", section_heading))
    story.append(Paragraph("4.1 <b>Aggregate Cap:</b> Except for breaches of confidentiality or gross negligence, neither party's cumulative liability under this Agreement shall exceed the total service fees actually paid by the Client in the twelve (12) months preceding the incident.", body_style))
    story.append(Paragraph("4.2 <b>Consequential Damages:</b> Neither party shall be liable for indirect, incidental, punitive, or loss of profits damages.", body_style))

    story.append(Paragraph("<b>SECTION 5: ANNUAL AUDIT RIGHTS</b>", section_heading))
    story.append(Paragraph("5.1 Client or its certified independent auditor may inspect Vendor's security controls, ISO-27001 certifications, and data handling procedures once per calendar year upon fourteen (14) days prior written notice.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("IN WITNESS WHEREOF, THE PARTIES HAVE DULY EXECUTED THIS MASTER AGREEMENT.", disclaimer_style))

    doc.build(story)
    print(f"Created: {path}")


def create_legal_notice():
    path = OUTPUT_DIR / "Consumer_Dispute_Legal_Notice.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    story = []

    story.append(Paragraph("ADVOCATE'S FORMAL STATUTORY LEGAL NOTICE", title_style))
    story.append(Paragraph("Issued under Section 35 of the Consumer Protection Act, 2019", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    story.append(Paragraph("<b>FROM:</b>", section_heading))
    story.append(Paragraph("Advocate Rajesh K. Varma, High Court of Bombay<br/>Chambers: 412, Lawyers Chambers, Fort, Mumbai - 400001", body_style))

    story.append(Paragraph("<b>TO:</b>", section_heading))
    story.append(Paragraph("Global FastTrack Logistics India Private Limited<br/>Registered Office: Andheri East, Mumbai - 400069", body_style))

    story.append(Paragraph("<b>SUBJECT MATTER & FACTS:</b>", section_heading))
    story.append(Paragraph("Under instructions from my client, Mr. Vivek Sen, residing at Juhu, Mumbai, I hereby issue this statutory legal notice to address your gross deficiency in service and unfair trade practices under the Consumer Protection Act, 2019.", body_style))
    story.append(Paragraph("On 5th September 2024, my client entrusted your courier service with a consignment of high-precision scientific testing equipment (Waybill #GFT-994821) valued at INR 4,80,000, destined for delivery to Bengaluru.", body_style))
    story.append(Paragraph("Notwithstanding the express payment of priority transit insurance, your personnel failed to deliver the consignment and subsequently declared the entire package lost due to negligent custody.", body_style))

    story.append(Paragraph("<b>STATUTORY DEMAND AND 15-DAY CURE PERIOD:</b>", section_heading))
    story.append(Paragraph("1. You are hereby called upon to pay my client the sum of <b>INR 4,80,000</b> towards the full declared value of the lost consignment, together with interest at 12% per annum from 5th September 2024 until payment.", body_style))
    story.append(Paragraph("2. You are further called upon to pay <b>INR 1,00,000</b> towards compensation for severe mental agony, business dislocation, and legal expenses.", body_style))
    story.append(Paragraph("3. <b>Fifteen (15) Days Notice:</b> You are required to remit the total sum of INR 5,80,000 within fifteen (15) days of receipt of this notice.", body_style))

    story.append(Paragraph("<b>NOTICE OF INTENDED LITIGATION:</b>", section_heading))
    story.append(Paragraph("Please note that should you fail or neglect to comply with the demands within the stipulated 15-day period, my client has given peremptory instructions to institute consumer complaint proceedings against your company before the District Consumer Disputes Redressal Commission, Mumbai, at your entire risk as to costs and consequences.", body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("ADVOCATE FOR COMPLAINANT — RAJESH K. VARMA, ADVOCATE", disclaimer_style))

    doc.build(story)
    print(f"Created: {path}")


if __name__ == "__main__":
    print(f"Generating sample PDFs in: {OUTPUT_DIR}")
    create_employment_agreement()
    create_lease_agreement()
    create_nda_agreement()
    create_services_contract()
    create_legal_notice()
    print("All sample PDFs successfully generated!")
