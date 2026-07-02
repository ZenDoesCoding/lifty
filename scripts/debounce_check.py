import os
from datetime import datetime, timedelta

def main():
    file_path = os.path.join('database', 'logs', 'last_forensic_analysis.txt')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    now = datetime.utcnow()
    
    # If the file doesn't exist, initialize it with a date 60 days ago
    if not os.path.exists(file_path):
        initial_date = now - timedelta(days=60)
        initial_date_str = initial_date.strftime('%Y-%m-%d')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(initial_date_str)
        print(f"DELTA_START: {initial_date_str}")
        return
        
    # Read the last analysis date
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Try to parse exact UTC time if previously saved with time, or just YYYY-MM-DD
            try:
                last_date = datetime.strptime(content, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                last_date = datetime.strptime(content, '%Y-%m-%d')
    except Exception as e:
        # Fallback if file is corrupted
        initial_date = now - timedelta(days=60)
        initial_date_str = initial_date.strftime('%Y-%m-%d')
        print(f"DELTA_START: {initial_date_str}")
        return

    # Calculate hours since last run
    hours_diff = (now - last_date).total_seconds() / 3600.0
    
    if hours_diff < 24:
        print("ABORT")
    else:
        print(f"DELTA_START: {last_date.strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
