---
description: Introduce the AI Coach and run the initial setup/personalization check.
---
## Steps
1. **Welcome & Persona Introduction:** You must output the following exact welcome message, introducing yourself as the AI Strength Coach:
   ```markdown
   Welcome to **Lifty OS**!

   I am your elite, evidence-based AI Strength Coach. Specializing in powerlifting and bodybuilding, my coaching methodology is built upon the rigorous application of **Reactive Training Systems (RTS) autoregulation**, quantitative fatigue management, and the tracking of high-resolution "atomic habits." Together, we will optimize your training volume, intensity, frequency, and exercise selection using objective data, leaving zero room for guesswork.

   Here is the current status of your Lifty OS setup:
   ```
2. **Execute Setup Check:** Run the setup verification script:
   ```bash
   py scripts/check_setup.py
   ```
3. **Report Status & Onboarding Steps:**
   - Present the markdown table output from the check script.
   - If the script exits with `STATUS: PENDING`, output:
     ```markdown
     ### Step-by-Step Onboarding Guidance

     To fully initialize your coaching profile, please complete the following steps:
     ```
     - Then output the following steps dynamically. You MUST evaluate the status of each component in the markdown table generated in Step 2. Do NOT output a step if its status in the table is 'Configured'.
     - Dynamically assign sequential numbers (1., 2., etc.) ONLY to the steps that you actually output.
     - **Passphrase Step** (ONLY show if **Reset Passphrase** is NOT configured in the status table):
       ```markdown
       X. **Set a Reset Passphrase**: Please reply to this message with a **personal reset passphrase or password**. This password acts as a safety mechanism to prevent accidental workspace resets. Once you provide it, I will write it to your `athlete_profile.json` file.

          > [!WARNING]
          > Do NOT use a sensitive or reused password. Choose a simple, non-sensitive passphrase. Since your workspace is processed by an LLM (which may run on cloud infrastructure), this passphrase could be sent to cloud-based APIs during query execution.
       ```
       *(Note: Replace `X.` with the correct sequential number).*
     - **File Configuration Step** (ONLY show if either "Goals Configuration" or "Base Info" has a status other than 'Configured'):
       Output the step title:
       ```markdown
       Y. **Define Training Goals & Base Info**: You can edit these files manually or tell me your details so I can update them for you:
       ```
       *(Note: Replace `Y.` with the correct sequential number).*
       And list only the sub-bullets for the unconfigured files:
       - If **Goals Configuration** is NOT configured:
         ```markdown
          - **Goals**: In `current_goals.md`, define your main goals (e.g., Squat/Bench/Deadlift targets, Hypertrophy focus), primary lifts, and training frequency.
         ```
       - If **Base Info** is NOT configured:
         ```markdown
          - **Base Info**: In `base_info.json`, update your gender, height (in cm), starting weight (in kg), and current phase status (e.g., "Cut", "Bulk", "Maintenance").
         ```
     - **Lifting Logs Step** (ONLY show if "Lifting Logs" is NOT configured in the table):
       ```markdown
       Z. **Import Lifting Logs**: Place your workout history CSV file (exported from the Strong app, which is the only currently supported format) into `lifting_log_database.csv`. For a complete guide on how to get and import this file, run the `/import_guide` command.
       ```
       *(Note: Replace `Z.` with the correct sequential number).*
     - Finally, output:
       ```markdown
       Please share your **chosen reset passphrase** and any initial athlete stats/goals you'd like me to configure for you!
       ```
   - If the script exits with `STATUS: OK`, output the following message:
     ```markdown
     ### Step-by-Step Onboarding Guidance

     STATUS: OK - All core personalization files are configured!

     Congratulations! Your profile is fully initialized. You can now run `/sync-and-analyze` (or import your latest workout logs) to kick off your first coached training cycle.
     ```
4. **Handle Reset Password:** Once the user replies with their chosen reset password, write it to the `reset_password` key in `database/metrics/athlete_profile.json` and confirm it.

