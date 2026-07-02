import csv
import json
import argparse
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

class LiftyDB:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data = self._load_data()

    def _calculate_e1rm(self, weight: float, reps: int, set_type: str) -> float:
        if set_type == "W" or set_type == "Rest Timer" or set_type == "Note":
            return 0.0
        if set_type == "F":
            reps -= 1
        if reps <= 0 or weight <= 0: 
            return 0.0
        if reps == 1:
            return round(weight, 2)
        return round(weight * (1 + 0.0333 * reps), 2)

    def _load_data(self) -> List[Dict[str, Any]]:
        rows = []
        if not os.path.exists(self.csv_path):
            return []
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';', quotechar='"')
            header = next(reader, None)
            
            if header and not header[0].isdigit():
                pass
            else:
                f.seek(0)
            
            for row in reader:
                if len(row) < 11: continue
                try:
                    set_order = row[5].strip()
                    if set_order == "Rest Timer" or set_order == "Note":
                        continue
                        
                    weight = float(row[6]) if row[6] else 0.0
                    reps = int(row[7]) if row[7] else 0
                    rpe = float(row[8]) if row[8] else 0.0
                    
                    # Store raw date for filtering
                    date_str = row[1]
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                    rows.append({
                        "session_id": row[0],
                        "date": date_str,
                        "date_obj": date_obj,
                        "exercise": row[4],
                        "set_order": set_order,
                        "weight": weight,
                        "reps": reps,
                        "rpe": rpe,
                        "e1rm": self._calculate_e1rm(weight, reps, set_order),
                        "note": row[11] if len(row) > 11 else "",
                        "workout_note": row[12] if len(row) > 12 else ""
                    })
                except Exception:
                    continue
        return rows

    def get_last_n_workouts(self, n: int) -> List[Dict[str, Any]]:
        unique_sessions = []
        seen = set()
        for row in reversed(self.data):
            sid = row['session_id']
            if sid not in seen:
                unique_sessions.append(sid)
                seen.add(sid)
            if len(unique_sessions) >= n:
                break
        
        return [row for row in self.data if row['session_id'] in unique_sessions]

    def get_exercise_history(self, exercise_name: str, n: int = 10) -> List[Dict[str, Any]]:
        matches = [row for row in self.data if exercise_name.lower() in row['exercise'].lower()]
        return matches[-n:]

    def filter_by_date(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        return [row for row in self.data if start <= row['date_obj'] <= end]

    def generate_index(self) -> Dict[str, Any]:
        index = {"exercises": {}, "total_sessions": 0, "last_update": str(datetime.now())}
        unique_sessions = set()
        
        for row in self.data:
            unique_sessions.add(row['session_id'])
            ex = row['exercise']
            if ex not in index['exercises']:
                index['exercises'][ex] = {"count": 0, "last_date": "", "best_e1rm": 0.0}
            
            index['exercises'][ex]['count'] += 1
            index['exercises'][ex]['last_date'] = row['date']
            if row['e1rm'] > index['exercises'][ex]['best_e1rm']:
                index['exercises'][ex]['best_e1rm'] = row['e1rm']
        
        index['total_sessions'] = len(unique_sessions)
        return index

def main():
    parser = argparse.ArgumentParser(description="Lifty Metrics Query Utility")
    parser.add_argument("-e", "--exercise", help="Filter by exercise name")
    parser.add_argument("-n", "--last-n", type=int, help="Last N items")
    parser.add_argument("-w", "--workouts", action="store_true", help="Retrieve whole workouts instead of specific sets")
    parser.add_argument("-idx", "--index", action="store_true", help="Generate/Update index.json")
    parser.add_argument("-s", "--session", help="Retrieve specific session ID")
    
    # Date Filtering
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Number of days from start date")
    
    args = parser.parse_args()
    
    if args.days and args.end_date:
        print("Error: Specify either --days or --end-date, not both.")
        return

    db_path = "database/logs/lifting_log_database.csv"
    db = LiftyDB(db_path)

    if args.index:
        idx = db.generate_index()
        with open("database/metrics/index.json", "w") as f:
            json.dump(idx, f, indent=2)
        print("Index updated successfully.")
        return

    # Date filtering logic
    if args.days and not args.start_date and not args.end_date:
        args.start_date = (datetime.now() - timedelta(days=args.days)).strftime('%Y-%m-%d')
    
    result = []
    
    if args.start_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        if args.end_date:
            end = datetime.strptime(args.end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        elif args.days:
            end = start + timedelta(days=args.days)
        else:
            end = datetime.now()
        result = db.filter_by_date(start, end)
        
    elif args.session:
        result = [row for row in db.data if row['session_id'] == args.session]
    elif args.workouts:
        n = args.last_n if args.last_n else 5
        result = db.get_last_n_workouts(n)
    elif args.exercise:
        n = args.last_n if args.last_n else 10
        result = db.get_exercise_history(args.exercise, n)
    else:
        n = args.last_n if args.last_n else 5
        result = db.get_last_n_workouts(n)

    # Remove the date_obj from output to keep it clean for the LLM
    for row in result:
        if 'date_obj' in row:
            del row['date_obj']

    # Save results to file instead of printing to stdout
    output_file = os.path.join('database', 'metrics', 'last_query_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    print(f"Extraction Complete. {len(result)} sets retrieved.")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
