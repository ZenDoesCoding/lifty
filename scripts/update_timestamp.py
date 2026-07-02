import os
from datetime import datetime

def main():
    file_path = os.path.join('database', 'logs', 'last_forensic_analysis.txt')
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    main()
