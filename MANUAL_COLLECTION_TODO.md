# LegalLens — Manual Collection TODO

Items that could not be collected automatically are listed below.
Follow the instructions for each item to download and import manually.



## eCourts — Manual Collection Required

**Source:** services.ecourts.gov.in  
**Reason not automated:** Mandatory image CAPTCHA on every query; PHP session binding; IP banning.  
**Status:** MANUAL IMPORT ONLY

### Recommended Authorized Alternatives

| Source | URL | Format | Notes |
|--------|-----|--------|-------|
| DevDataLab / AWS Open Data (District Courts 2010-2018) | https://registry.opendata.aws/devdatalab-india-courts/ | CSV/Parquet | ~1TB, 81M+ cases |
| OpenNyAI Corpus (Hugging Face) | https://huggingface.co/opennyaiorg | JSONL/CSV | AI-ready NLP datasets |

### How to Import Manually

1. Download a subset from one of the authorized sources above.
2. Use the manual import utility:

```bash
python import_manual.py path/to/downloaded_file.csv \
  --source ecourts \
  --doc-type judgment \
  --domain "Criminal Law" \
  --title "District Court Judgments 2010-2018" \
  --url "https://registry.opendata.aws/devdatalab-india-courts/"
```

3. The pipeline will hash, classify, and add the file to the catalogue automatically.

### What NOT to Do

- Do NOT use third-party CAPTCHA-solving services to scrape eCourts
- Do NOT purchase/use automated browser sessions against eCourts
- Do NOT attempt to bypass PHP session validation

