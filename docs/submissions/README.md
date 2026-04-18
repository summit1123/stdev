# Submission Source

This directory holds reviewer-facing Markdown source before packaging.

Recommended flow:

1. Write the real content in `proposal.md`.
2. Run `python3 scripts/review_submission_source.py docs/submissions/proposal.md`.
3. Render with `python3 scripts/render_markdown_submission.py`.
4. Run `python3 scripts/review_submission_pdf.py output/pdf/proposal.pdf` only as the final attachment check.
