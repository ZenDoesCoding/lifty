#!/usr/bin/env python3
import os
import json
import sys
import shutil
from pathlib import Path

def main():
    # Configure stdout/stderr to use UTF-8 encoding on Windows to prevent UnicodeEncodeErrors
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Use current working directory as workspace root
    root = Path.cwd()
    
    profile_path = root / "database" / "metrics" / "athlete_profile.json"
    lock_path = root / "RESET_LOCK.txt"
    
    if not profile_path.exists():
        print("Error: database/metrics/athlete_profile.json is missing.", file=sys.stderr)
        sys.exit(1)
        
    if not lock_path.exists():
        print("Error: RESET_LOCK.txt is missing from the workspace root.", file=sys.stderr)
        sys.exit(1)
        
    # Read the athlete profile
    try:
        profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing athlete_profile.json: {e}", file=sys.stderr)
        sys.exit(1)
        
    configured_password = profile_data.get("reset_password", "").strip()
    
    # If no reset password is set, abort
    if not configured_password:
        print("Error: No reset password has been configured yet.", file=sys.stderr)
        print("Please run the onboarding process (/onboard) to initialize the workspace and set a password.", file=sys.stderr)
        sys.exit(1)
        
    # Read the user entered password in RESET_LOCK.txt
    lock_lines = lock_path.read_text(encoding="utf-8").split("\n")
    entered_password = ""
    for line in lock_lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        entered_password = line_stripped
        break
        
    if not entered_password:
        print("Error: RESET_LOCK.txt does not contain an authorization password.", file=sys.stderr)
        print("Please write your reset password in RESET_LOCK.txt (on a new line below the comments) and try again.", file=sys.stderr)
        sys.exit(1)
        
    if entered_password != configured_password:
        print("Error: Reset authorization failed.", file=sys.stderr)
        print("The password entered in RESET_LOCK.txt does not match your configured reset password.", file=sys.stderr)
        sys.exit(1)
        
    print("Reset authorized. Proceeding with workspace cleaning...")
    
    # Revert all files back to clean clone defaults
    try:
        # 1. Goals
        goals_file = root / "database" / "goals" / "current_goals.md"
        goals_file.parent.mkdir(parents=True, exist_ok=True)
        goals_file.write_text(
            "# Current Goals\n\n"
            "<!-- Specify your main training goal (e.g. increase squat/bench/deadlift, hypertrophy focus) -->\n"
            "<!-- Example: Maximize Bench Press Strength -->\n"
            "- Primary: \n\n"
            "<!-- Specify supporting targets (e.g. bring squat-to-bench ratio to 1.4+, improve conditioning) -->\n"
            "<!-- Example: Bring Squat and Deadlift standards closer to Bench Press (Targeting S:B ratio of 1.4+) -->\n"
            "- Secondary: \n\n"
            "<!-- Specify target number of training days per week (integer, e.g. 4) -->\n"
            "<!-- Example: 4 days per week -->\n"
            "- Training Frequency: \n",
            encoding="utf-8"
        )
        
        # 2. Base Info
        base_info_file = root / "database" / "metrics" / "base_info.json"
        base_info_file.parent.mkdir(parents=True, exist_ok=True)
        base_info_file.write_text(json.dumps({
            "status": "Maintenance, Bulk, Cut",
            "weight": "40.0 - 200.0 (float in kg)",
            "height": "100 - 250 (int in cm)",
            "gender": "male, female"
        }, indent=2) + "\n", encoding="utf-8")
        
        # 4. Logs
        logs_dir = root / "database" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        lifting_log = logs_dir / "lifting_log_database.csv"
        lifting_log.write_text(
            '"Workout #";"Date";"Workout Name";"Duration (sec)";"Exercise Name";"Set Order";"Weight (kg)";"Reps";"RPE";"Distance (meters)";"Seconds";"Notes";"Workout Notes"\n',
            encoding="utf-8"
        )
        
        weight_log = logs_dir / "weight_log.csv"
        weight_log.write_text("Date,Weight_kg\n", encoding="utf-8")
        
        wellness_log = logs_dir / "wellness_log.csv"
        wellness_log.write_text(
            "Date,Sleep_Start,Sleep_End,Sleep_Quality_1_to_10,Stress_1_to_10,Soreness_1_to_10,Notes\n",
            encoding="utf-8"
        )

        
        # 5. Metrics index/PR/history/profile
        profile_file = root / "database" / "metrics" / "athlete_profile.json"
        profile_file.write_text(json.dumps({
            "insights": [],
            "reset_password": ""
        }, indent=2) + "\n", encoding="utf-8")
        
        (root / "database" / "metrics" / "e1rm_history.json").write_text("{}\n", encoding="utf-8")
        (root / "database" / "metrics" / "pr_tracking.json").write_text("{}\n", encoding="utf-8")
        (root / "database" / "metrics" / "index.json").write_text("{}\n", encoding="utf-8")
        
        # 6. Active Plan
        active_plan_file = root / "training_plans" / "active_plan.md"
        active_plan_file.parent.mkdir(parents=True, exist_ok=True)
        active_plan_file.write_text("# LIFTY OS: ACTIVE TRAINING PLAN\n", encoding="utf-8")
        
        # 7. Reset lock file itself
        lock_file_default = (
            "# LIFTY OS: RESET AUTHORIZATION LOCK\n"
            "# To perform a complete workspace reset, enter your reset password on the line below:\n\n"
        )
        lock_path.write_text(lock_file_default, encoding="utf-8")
        
        # 8. Clean temporary files & archives
        archive_dir = root / "training_plans" / "archive"
        if archive_dir.exists():
            shutil.rmtree(archive_dir)
            archive_dir.mkdir(parents=True, exist_ok=True)
            
        last_analysis_txt = logs_dir / "last_forensic_analysis.txt"
        if last_analysis_txt.exists():
            last_analysis_txt.unlink()
            
        print("✅ Workspace successfully reset to clean clone defaults!")
        sys.exit(0)
    except Exception as e:
        print(f"Error resetting workspace files: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
