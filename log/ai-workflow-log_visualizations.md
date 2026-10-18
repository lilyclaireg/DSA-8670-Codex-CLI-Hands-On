# AI Workflow Log: Visualizations

**Date:** 2026-10-18  
**Time:** Not available in the conversation history; exact prompt times are not recorded.

## Entry 17 - Request for visualization plan

- **Date/time:** 2026-10-18; exact time not available in the conversation history.

- **Prompt:** Propose visualizations and wait for approval.
- **Codex produced:** Five options: ranked median-price dot plot, price-versus-quality scatter, price-versus-year-built scatter, price-versus-lot-area scatter, and a neighborhood-rank heatmap.
- **Accepted:** The user said to do all five and asked whether any additional plot was necessary.
- **Modified:** None yet; Codex recommended the five options were sufficient and asked for confirmation before generating them.
- **Rejected:** No additional chart was proposed as necessary.
- **Rationale:** Together, the five views cover prices, all three characteristics, and cross-measure ranks.

## Entry 18 - Choose all five visualizations

- **Date/time:** 2026-10-18; exact time not available in the conversation history.

- **Prompt:** Select all five options and ask whether any other visualization was necessary for the question.
- **Codex produced:** Recommended keeping all five and including sales counts for context; awaited confirmation to generate them.
- **Accepted:** The user confirmed proceeding with all five.
- **Modified:** No additions were requested.
- **Rejected:** None.
- **Rationale:** The set covers price variation and each of the three housing characteristics.

## Entry 19 - Confirm and generate visualizations

- **Date/time:** 2026-10-18; exact time not available in the conversation history.

- **Prompt:** Confirm proceeding with all five visualizations.
- **Codex produced:** `Amos_Housing_visualizations.py` and five SVG images in the requested order. The script ran successfully on 2,930 sales across 28 neighborhoods.
- **Accepted:** The user proceeded to narrative drafting.
- **Modified:** SVG images were used to avoid external plotting dependencies; sales counts were included in the charts where practical, and rank 1 was labeled highest in the heatmap.
- **Rejected:** None.
- **Rationale:** The selected set directly visualizes the approved analysis and carries sample-size context.
