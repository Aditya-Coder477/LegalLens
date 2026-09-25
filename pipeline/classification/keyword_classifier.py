"""
pipeline/classification/keyword_classifier.py
==============================================
Deterministic keyword/metadata-based legal domain classifier.
Covers all 50 legal domains defined in LegalDomain enum.

Classification pipeline:
  1. Check act title against exact known-act patterns (highest confidence)
  2. Match ministry/department metadata
  3. Match keywords in title + subject text
  4. Return (primary_domain, secondary_domains, confidence, "keyword")

Confidence scoring:
  - Exact title match: 0.95
  - Ministry match: 0.85
  - Multiple keyword matches: 0.70
  - Single keyword match: 0.50
  - No match: (UNCLASSIFIED, 0.0)

Rules:
  - Never modifies source text
  - Deterministic: same input always → same output
  - No external API calls
"""

from __future__ import annotations

import re
from typing import Optional

from pipeline.core.metadata import LegalDomain


# ──────────────────────────────────────────────
# Domain keyword dictionaries
# ──────────────────────────────────────────────

# Each domain maps to a tuple of (keywords_list, ministry_hints_list)
# Keywords are matched case-insensitively against: title + subject + act_number text
DOMAIN_KEYWORDS: dict[str, tuple[list[str], list[str]]] = {
    LegalDomain.CONSTITUTIONAL_LAW.value: (
        ["constitution", "constitutional", "fundamental rights", "directive principles",
         "parliament", "legislature", "union", "rajya sabha", "lok sabha",
         "president of india", "governor", "supreme court constitution",
         "constitutional amendment", "article 370", "article 21", "citizenship amendment"],
        ["ministry of law", "legislative department"],
    ),
    LegalDomain.CONTRACT_LAW.value: (
        ["contract", "agreement", "consideration", "offer and acceptance",
         "breach of contract", "specific relief", "performance of contract",
         "indemnity", "guarantee", "bailment", "pledge", "agency"],
        ["ministry of law"],
    ),
    LegalDomain.COMMERCIAL_CORPORATE.value: (
        ["companies act", "company", "corporate", "corporation", "director",
         "shareholder", "memorandum of association", "articles of association",
         "limited liability", "partnership", "llp", "merger", "acquisition",
         "takeover", "sebi", "stock exchange", "registered company",
         "board of directors", "statutory audit", "mca"],
        ["ministry of corporate affairs", "mca"],
    ),
    LegalDomain.EMPLOYMENT_LABOUR.value: (
        ["labour", "labor", "employment", "worker", "workman", "trade union",
         "industrial dispute", "factory", "wages", "minimum wages", "esi",
         "epf", "provident fund", "gratuity", "maternity", "bonus",
         "shops and establishment", "contract labour", "industrial employment",
         "occupational safety", "code on wages", "labour code"],
        ["ministry of labour", "labour ministry"],
    ),
    LegalDomain.CONSUMER_LAW.value: (
        ["consumer", "consumer protection", "consumer forum", "deficiency in service",
         "unfair trade practice", "national consumer", "district consumer",
         "consumer disputes", "product liability", "e-commerce consumer",
         "consumer commission"],
        ["ministry of consumer affairs", "consumer affairs"],
    ),
    LegalDomain.CRIMINAL_LAW.value: (
        ["criminal", "crime", "offence", "offense", "ipc", "indian penal code",
         "bharatiya nyaya sanhita", "bns", "crpc", "bnss", "criminal procedure",
         "arrest", "bail", "cognizable", "non-cognizable", "murder", "theft",
         "fraud", "cheating", "forgery", "dacoity", "rape", "pocso",
         "prevention of corruption", "ndps", "narcotic", "terrorism", "uapa"],
        ["ministry of home affairs", "home ministry"],
    ),
    LegalDomain.CIVIL_PROCEDURE.value: (
        ["civil procedure", "code of civil procedure", "cpc", "decree", "suit",
         "plaint", "summons", "execution", "appeal civil", "civil court",
         "limitation act", "pecuniary jurisdiction", "civil jurisdiction",
         "order and rule", "injunction", "stay"],
        ["ministry of law"],
    ),
    LegalDomain.PROPERTY_REAL_ESTATE.value: (
        ["transfer of property", "property", "real estate", "rera", "land",
         "immovable property", "mortgage", "lease", "easement", "sale deed",
         "registration of property", "stamp duty", "benami", "land acquisition",
         "urban land ceiling", "apartment", "builder", "developer",
         "housing society", "condominium"],
        ["ministry of housing", "ministry of urban"],
    ),
    LegalDomain.FAMILY_LAW.value: (
        ["family", "marriage", "divorce", "matrimonial", "hindu marriage",
         "muslim marriage", "special marriage", "maintenance", "alimony",
         "custody", "guardianship", "adoption", "succession", "inheritance",
         "personal law", "hindu succession", "hindu adoption",
         "muslim women", "christian marriage", "dowry prohibition"],
        ["ministry of women", "ministry of law"],
    ),
    LegalDomain.INTELLECTUAL_PROPERTY.value: (
        ["intellectual property", "patent", "trademark", "copyright",
         "industrial design", "geographical indication", "trade secret",
         "ipr", "ip", "plant variety", "semiconductor", "layout design",
         "passing off", "infringement"],
        ["ministry of commerce", "dpiit", "department for promotion of industry"],
    ),
    LegalDomain.IT_CYBER_LAW.value: (
        ["information technology", "it act", "cyber", "cybercrime", "hacking",
         "electronic signature", "digital signature", "intermediary",
         "computer", "network", "internet", "online platform", "social media",
         "content moderation", "cert-in", "section 69", "section 79",
         "cyber security", "information security", "electronic record"],
        ["meity", "ministry of electronics", "ministry of it"],
    ),
    LegalDomain.DATA_PROTECTION_PRIVACY.value: (
        ["data protection", "personal data", "privacy", "dpdp", "dpdpa",
         "data privacy", "data breach", "data fiduciary", "consent manager",
         "data principal", "data processor", "right to be forgotten",
         "data localisation", "dpb", "data protection board",
         "digital personal data"],
        ["meity", "ministry of electronics"],
    ),
    LegalDomain.TAX_LAW.value: (
        ["tax", "income tax", "gst", "goods and services tax", "vat",
         "customs", "excise", "direct tax", "indirect tax", "tds",
         "advance tax", "tax deduction", "income tax act", "wealth tax",
         "service tax", "central excise", "customs act", "finance act",
         "taxation", "tax evasion", "benami transaction"],
        ["ministry of finance", "cbdt", "cbic", "revenue department"],
    ),
    LegalDomain.BANKING_FINANCIAL.value: (
        ["banking", "bank", "rbi", "reserve bank", "nbfc", "non-banking",
         "financial institution", "credit", "loan", "mortgage",
         "banking regulation", "payment", "financial services",
         "financial stability", "microfinance", "cooperative bank",
         "banking ombudsman", "sarfaesi", "debt recovery tribunal",
         "drt", "ibc banking"],
        ["ministry of finance", "rbi", "department of financial services"],
    ),
    LegalDomain.INSURANCE_LAW.value: (
        ["insurance", "life insurance", "general insurance", "irda", "irdai",
         "policyholder", "premium", "claim settlement", "reinsurance",
         "insurance ombudsman", "insurance regulatory", "insurance act"],
        ["irdai", "ministry of finance insurance"],
    ),
    LegalDomain.ARBITRATION_ADR.value: (
        ["arbitration", "conciliation", "mediation", "lok adalat",
         "adr", "alternative dispute resolution", "arbitral tribunal",
         "arbitral award", "enforcement of award", "domestic arbitration",
         "international arbitration", "institutional arbitration",
         "nalsa", "legal services authority"],
        ["ministry of law", "nalsa"],
    ),
    LegalDomain.ENVIRONMENTAL_LAW.value: (
        ["environment", "environmental", "pollution", "air pollution",
         "water pollution", "noise pollution", "hazardous waste",
         "forest", "wildlife", "biodiversity", "coastal regulation",
         "environment protection", "environment impact assessment", "eia",
         "climate change", "carbon", "national green tribunal", "ngt",
         "ozone depletion", "e-waste"],
        ["ministry of environment", "moefcc"],
    ),
    LegalDomain.LAND_PROPERTY.value: (
        ["land", "land revenue", "land records", "cadastral", "mutation",
         "land reform", "ceiling on land", "tenancy", "land acquisition",
         "rehabilitation resettlement", "rfctlarr", "urban land",
         "agricultural land ceiling", "land use change", "revenue court"],
        ["ministry of rural development", "land resources"],
    ),
    LegalDomain.ADMINISTRATIVE_LAW.value: (
        ["administrative", "public administration", "rule of law",
         "writ petition", "mandamus", "certiorari", "prohibition",
         "quo warranto", "natural justice", "administrative tribunal",
         "cat", "central administrative tribunal", "delegated legislation",
         "public authority", "rti", "right to information"],
        ["ministry of personnel", "dopt"],
    ),
    LegalDomain.PUBLIC_FINANCIAL_GRIEVANCE.value: (
        ["grievance", "complaint", "ombudsman", "redressal", "lokpal",
         "lokayukta", "vigilance", "anti-corruption", "whistleblower",
         "public interest", "public accounts", "cag", "comptroller",
         "auditor general", "public expenditure", "fiscal responsibility",
         "frbm", "government accountability"],
        ["ministry of finance", "cvc", "lokpal"],
    ),
    # ── Secondary domains ─────────────────────
    LegalDomain.INSOLVENCY_BANKRUPTCY.value: (
        ["insolvency", "bankruptcy", "ibc", "insolvency and bankruptcy code",
         "nclt", "nclat", "liquidation", "corporate insolvency",
         "resolution professional", "committee of creditors", "moratorium",
         "personal insolvency", "fresh start process"],
        ["ministry of corporate affairs", "ibbi"],
    ),
    LegalDomain.SECURITIES_CAPITAL_MARKETS.value: (
        ["securities", "stock market", "sebi", "capital markets",
         "insider trading", "listing obligations", "takeover code",
         "mutual fund", "debenture", "bonds", "depository",
         "securities exchange", "ipo", "fpo", "offer for sale",
         "securities fraud", "market manipulation"],
        ["sebi", "ministry of finance"],
    ),
    LegalDomain.COMPETITION_LAW.value: (
        ["competition", "anti-competitive", "cartel", "abuse of dominance",
         "combination", "merger control", "competition commission",
         "cci", "monopoly", "price fixing", "market power"],
        ["cci", "ministry of corporate affairs"],
    ),
    LegalDomain.TELECOMMUNICATIONS.value: (
        ["telecom", "telecommunications", "trai", "spectrum", "licence",
         "internet service provider", "isp", "broadband", "mobile",
         "telegraph", "wireless", "telecom regulatory", "dot",
         "unified licence", "telecom policy"],
        ["dot", "trai", "ministry of communications"],
    ),
    LegalDomain.MEDIA_ENTERTAINMENT.value: (
        ["media", "press", "newspaper", "cinematograph", "film", "television",
         "broadcast", "cable television", "ott platform", "streaming",
         "content regulation", "censor", "certification", "information and broadcasting",
         "prasar bharati", "radio", "advertisement standards"],
        ["ministry of information and broadcasting", "i&b ministry"],
    ),
    LegalDomain.EDUCATION_LAW.value: (
        ["education", "school", "university", "higher education", "ugc",
         "aicte", "medical education", "right to education", "rte",
         "coaching", "examination", "board of education", "university act",
         "deemed university", "ner", "nep"],
        ["ministry of education", "ugc", "aicte"],
    ),
    LegalDomain.HEALTH_MEDICAL.value: (
        ["health", "medical", "hospital", "healthcare", "nmc",
         "medical council", "clinical establishment", "public health",
         "epidemic", "quarantine", "mental health", "ayushman bharat",
         "nhm", "national health mission", "health policy"],
        ["ministry of health", "ayush"],
    ),
    LegalDomain.PHARMACEUTICAL.value: (
        ["drug", "pharmaceutical", "medicine", "narcotic drug",
         "pharmacy", "drug regulation", "cdsco", "dcgi", "drug controller",
         "clinical trial", "pharmacovigilance", "drug price",
         "essential medicines", "drug and cosmetics"],
        ["cdsco", "ministry of health pharmaceuticals", "national pharmaceutical"],
    ),
    LegalDomain.FOOD_SAFETY.value: (
        ["food", "food safety", "fssai", "food adulteration",
         "food standards", "food business", "food packaging",
         "food labelling", "eating establishment", "restaurant regulation",
         "food import", "food hygiene"],
        ["fssai", "ministry of health food"],
    ),
    LegalDomain.MOTOR_VEHICLE_TRANSPORT.value: (
        ["motor vehicle", "transport", "road", "driving licence",
         "vehicle registration", "road tax", "traffic", "mv act",
         "motor accident", "hit and run", "third party insurance",
         "goods transport", "permit", "passenger vehicle"],
        ["ministry of road transport", "morth"],
    ),
    LegalDomain.AVIATION_LAW.value: (
        ["aviation", "aircraft", "airline", "airport", "dgca",
         "civil aviation", "air transport", "flight", "aerodrome",
         "aai", "airports authority", "air navigation"],
        ["dgca", "ministry of civil aviation"],
    ),
    LegalDomain.MARITIME_LAW.value: (
        ["maritime", "shipping", "ship", "vessel", "port",
         "merchant shipping", "sea carriage", "admiralty", "salvage",
         "bill of lading", "marine insurance", "coastal shipping",
         "inland waterways"],
        ["ministry of ports shipping", "dgshipping"],
    ),
    LegalDomain.ELECTRICITY_ENERGY.value: (
        ["electricity", "power", "energy", "cerc", "serc",
         "electricity act", "power purchase", "tariff", "distribution",
         "transmission", "generation", "renewable energy", "solar",
         "wind", "hydropower", "nuclear energy", "coal",
         "petroleum", "natural gas"],
        ["cerc", "ministry of power", "mnre"],
    ),
    LegalDomain.MINING_NATURAL_RESOURCES.value: (
        ["mining", "mine", "mineral", "mineral rights", "lease",
         "coal mine", "minor mineral", "quarry", "mmdr act",
         "national mineral policy", "offshore mining",
         "deep sea mining"],
        ["ministry of mines", "coal ministry"],
    ),
    LegalDomain.AGRICULTURAL_LAW.value: (
        ["agriculture", "farm", "farmer", "crop", "agrarian",
         "land ceiling agriculture", "apmc", "agricultural produce",
         "irrigation", "seed", "fertiliser", "pesticide",
         "pm fasal bima", "msp", "minimum support price",
         "farmer distress", "agricultural reform"],
        ["ministry of agriculture", "nafed"],
    ),
    LegalDomain.IMMIGRATION_CITIZENSHIP.value: (
        ["citizenship", "passport", "visa", "immigration", "foreigner",
         "naturalization", "overseas citizen", "oci", "pio",
         "registration of foreigners", "frro", "indian citizen",
         "citizenship amendment"],
        ["ministry of home affairs immigration", "boi"],
    ),
    LegalDomain.ELECTION_ELECTORAL.value: (
        ["election", "electoral", "voter", "constituency", "candidate",
         "election commission", "eci", "model code of conduct",
         "electoral roll", "electronic voting machine", "evm",
         "delimitation", "political party", "election expenditure",
         "pil election", "rpact"],
        ["election commission", "ministry of law elections"],
    ),
    LegalDomain.GOVERNMENT_SERVICE.value: (
        ["civil service", "government servant", "ias", "ips", "ifs",
         "central services", "service rules", "dpc", "promotion",
         "seniority", "transfer posting", "conduct rules",
         "all india service", "departmental inquiry", "suspension",
         "pension service"],
        ["dopt", "ministry of personnel"],
    ),
    LegalDomain.PENSION_SOCIAL_WELFARE.value: (
        ["pension", "retirement", "provident fund", "gratuity pension",
         "nps", "national pension", "epfo", "social security",
         "welfare scheme", "bpl", "below poverty line",
         "social assistance", "old age pension", "widow pension"],
        ["ministry of labour pension", "epfo", "pfrda"],
    ),
    LegalDomain.HUMAN_RIGHTS.value: (
        ["human rights", "nhrc", "shrc", "fundamental rights",
         "right to life", "torture", "cruel treatment",
         "custodial death", "encounter", "violation of rights",
         "human rights commission", "uhrc"],
        ["nhrc", "ministry of law human rights"],
    ),
    LegalDomain.CHILD_RIGHTS.value: (
        ["child", "juvenile", "minor", "pocso", "child labour",
         "child protection", "child marriage", "ncpcr",
         "juvenile justice", "jj act", "adoption child",
         "child welfare", "orphan", "street child"],
        ["ncpcr", "ministry of women child"],
    ),
    LegalDomain.WOMEN_LAW.value: (
        ["women", "woman", "gender", "domestic violence", "sexual harassment",
         "posh act", "dowry", "maternity benefit", "equal remuneration",
         "women empowerment", "protection of women", "sexual assault women"],
        ["ministry of women and child", "ncw"],
    ),
    LegalDomain.DISABILITY_RIGHTS.value: (
        ["disability", "disabled", "person with disability", "pwd",
         "rights of persons with disabilities", "rpwd", "blind",
         "deaf", "mental disability", "cerebral palsy",
         "accessibility", "barrier free", "braille"],
        ["ministry of social justice", "depwd"],
    ),
    LegalDomain.SENIOR_CITIZEN.value: (
        ["senior citizen", "elderly", "old age", "maintenance of parents",
         "senior citizens welfare", "elder abuse"],
        ["ministry of social justice elderly"],
    ),
    LegalDomain.LOCAL_GOVERNMENT_MUNICIPAL.value: (
        ["municipal", "municipality", "town planning", "urban local body",
         "corporation", "city council", "ward", "property tax municipal",
         "building bye-laws", "urban development", "smart city",
         "slum", "urban poor"],
        ["ministry of housing urban affairs"],
    ),
    LegalDomain.PANCHAYATI_RAJ.value: (
        ["panchayat", "panchayati raj", "gram sabha", "gram panchayat",
         "block panchayat", "zila parishad", "rural local body",
         "nyay panchayat", "village court"],
        ["ministry of panchayati raj"],
    ),
    LegalDomain.PUBLIC_PROCUREMENT.value: (
        ["procurement", "tender", "public procurement", "gem",
         "government e-marketplace", "l1", "rfp", "request for proposal",
         "bid", "government contract procurement",
         "general financial rules", "gfr"],
        ["ministry of finance procurement", "gem portal"],
    ),
    LegalDomain.FOREIGN_EXCHANGE_INVESTMENT.value: (
        ["foreign exchange", "fema", "fdi", "foreign direct investment",
         "fii", "portfolio investment", "rbi foreign", "ecb",
         "external commercial borrowing", "nri", "remittance",
         "overseas investment", "fcra", "foreign contribution"],
        ["rbi forex", "ministry of finance fema", "dpiit fdi"],
    ),
    LegalDomain.INTERNATIONAL_TRADE.value: (
        ["import", "export", "customs duty", "anti-dumping", "wto",
         "trade agreement", "fta", "free trade", "dgft",
         "foreign trade policy", "tariff", "non-tariff barrier",
         "safeguard duty", "countervailing duty"],
        ["dgft", "ministry of commerce"],
    ),
    LegalDomain.EMERGING_TECHNOLOGY_AI.value: (
        ["artificial intelligence", "ai regulation", "digital india act",
         "digital regulation", "algorithmic", "machine learning regulation",
         "deepfake", "synthetic media", "automated decision",
         "facial recognition", "digital public infrastructure",
         "account aggregator", "open network", "ondc"],
        ["meity ai", "niti aayog ai"],
    ),
}


# ──────────────────────────────────────────────
# Exact-title patterns for high-confidence matching
# ──────────────────────────────────────────────

EXACT_TITLE_PATTERNS: dict[str, str] = {
    # Maps lowercase title substring → domain value
    "indian penal code": LegalDomain.CRIMINAL_LAW.value,
    "bharatiya nyaya sanhita": LegalDomain.CRIMINAL_LAW.value,
    "code of criminal procedure": LegalDomain.CRIMINAL_LAW.value,
    "bharatiya nagarik suraksha": LegalDomain.CRIMINAL_LAW.value,
    "indian contract act": LegalDomain.CONTRACT_LAW.value,
    "specific relief act": LegalDomain.CONTRACT_LAW.value,
    "companies act": LegalDomain.COMMERCIAL_CORPORATE.value,
    "limited liability partnership": LegalDomain.COMMERCIAL_CORPORATE.value,
    "income tax act": LegalDomain.TAX_LAW.value,
    "goods and services tax": LegalDomain.TAX_LAW.value,
    "customs act": LegalDomain.TAX_LAW.value,
    "information technology act": LegalDomain.IT_CYBER_LAW.value,
    "digital personal data protection": LegalDomain.DATA_PROTECTION_PRIVACY.value,
    "constitution of india": LegalDomain.CONSTITUTIONAL_LAW.value,
    "transfer of property act": LegalDomain.PROPERTY_REAL_ESTATE.value,
    "registration act": LegalDomain.PROPERTY_REAL_ESTATE.value,
    "real estate (regulation": LegalDomain.PROPERTY_REAL_ESTATE.value,
    "consumer protection act": LegalDomain.CONSUMER_LAW.value,
    "motor vehicles act": LegalDomain.MOTOR_VEHICLE_TRANSPORT.value,
    "electricity act": LegalDomain.ELECTRICITY_ENERGY.value,
    "mines and minerals": LegalDomain.MINING_NATURAL_RESOURCES.value,
    "insolvency and bankruptcy code": LegalDomain.INSOLVENCY_BANKRUPTCY.value,
    "arbitration and conciliation": LegalDomain.ARBITRATION_ADR.value,
    "trade marks act": LegalDomain.INTELLECTUAL_PROPERTY.value,
    "patents act": LegalDomain.INTELLECTUAL_PROPERTY.value,
    "copyright act": LegalDomain.INTELLECTUAL_PROPERTY.value,
    "environment protection act": LegalDomain.ENVIRONMENTAL_LAW.value,
    "forest conservation act": LegalDomain.ENVIRONMENTAL_LAW.value,
    "wild life protection": LegalDomain.ENVIRONMENTAL_LAW.value,
    "banking regulation act": LegalDomain.BANKING_FINANCIAL.value,
    "reserve bank of india act": LegalDomain.BANKING_FINANCIAL.value,
    "sarfaesi": LegalDomain.BANKING_FINANCIAL.value,
    "insurance act": LegalDomain.INSURANCE_LAW.value,
    "irdai": LegalDomain.INSURANCE_LAW.value,
    "securities and exchange board": LegalDomain.SECURITIES_CAPITAL_MARKETS.value,
    "prevention of corruption": LegalDomain.CRIMINAL_LAW.value,
    "foreign exchange management": LegalDomain.FOREIGN_EXCHANGE_INVESTMENT.value,
    "foreign contribution": LegalDomain.FOREIGN_EXCHANGE_INVESTMENT.value,
    "food safety and standards": LegalDomain.FOOD_SAFETY.value,
    "drugs and cosmetics": LegalDomain.PHARMACEUTICAL.value,
    "narcotic drugs": LegalDomain.CRIMINAL_LAW.value,
    "right to information": LegalDomain.ADMINISTRATIVE_LAW.value,
    "juvenile justice": LegalDomain.CHILD_RIGHTS.value,
    "pocso": LegalDomain.CHILD_RIGHTS.value,
    "protection of children": LegalDomain.CHILD_RIGHTS.value,
    "maternity benefit": LegalDomain.WOMEN_LAW.value,
    "dowry prohibition": LegalDomain.WOMEN_LAW.value,
    "domestic violence": LegalDomain.WOMEN_LAW.value,
    "sexual harassment of women": LegalDomain.WOMEN_LAW.value,
    "rights of persons with disabilities": LegalDomain.DISABILITY_RIGHTS.value,
    "maintenance and welfare of parents": LegalDomain.SENIOR_CITIZEN.value,
    "citizen": LegalDomain.CONSTITUTIONAL_LAW.value,
    "representation of the people": LegalDomain.ELECTION_ELECTORAL.value,
    "panchayats": LegalDomain.PANCHAYATI_RAJ.value,
    "municipal corporations": LegalDomain.LOCAL_GOVERNMENT_MUNICIPAL.value,
    "competition act": LegalDomain.COMPETITION_LAW.value,
    "telecom": LegalDomain.TELECOMMUNICATIONS.value,
    "cinematograph": LegalDomain.MEDIA_ENTERTAINMENT.value,
    "press and registration": LegalDomain.MEDIA_ENTERTAINMENT.value,
    "right of children to free and compulsory education": LegalDomain.EDUCATION_LAW.value,
    "university grants commission": LegalDomain.EDUCATION_LAW.value,
    "clinical establishments": LegalDomain.HEALTH_MEDICAL.value,
    "mental healthcare": LegalDomain.HEALTH_MEDICAL.value,
    "aviation": LegalDomain.AVIATION_LAW.value,
    "merchant shipping": LegalDomain.MARITIME_LAW.value,
    "land acquisition": LegalDomain.LAND_PROPERTY.value,
    "code on wages": LegalDomain.EMPLOYMENT_LABOUR.value,
    "industrial disputes act": LegalDomain.EMPLOYMENT_LABOUR.value,
    "factories act": LegalDomain.EMPLOYMENT_LABOUR.value,
    "hindu marriage": LegalDomain.FAMILY_LAW.value,
    "special marriage": LegalDomain.FAMILY_LAW.value,
    "hindu succession": LegalDomain.FAMILY_LAW.value,
    "guardian and wards": LegalDomain.FAMILY_LAW.value,
}


# ──────────────────────────────────────────────
# Classifier
# ──────────────────────────────────────────────

def classify(
    title: str,
    subject: str = "",
    ministry: str = "",
    act_number: str = "",
    extra_text: str = "",
) -> tuple[str, list[str], float, str]:
    """
    Classify a document into one of 50 legal domains.

    Args:
        title: Document title.
        subject: Subject/dc.subject metadata.
        ministry: Ministry/department string.
        act_number: Act number (if known).
        extra_text: Additional text snippet (first 500 chars of content).

    Returns:
        (primary_domain, secondary_domains, confidence, method)
        where method = "keyword"
    """
    combined = f"{title} {subject} {ministry} {act_number} {extra_text}".lower()

    # 1. Exact title match (highest confidence)
    title_lower = title.lower()
    for pattern, domain in EXACT_TITLE_PATTERNS.items():
        if pattern in title_lower:
            return domain, [], 0.95, "keyword"

    # 2. Score all domains
    scores: dict[str, float] = {}

    for domain, (keywords, ministry_hints) in DOMAIN_KEYWORDS.items():
        score = 0.0
        # Ministry match
        for hint in ministry_hints:
            if hint in combined:
                score += 0.35
                break
        # Keyword matches with word boundary check
        kw_matches = 0
        for kw in keywords:
            # If multi-word keyword, check substring; if single word, require word boundary
            if " " in kw:
                if kw in combined:
                    kw_matches += 1
            else:
                if re.search(rf"\b{re.escape(kw)}\b", combined):
                    kw_matches += 1

        if kw_matches >= 3:
            score += 0.40
        elif kw_matches == 2:
            score += 0.28
        elif kw_matches == 1:
            score += 0.15
        if score > 0:
            scores[domain] = score

    if not scores:
        return LegalDomain.UNCLASSIFIED.value, [], 0.0, "keyword"

    # Sort by score descending
    sorted_domains = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_domains[0]
    secondary = [d for d, s in sorted_domains[1:] if s >= 0.20][:4]

    confidence = min(primary[1], 0.90)  # cap at 0.90 for keyword method

    return primary[0], secondary, confidence, "keyword"
