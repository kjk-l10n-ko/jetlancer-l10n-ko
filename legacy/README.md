# Legacy translated files (migration input)

These files are the pre-migration state — the translated Korean patch outputs
before migration to the pipeline PO format.

- `contents/ui_ko.tsv` — UI string table (English source + Korean translation)
- `out/Dialogue/` — Translated dialogue CSV files (recursive)

These are the **input** to `python -m adapters.jetlancer migrate`
(see `game.toml` and `run.sh`). They are frozen here for reproduction; do
not edit them directly — edit the PO files in `locales/` instead.