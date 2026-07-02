---
description: This workflow automates the full data-to-coaching pipeline of Lifty OS using Delta-State Architecture.
---
## Steps
(If the user wrote exactly "!override *number*" within the prompt you must skip the Debounce Check completely, use the `*number*` specified with `!override` for the `<DELTA_START>` value instead and continue with step 2)
1. **Verify Onboarding Setup:** Run setup verification check:
   ```bash
   py scripts/check_setup.py
   ```
   If the script exits with status code 1, immediately abort this workflow and all subsequent tool calls, reporting that the setup requires personalization. Direct the user to run `/onboard` first.
2. **Debounce Check:** Run `py scripts/debounce_check.py`. If the output is "ABORT" the workflow and all further tool calls must be aborted immediately and the output from this workflow must only be "WORKFLOW ABORTED, LAST WORKFLOW WAS CALLED *last_forensic_analysis extract*". Otherwise, extract the DELTA_START date and continue with step 3.
3. **Delta Extraction:** Run `py scripts/query_metrics.py -idx` to update the index. Then run `py scripts/query_metrics.py --start-date <DELTA_START>` using the date output from Step 2.
4. **Execute Meso Analyzer:** Run `py scripts/meso_analyzer.py` to calculate ACWR, e1RM trajectories, and generate the Meso Context.
5. **Timestamp Update:** Run `py scripts/update_timestamp.py` to overwrite `database\logs\last_forensic_analysis.txt` with the current UTC time.
6. **Analyze Fatigue:** Apply the `@forensic_analysis` rule.
7. **Update Training Plan:** Apply the `@coaching_logic` rule.