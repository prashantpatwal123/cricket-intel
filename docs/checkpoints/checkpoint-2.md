# Checkpoint 2: Ask Cricket v0 + What Happens Next? + baseline model

- **Ask Cricket v0** (`/ask`): 10 deterministic templates (run out / bowled / caught behind… counts; who dismissed X most; X vs bowler runs and SR; chasing vs setting; which over; vs pace/spin; sixes/fours). Recognises format, phase, "internationals" and "since YYYY". Entity resolution uses dataset names (full name or unique surname) and asks for clarification when ambiguous. No LLM. Tests assert every number in the answer text appears in the query payload.
- **What Happens Next?** (`/play`): 400 historical moments, weighted toward tight finishes, death overs and milestones. Drawn only from matches after the model's training cutoff. Opaque HMAC moment ids. Points shown before picking. Reveal shows the real outcome (OBSERVED), the model distribution (MODELLED), drivers and the next balls. Score and streak persist in localStorage.
- **Scoring decision:** `docs/game-scoring.md`.
- **Baseline model:** `docs/model-card-baseline.md`.
- Screenshots: `docs/screenshots/checkpoint-2/`.
