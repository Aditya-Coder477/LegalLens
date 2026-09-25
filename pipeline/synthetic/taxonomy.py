"""
pipeline/synthetic/taxonomy.py
==============================
Fictional entities, courts, ministries, domains, and templates for synthetic generation.
Guarantees NO real entities, real courts, real case numbers, or real Acts are used.
"""

from __future__ import annotations

from pipeline.core.metadata import LegalDomain

# Fictional courts (all explicitly marked Synthetic)
SYNTHETIC_COURTS = [
    "High Court of Dakshin Pradesh (Synthetic)",
    "High Court of Uttaraanchal (Synthetic)",
    "High Court of Paschim Rashtra (Synthetic)",
    "High Court of Purvanchal (Synthetic)",
    "National Commercial Appellate Tribunal of Bharat (Synthetic)",
    "Appellate Tribunal for Digital Commerce (Synthetic)",
    "Environmental Redressal Tribunal of Dakshin Pradesh (Synthetic)",
]

# Fictional Government Ministries and Authorities
SYNTHETIC_MINISTRIES = [
    "Ministry of Digital Economy and Innovation (Synthetic)",
    "Ministry of Clean Energy and Climate Transition (Synthetic)",
    "Ministry of Citizen Welfare and Legal Services (Synthetic)",
    "Ministry of Commerce and Fair Competition (Synthetic)",
    "Ministry of Health Technologies and Biosecurity (Synthetic)",
    "Ministry of Urban Infrastructure and Transport (Synthetic)",
    "Department of Consumer Empowerment (Synthetic)",
    "Department of Telecommunications and Cyber Infrastructure (Synthetic)",
]

SYNTHETIC_AUTHORITIES = [
    "Digital Services Regulatory Authority of Bharat (Synthetic)",
    "National Fair Lending and Credit Commission (Synthetic)",
    "National Clean Energy Grid Council (Synthetic)",
    "Medical Devices Quality and Traceability Board (Synthetic)",
    "Dakshin Pradesh Legal Aid and Literacy Authority (Synthetic)",
    "Central Cybersecurity Emergency Coordination Cell (Synthetic)",
    "Consumer Protection and Redressal Council (Synthetic)",
    "National Electronic Toll and Highway Safety Directorate (Synthetic)",
]

# Fictional Corporate Entities
SYNTHETIC_COMPANIES = [
    "Aarav Technologies Pvt. Ltd. (Synthetic)",
    "Bhoomi Infrastructure & Logistics LLP (Synthetic)",
    "Neelam Cloud Services India Ltd. (Synthetic)",
    "Veda Data Analytics Pvt. Ltd. (Synthetic)",
    "Daksha Renewable Energy Solutions Ltd. (Synthetic)",
    "Kaveri Healthtech Innovations Pvt. Ltd. (Synthetic)",
    "Suraksha Cybersecurity Systems LLP (Synthetic)",
    "Pavan Logistics & Freight Corp. (Synthetic)",
    "Chaitanya Consumer Goods Ltd. (Synthetic)",
    "Pratham Software Solutions Pvt. Ltd. (Synthetic)",
    "Vistara Retail Enterprises LLP (Synthetic)",
    "Zenith FinTech Services Pvt. Ltd. (Synthetic)",
    "Samarth Engineering Consultants Pvt. Ltd. (Synthetic)",
    "Mitra Digital Payment Solutions Ltd. (Synthetic)",
]

# Fictional Jurisdictions
SYNTHETIC_JURISDICTIONS = [
    "Union of Bharat (Synthetic)",
    "State of Dakshin Pradesh (Synthetic)",
    "State of Uttaraanchal (Synthetic)",
    "State of Paschim Rashtra (Synthetic)",
    "State of Purvanchal (Synthetic)",
]

# Map of core legal domains to generate content across
CORE_SYNTHETIC_DOMAINS = [
    LegalDomain.CONSTITUTIONAL_LAW.value,
    LegalDomain.CRIMINAL_LAW.value,
    LegalDomain.CIVIL_PROCEDURE.value,
    LegalDomain.CONTRACT_LAW.value,
    LegalDomain.COMMERCIAL_CORPORATE.value,
    LegalDomain.EMPLOYMENT_LABOUR.value,
    LegalDomain.CONSUMER_LAW.value,
    LegalDomain.INTELLECTUAL_PROPERTY.value,
    LegalDomain.IT_CYBER_LAW.value,
    LegalDomain.DATA_PROTECTION_PRIVACY.value,
    LegalDomain.ARBITRATION_ADR.value,
    LegalDomain.ENVIRONMENTAL_LAW.value,
    LegalDomain.PROPERTY_REAL_ESTATE.value,
    LegalDomain.FAMILY_LAW.value,
    LegalDomain.TAX_LAW.value,
    LegalDomain.BANKING_FINANCIAL.value,
    LegalDomain.INSOLVENCY_BANKRUPTCY.value,
    LegalDomain.COMPETITION_LAW.value,
    LegalDomain.ADMINISTRATIVE_LAW.value,
    LegalDomain.HUMAN_RIGHTS.value,
    LegalDomain.EDUCATION_LAW.value,
    LegalDomain.HEALTH_MEDICAL.value,
    LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
    LegalDomain.EMERGING_TECHNOLOGY_AI.value,
    LegalDomain.TELECOMMUNICATIONS.value,
]
