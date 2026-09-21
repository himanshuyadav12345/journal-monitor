# Journal Monitor

Metadata-only monitoring of 79 academic journals.

## Scope
- New issues
- Online-first / advance articles where publisher metadata exposes them
- DOI/URL/title-date deduplication
- Crossref fallback
- No PDFs, full text, or abstracts

EPW and Social Scientist are deferred.

## Run
```bash
pip install -r requirements.txt
python -m monitor.main
```

GitHub Actions runs daily and can also be triggered manually from Actions → Journal Monitor → Run workflow.

Edit `config/journals.json` to add/remove journals. Set `enabled: false` to pause a journal without deleting its configuration.
