#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path

def check_goals(root: Path):
    path = root / "database" / "goals" / "current_goals.md"
    if not path.exists():
        return "Missing", "Create database/goals/current_goals.md"
    
    content = path.read_text(encoding="utf-8").strip()
    
    # Check if the fields are actually filled
    lines = content.splitlines()
    has_primary = False
    has_secondary = False
    has_frequency = False
    
    for line in lines:
        line = line.strip()
        if line.startswith("- Primary:") and len(line.replace("- Primary:", "").strip()) > 0:
            has_primary = True
        elif line.startswith("- Secondary:") and len(line.replace("- Secondary:", "").strip()) > 0:
            has_secondary = True
        elif line.startswith("- Training Frequency:") and len(line.replace("- Training Frequency:", "").strip()) > 0:
            has_frequency = True
            
    if not (has_primary and has_secondary and has_frequency):
        return "Placeholder", "Define your training goals, primary lifts, target ratios, and frequency in database/goals/current_goals.md"
    
    return "Configured", "Ready"

def check_base_info(root: Path):
    path = root / "database" / "metrics" / "base_info.json"
    if not path.exists():
        return "Missing", "Create database/metrics/base_info.json"
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        weight = data.get("weight", 0.0)
        height = data.get("height", 0)
        gender = data.get("gender", "")
        status = data.get("status", "")
        
        # Validate types and ranges/values
        if (not isinstance(weight, (int, float)) or weight <= 0.0 or
            not isinstance(height, int) or height <= 0 or
            gender not in ["male", "female"] or
            status not in ["Maintenance", "Bulk", "Cut"]):
            return "Placeholder", "Update weight, height, gender, and status in database/metrics/base_info.json"
    except Exception as e:
        return "Error", f"Failed to parse JSON: {e}"
    
    return "Configured", "Ready"

def check_athlete_profile(root: Path):
    path = root / "database" / "metrics" / "athlete_profile.json"
    if not path.exists():
        return "Missing", "Create database/metrics/athlete_profile.json"
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        password = data.get("reset_password", "").strip()
        if not password:
            return "Placeholder", "Set a reset passphrase in database/metrics/athlete_profile.json"
    except Exception as e:
        return "Error", f"Failed to parse JSON: {e}"
    
    return "Configured", "Ready"

def check_lifting_logs(root: Path):
    path = root / "database" / "logs" / "lifting_log_database.csv"
    if not path.exists():
        return "Missing", "Create database/logs/lifting_log_database.csv. Help: /import_guide"
    
    try:
        content = path.read_text(encoding="utf-8").strip()
        lines = [line for line in content.split("\n") if line.strip()]
        if len(lines) <= 1:
            return "Placeholder", "Export history from Strong app (only format currently supported). Help: /import_guide"
    except Exception as e:
        return "Error", f"Failed to read CSV: {e}"
    
    return "Configured", "Ready"

def main():
    # Configure stdout/stderr to use UTF-8 encoding on Windows to prevent UnicodeEncodeErrors
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Use current working directory as the workspace root
    root = Path.cwd()
    
    files_to_check = [
        ("Goals Configuration", "database/goals/current_goals.md", check_goals),
        ("Base Info", "database/metrics/base_info.json", check_base_info),
        ("Lifting Logs", "database/logs/lifting_log_database.csv", check_lifting_logs),
        ("Reset Passphrase", "database/metrics/athlete_profile.json", check_athlete_profile),
    ]
    
    results = []
    unconfigured_count = 0
    
    for name, rel_path, check_fn in files_to_check:
        status, action = check_fn(root)
        results.append({
            "name": name,
            "path": rel_path,
            "status": status,
            "action": action
        })
        if status != "Configured":
            unconfigured_count += 1
            
    # Print the markdown table
    print("| Component | File Path | Status | Action Required |")
    print("| :--- | :--- | :--- | :--- |")
    for r in results:
        status_str = r["status"]
        if status_str == "Configured":
            status_emoji = "✅ Configured"
        elif status_str == "Placeholder":
            status_emoji = "⚠️ Default Placeholder"
        elif status_str == "Missing":
            status_emoji = "❌ Missing"
        else:
            status_emoji = "❌ Error"
            
        print(f"| {r['name']} | `{r['path']}` | {status_emoji} | {r['action']} |")
        
    print()
    if unconfigured_count > 0:
        print(f"STATUS: PENDING - {unconfigured_count} file(s) require personalization.")
        sys.exit(1)
    else:
        print("STATUS: OK - All core personalization files are configured!")
        sys.exit(0)

if __name__ == "__main__":
    main()
