# Build Notes

## Business logic

Zoom's core commercial fit is MEP/mechanical/infrastructure. It commonly operates as subcontractor/JV partner. Therefore LGA searches for both:

1. DIRECT — buyer is procuring work Zoom could perform.
2. INDIRECT — project/main-contractor signal indicates a plausible subcontracting or specialist-package opportunity.

## Scoring

The final 1–5 score is calculated by application code from six weighted criteria. The LLM cannot directly assign the final score.

## Evidence

Each lead retains source URL, source name, extracted facts and confidence. The system should never fabricate a project value. Values should be labeled OFFICIAL, CONVERTED, ESTIMATED, or UNKNOWN.

## Next iteration

- Source-specific Etimad adapter
- Forsah adapter
- NHC procurement adapter
- TenderSA adapter
- Project-award intelligence sources
- persistent PostgreSQL storage
- golden dataset
- feedback capture
- daily scheduled execution
- production email provider
