#!/usr/bin/env bash
# Rebuild the ledgers from the audit decisions and fill every number and table in paper_en.md / paper_draft.md.
# Needs Python 3 with numpy (error_sim.py) and matplotlib (fig_main_v2.py). After the run, `git diff` should be empty.
set -euo pipefail
cd "$(dirname "$0")"
python3 build_long_fires_v2.py > /dev/null      # edo_long_fires_v2.csv (92 records, 75 areas) from hensai_shapes.csv + audits
python3 exclusions.py > /dev/null               # exclusions.csv (reason and category for every excluded candidate)
(cd straight_check && python3 match_yamakawa.py > /dev/null)   # straight_check/vs_yamakawa.csv
python3 paper_numbers.py                        # fills <!--n:..--> markers and tables in both papers
python3 fig_main_v2.py > /dev/null              # fig_main_v2.png
