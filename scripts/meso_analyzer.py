import os
import shutil
import sys
from datetime import datetime, timedelta
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF, XPos, YPos
from query_metrics import LiftyDB
from check_setup import check_base_info, check_goals

# Helper for fractional sets
def get_fractional_value(exercise: str) -> float:
    ex_lower = exercise.lower()
    if 'squat' in ex_lower or 'bench' in ex_lower or 'deadlift' in ex_lower:
        return 1.0
    return 0.5

def calculate_acwr(data, end_date):
    # Acute: Last 7 days
    # Chronic: Last 28 days
    acute_start = end_date - timedelta(days=7)
    chronic_start = end_date - timedelta(days=28)
    
    acute_load = 0.0
    chronic_load_total = 0.0
    
    weekly_loads = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    
    for row in data:
        dt = row['date_obj']
        if chronic_start <= dt <= end_date:
            val = get_fractional_value(row['exercise'])
            chronic_load_total += val
            
            # Bucket into 4 weeks for plotting
            days_ago = (end_date - dt).days
            if days_ago < 7: weekly_loads[4] += val
            elif days_ago < 14: weekly_loads[3] += val
            elif days_ago < 21: weekly_loads[2] += val
            elif days_ago < 28: weekly_loads[1] += val
            
        if acute_start < dt <= end_date:
            val = get_fractional_value(row['exercise'])
            acute_load += val
            
    chronic_load_avg = chronic_load_total / 4.0 if chronic_load_total > 0 else 0
    acwr = acute_load / chronic_load_avg if chronic_load_avg > 0 else 0
    
    return acute_load, chronic_load_avg, acwr, weekly_loads

def calculate_e1rm_trends(data, end_date):
    target_exercises = ['Squat', 'Bench Press', 'Deadlift']
    trends = {}
    
    for target in target_exercises:
        # Try 45 days first
        start_date = end_date - timedelta(days=45)
        daily_maxes = {}
        for row in data:
            if start_date <= row['date_obj'] <= end_date:
                ex_name = row['exercise'].lower()
                tgt_name = target.lower()
                # Strict matching: target exercise should be exactly equal, or match "target ("
                if ex_name == tgt_name or ex_name.startswith(tgt_name + " ("):
                    day_str = row['date_obj'].strftime('%Y-%m-%d')
                    if day_str not in daily_maxes or row['e1rm'] > daily_maxes[day_str]:
                        daily_maxes[day_str] = row['e1rm']
        
        # If fewer than 3 sessions, look back 90 days (add another 45 days prior)
        if len(daily_maxes) < 3:
            start_date = end_date - timedelta(days=90)
            daily_maxes = {}
            for row in data:
                if start_date <= row['date_obj'] <= end_date:
                    ex_name = row['exercise'].lower()
                    tgt_name = target.lower()
                    if ex_name == tgt_name or ex_name.startswith(tgt_name + " ("):
                        day_str = row['date_obj'].strftime('%Y-%m-%d')
                        if day_str not in daily_maxes or row['e1rm'] > daily_maxes[day_str]:
                            daily_maxes[day_str] = row['e1rm']
                            
        if len(daily_maxes) > 1:
            # Sort by date
            sorted_days = sorted(daily_maxes.keys())
            x_vals = [(datetime.strptime(d, '%Y-%m-%d') - start_date).days for d in sorted_days]
            y_vals = [daily_maxes[d] for d in sorted_days]
            
            # Linear Regression
            z = np.polyfit(x_vals, y_vals, 1) # z[0] is slope (kg/day)
            slope_weekly = z[0] * 7
            volatility = np.std(y_vals) if len(y_vals) > 0 else 0
            
            trends[target] = {
                'x': x_vals,
                'y': y_vals,
                'slope_weekly': slope_weekly,
                'volatility': volatility,
                'line_poly': np.poly1d(z)
            }
            
    return trends

def calculate_intensity(data, end_date):
    start_date = end_date - timedelta(days=45)
    brackets = {'Low (<7)': 0, 'Medium (7-8.4)': 0, 'High (8.5+)': 0}
    
    for row in data:
        if start_date <= row['date_obj'] <= end_date:
            rpe = row['rpe']
            if rpe < 7: brackets['Low (<7)'] += 1
            elif rpe < 8.5: brackets['Medium (7-8.4)'] += 1
            else: brackets['High (8.5+)'] += 1
            
    total = sum(brackets.values())
    
    # If fewer than 3 sets are found, look back 90 days (add another 45 days prior)
    if total < 3:
        start_date = end_date - timedelta(days=90)
        brackets = {'Low (<7)': 0, 'Medium (7-8.4)': 0, 'High (8.5+)': 0}
        for row in data:
            if start_date <= row['date_obj'] <= end_date:
                rpe = row['rpe']
                if rpe < 7: brackets['Low (<7)'] += 1
                elif rpe < 8.5: brackets['Medium (7-8.4)'] += 1
                else: brackets['High (8.5+)'] += 1
        total = sum(brackets.values())
        
    if total > 0:
        return {k: v/total*100 for k, v in brackets.items()}, total
    return brackets, 0

def archive_meso_state():
    state_file = 'database/metrics/meso_state.md'
    if os.path.exists(state_file):
        mod_time = datetime.fromtimestamp(os.path.getmtime(state_file))
        timestamp = mod_time.strftime('%Y_%m_%d_%H_%M')
        archive_dir = 'database/metrics/archive'
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, f'meso_state_{timestamp}.md')
        shutil.copy2(state_file, archive_path)

def generate_pdf(weekly_loads, trends, intensity_dist, timestamp):
    # Ensure artifacts directory exists for temporary plots
    os.makedirs('artifacts', exist_ok=True)
    
    # 1. Volume Plot
    plt.figure(figsize=(6, 4))
    weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    loads = [weekly_loads[i] for i in range(1, 5)]
    plt.bar(weeks, loads, color='#3b82f6')
    plt.title('Rolling 4-Week Volume (Fractional Sets)')
    plt.ylabel('Fractional Sets')
    vol_plot_path = 'artifacts/temp_vol_plot.png'
    plt.savefig(vol_plot_path, bbox_inches='tight')
    plt.close()
    
    # 2. Intensity Plot
    plt.figure(figsize=(6, 4))
    labels = list(intensity_dist.keys())
    sizes = list(intensity_dist.values())
    if sum(sizes) > 0:
        colors = ['#22c55e', '#eab308', '#ef4444']
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    else:
        plt.pie([1], labels=['No Data Available'], colors=['#94a3b8'], startangle=140)
    plt.title('Intensity Distribution (RPE)')
    int_plot_path = 'artifacts/temp_int_plot.png'
    plt.savefig(int_plot_path, bbox_inches='tight')
    plt.close()
    
    # 3. e1RM Scatter Plot
    plt.figure(figsize=(6, 4))
    colors_dict = {'Squat': '#ef4444', 'Bench Press': '#3b82f6', 'Deadlift': '#22c55e'}
    if trends:
        for target, d in trends.items():
            plt.scatter(d['x'], d['y'], label=target, color=colors_dict.get(target, '#000000'))
            # Plot trendline
            xp = np.linspace(min(d['x']), max(d['x']), 100)
            plt.plot(xp, d['line_poly'](xp), color=colors_dict.get(target, '#000000'), linestyle='--')
        plt.legend()
    else:
        plt.text(0.5, 0.5, 'No e1RM Data in last 90 Days', ha='center', va='center')
    plt.title('e1RM Trajectory')
    plt.xlabel('Days from Start of Block')
    plt.ylabel('e1RM (kg)')
    e1rm_plot_path = 'artifacts/temp_e1rm_plot.png'
    plt.savefig(e1rm_plot_path, bbox_inches='tight')
    plt.close()

    
    # PDF Generation
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Lifty OS: Mesocycle Graph Overview', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    pdf.image(vol_plot_path, x=20, y=30, w=170)
    pdf.image(int_plot_path, x=20, y=140, w=170)
    
    pdf.add_page()
    pdf.image(e1rm_plot_path, x=20, y=20, w=170)
    
    out_dir = 'database/logs'
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f'mesocycle_graph_overview_{timestamp}.pdf')
    pdf.output(pdf_path)
    
    return pdf_path

def main():
    # Hard setup check: abort if Goals or Base Info is not configured
    root = Path.cwd()
    goals_status, goals_err = check_goals(root)
    base_status, base_err = check_base_info(root)
    if goals_status != "Configured" or base_status != "Configured":
        print("Error: Setup is unconfigured.", file=sys.stderr)
        if goals_status != "Configured":
            print(f"Goals: {goals_err}", file=sys.stderr)
        if base_status != "Configured":
            print(f"Base Info: {base_err}", file=sys.stderr)
        sys.exit(1)
        
    db = LiftyDB("database/logs/lifting_log_database.csv")
    end_date = datetime.now()
    
    acute, chronic, acwr, weekly_loads = calculate_acwr(db.data, end_date)
    trends = calculate_e1rm_trends(db.data, end_date)
    intensity_dist, total_sets = calculate_intensity(db.data, end_date)
    
    archive_meso_state()
    
    # Generate Markdown
    md_content = f"# MESOCYCLE CONTEXT (Last 45 Days)\n"
    md_content += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    md_content += f"## 1. Workload (ACWR)\n"
    md_content += f"- **Acute Load (7d):** {acute:.1f} Fractional Sets\n"
    md_content += f"- **Chronic Load (28d avg):** {chronic:.1f} Fractional Sets/week\n"
    md_content += f"- **ACWR:** {acwr:.2f} "
    if acwr > 1.5:
        md_content += "(DANGER: >1.5 indicates high overreaching/injury risk)\n"
    elif acwr < 0.8:
        md_content += "(UNDER-TRAINING: <0.8 indicates detraining risk)\n"
    else:
        md_content += "(SWEET SPOT: 0.8 - 1.3 optimal)\n"
    md_content += f"- **Volume Curve:** W1({weekly_loads[1]}) -> W2({weekly_loads[2]}) -> W3({weekly_loads[3]}) -> W4({weekly_loads[4]})\n\n"
    
    md_content += f"## 2. Intensity Distribution\n"
    md_content += f"- Low Stress (<7 RPE): {intensity_dist.get('Low (<7)', 0):.1f}%\n"
    md_content += f"- Medium Stress (7-8.4 RPE): {intensity_dist.get('Medium (7-8.4)', 0):.1f}%\n"
    md_content += f"- High Stress (8.5+ RPE): {intensity_dist.get('High (8.5+)', 0):.1f}%\n\n"
    
    md_content += f"## 3. Strength Trajectory (e1RM)\n"
    for target, d in trends.items():
        slope = d['slope_weekly']
        volatility = d['volatility']
        trend_str = "Positive" if slope > 0 else "Negative"
        md_content += f"- **{target}:** {trend_str} trend ({slope:+.2f} kg/week) | Volatility (StdDev): {volatility:.2f}\n"
        
    os.makedirs('database/metrics', exist_ok=True)
    with open('database/metrics/meso_state.md', 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M')
    pdf_path = generate_pdf(weekly_loads, trends, intensity_dist, timestamp)
    
    print(f"Meso analysis complete. State saved to database/metrics/meso_state.md")
    print(f"PDF Graph Overview saved to {pdf_path}")

if __name__ == "__main__":
    main()
