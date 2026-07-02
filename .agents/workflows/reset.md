---
description: Completely reset the workspace back to clean git clone template defaults.
---
## Steps
1. **Explain Destructive Action:** Inform the user that resetting is highly destructive and will permanently delete all training history, active plans, goal configurations, and base info profile, returning the workspace to its default downloaded template state.
2. **Direct to RESET_LOCK.txt:** Instruct the user that they must open `RESET_LOCK.txt` in the root of the workspace and write their reset password (set up during onboarding) on a new line below the comments.
3. **Double Confirmation Prompt:** Ask the user to confirm their intent in the chat by typing exactly: "Yes, delete all data and reset Lifty OS". Do not run the script until the user responds with this exact confirmation.
4. **Run Reset Script:** Run the workspace reset script:
   ```bash
   py scripts/reset_workspace.py
   ```
5. **Verify Success:** If the script exits successfully (exit code 0), confirm to the user that the workspace has been reset and that they can start fresh by running `/onboard`. If it fails, report the error printed by the script.
