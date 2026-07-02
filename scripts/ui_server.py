import os
import json
import re
import urllib.parse
import asyncio
from typing import AsyncIterator, Any
import uvicorn

from google.antigravity import Agent, types
from google.antigravity.connections import connection

# =============================================================================
# Antigravity SDK Offline Mock Configuration
# =============================================================================

def parse_meso_state():
    path = "database/metrics/meso_state.md"
    metrics = {
        "acute_load": None,
        "chronic_load": None,
        "acwr": None,
        "slopes": {}
    }
    if not os.path.exists(path):
        return metrics
    
    try:
        content = open(path, "r", encoding="utf-8").read()
        
        # Parse Acute Load
        m = re.search(r"Acute Load \(7d\):\*\* ([\d\.]+)", content)
        if m: metrics["acute_load"] = float(m.group(1))
        
        # Parse Chronic Load
        m = re.search(r"Chronic Load \(28d avg\):\*\* ([\d\.]+)", content)
        if m: metrics["chronic_load"] = float(m.group(1))
        
        # Parse ACWR
        m = re.search(r"ACWR:\*\* ([\d\.]+)", content)
        if m: metrics["acwr"] = float(m.group(1))
        
        # Parse Slopes
        for line in content.splitlines():
            if "trend (" in line:
                m_ex = re.search(r"\- \*\*([^*]+)\*\*:", line)
                m_slope = re.search(r"([+-][\d\.]+) kg/week", line)
                if m_ex and m_slope:
                    metrics["slopes"][m_ex.group(1).strip()] = float(m_slope.group(1))
    except Exception as e:
        print("Error parsing meso_state:", e)
    return metrics

# Mock connections and templates removed in favor of live SDK execution.


# =============================================================================
# ASGI Web Server & API Handlers
# =============================================================================

async def serve_file(file_path, content_type, send):
    if not os.path.exists(file_path):
        await send_response(404, b"File Not Found", "text/plain", send)
        return
    with open(file_path, "rb") as f:
        content = f.read()
    await send_response(200, content, content_type, send)

async def send_response(status, body, content_type, send):
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [
            (b'content-type', content_type.encode('utf-8')),
            (b'content-length', str(len(body)).encode('utf-8')),
            (b'cache-control', b'no-cache')
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': body,
        'more_body': False
    })

async def handle_api_status(send):
    import sys
    sys.path.append(os.path.abspath("scripts"))
    try:
        import check_setup
        from pathlib import Path
        root_path = Path(os.path.abspath("."))
        
        goals_status, goals_action = check_setup.check_goals(root_path)
        base_status, base_action = check_setup.check_base_info(root_path)
        logs_status, logs_action = check_setup.check_lifting_logs(root_path)
    except Exception as e:
        goals_status, goals_action = "Error", str(e)
        base_status, base_action = "Error", str(e)
        logs_status, logs_action = "Error", str(e)
        
    results = [
        {"name": "Goals Configuration", "status": goals_status, "action": goals_action},
        {"name": "Base Profile", "status": base_status, "action": base_action},
        {"name": "Lifting Logs", "status": logs_status, "action": logs_action}
    ]
    body = json.dumps(results).encode('utf-8')
    await send_response(200, body, "application/json", send)

async def handle_api_get_base_info(send):
    path = "database/metrics/base_info.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = json.dumps({"weight": 0.0, "height": 0, "gender": "male", "status": "Maintenance"})
    await send_response(200, content.encode('utf-8'), "application/json", send)

async def handle_api_post_base_info(receive, send):
    body = b""
    while True:
        message = await receive()
        if message['type'] == 'http.request':
            body += message.get('body', b'')
            if not message.get('more_body', False):
                break
    try:
        data = json.loads(body.decode('utf-8'))
        os.makedirs("database/metrics", exist_ok=True)
        with open("database/metrics/base_info.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await send_response(200, b'{"status": "success"}', "application/json", send)
    except Exception as e:
        await send_response(400, f'{{"error": "{str(e)}"}}'.encode('utf-8'), "application/json", send)

async def handle_api_get_goals(send):
    path = "database/goals/current_goals.md"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""
    body = json.dumps({"content": content}).encode('utf-8')
    await send_response(200, body, "application/json", send)

async def handle_api_post_goals(receive, send):
    body = b""
    while True:
        message = await receive()
        if message['type'] == 'http.request':
            body += message.get('body', b'')
            if not message.get('more_body', False):
                break
    try:
        data = json.loads(body.decode('utf-8'))
        content = data.get("content", "")
        os.makedirs("database/goals", exist_ok=True)
        with open("database/goals/current_goals.md", "w", encoding="utf-8") as f:
            f.write(content)
        await send_response(200, b'{"status": "success"}', "application/json", send)
    except Exception as e:
        await send_response(400, f'{{"error": "{str(e)}"}}'.encode('utf-8'), "application/json", send)

async def handle_api_metrics(send):
    metrics = parse_meso_state()
    body = json.dumps(metrics).encode('utf-8')
    await send_response(200, body, "application/json", send)

async def run_pipeline_stream(send_fn):
    scripts = [
        ("Checking setup...", [sys.executable, "scripts/check_setup.py"]),
        ("Updating database index...", [sys.executable, "scripts/query_metrics.py", "-idx"]),
        ("Running meso analytics...", [sys.executable, "scripts/meso_analyzer.py"]),
        ("Updating timestamp...", [sys.executable, "scripts/update_timestamp.py"])
    ]
    
    for desc, cmd in scripts:
        await send_fn(f"\n\n--- [SYSTEM] {desc} ---\n")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                await send_fn(line.decode('utf-8', errors='replace'))
                
            await process.wait()
            if process.returncode != 0:
                await send_fn(f"\n[ERROR] Command failed with exit code {process.returncode}\n")
                return
        except Exception as e:
            await send_fn(f"\n[ERROR] Failed to execute command: {e}\n")
            return
    await send_fn("\n\n--- [SYSTEM] Pipeline complete! Dashboard metrics and charts have been refreshed. ---\n")

async def handle_api_run_pipeline(send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
            (b'transfer-encoding', b'chunked'),
            (b'cache-control', b'no-cache')
        ]
    })
    
    async def send_log_chunk(text):
        await send({
            'type': 'http.response.body',
            'body': text.encode('utf-8'),
            'more_body': True
        })
        
    await run_pipeline_stream(send_log_chunk)
    
    await send({
        'type': 'http.response.body',
        'body': b"",
        'more_body': False
    })

async def handle_api_chat(prompt, scope, send):
    # Retrieve Gemini API Key from custom headers
    headers = {k.decode('utf-8').lower(): v.decode('utf-8') for k, v in scope.get('headers', [])}
    api_key = headers.get('x-gemini-api-key', '').strip()
    
    # Fallback to environment variable
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/event-stream'),
            (b'cache-control', b'no-cache'),
            (b'connection', b'keep-alive')
        ]
    })
    
    if not api_key:
        # Stream a clear API Key Needed warning to the user
        payload = {
            "type": "text",
            "text": "⚠️ **Gemini API Key missing.** \n\n"
                    "To chat with the live coach, please paste your API Key in the top-right header input field, "
                    "or define the `GEMINI_API_KEY` environment variable in your terminal. \n\n"
                    "You can get a free key from the [Google AI Studio](https://aistudio.google.com/app/api-keys)."
        }
        await send({
            'type': 'http.response.body',
            'body': f"data: {json.dumps(payload)}\n\n".encode('utf-8'),
            'more_body': True
        })
        await send({
            'type': 'http.response.body',
            'body': b"",
            'more_body': False
        })
        return
        
    try:
        from google.antigravity import LocalAgentConfig
        from google.antigravity.hooks import policy
        
        config = LocalAgentConfig(
            api_key=api_key,
            policies=[policy.allow_all()], # Auto-allow read/write tools inside the workspace
            workspaces=[os.path.abspath(".")] # Limit tool scoping to the project directory
        )
        
        async with Agent(config=config) as agent:
            response = await agent.chat(prompt)
            async for chunk in response.chunks:
                chunk_type = ""
                chunk_text = ""
                chunk_name = ""
                chunk_args = {}
                
                if isinstance(chunk, types.Thought):
                    chunk_type = "thought"
                    chunk_text = chunk.text
                elif isinstance(chunk, types.Text):
                    chunk_type = "text"
                    chunk_text = chunk.text
                elif isinstance(chunk, types.ToolCall):
                    chunk_type = "tool_call"
                    chunk_name = chunk.name
                    chunk_args = chunk.args
                else:
                    continue
                    
                payload = {
                    "type": chunk_type,
                    "text": chunk_text,
                    "name": chunk_name,
                    "args": chunk_args
                }
                
                await send({
                    'type': 'http.response.body',
                    'body': f"data: {json.dumps(payload)}\n\n".encode('utf-8'),
                    'more_body': True
                })
    except Exception as e:
        payload = {
            "type": "text",
            "text": f"Error running Gemini Antigravity Agent: {str(e)}"
        }
        await send({
            'type': 'http.response.body',
            'body': f"data: {json.dumps(payload)}\n\n".encode('utf-8'),
            'more_body': True
        })
        
    await send({
        'type': 'http.response.body',
        'body': b"",
        'more_body': False
    })

# Main ASGI Router
async def app(scope, receive, send):
    path = scope['path']
    method = scope.get('method', 'GET')
    
    if scope['type'] == 'http':
        if path == '/' or path == '/index.html':
            await serve_file("assets/ui/index.html", "text/html", send)
        elif path == '/assets/styles.css':
            await serve_file("assets/ui/styles.css", "text/css", send)
        elif path == '/assets/app.js':
            await serve_file("assets/ui/app.js", "text/javascript", send)
        elif path == '/assets/temp_vol_plot.png':
            await serve_file("artifacts/temp_vol_plot.png", "image/png", send)
        elif path == '/assets/temp_int_plot.png':
            await serve_file("artifacts/temp_int_plot.png", "image/png", send)
        elif path == '/assets/temp_e1rm_plot.png':
            await serve_file("artifacts/temp_e1rm_plot.png", "image/png", send)
        elif path == '/favicon.ico':
            await send_response(204, b"", "image/x-icon", send)
        elif path == '/api/status' and method == 'GET':
            await handle_api_status(send)
        elif path == '/api/base-info' and method == 'GET':
            await handle_api_get_base_info(send)
        elif path == '/api/base-info' and method == 'POST':
            await handle_api_post_base_info(receive, send)
        elif path == '/api/goals' and method == 'GET':
            await handle_api_get_goals(send)
        elif path == '/api/goals' and method == 'POST':
            await handle_api_post_goals(receive, send)
        elif path == '/api/metrics' and method == 'GET':
            await handle_api_metrics(send)
        elif path == '/api/run-pipeline' and method == 'POST':
            await handle_api_run_pipeline(send)
        elif path == '/api/chat' and method == 'GET':
            query_string = scope.get('query_string', b'').decode('utf-8')
            params = urllib.parse.parse_qs(query_string)
            prompt = params.get('prompt', [''])[0]
            await handle_api_chat(prompt, scope, send)
        else:
            await send_response(404, b"Not Found", "text/plain", send)

if __name__ == "__main__":
    import sys
    
    # Pre-generate default/mock charts on startup so the UI is immediately fully functional with no placeholders
    try:
        print("Checking configuration status for chart generation...")
        import check_setup
        from pathlib import Path
        root_path = Path(os.path.abspath("."))
        
        goals_status, _ = check_setup.check_goals(root_path)
        base_status, _ = check_setup.check_base_info(root_path)
        logs_status, _ = check_setup.check_lifting_logs(root_path)
        
        if goals_status == "Configured" and base_status == "Configured" and logs_status == "Configured":
            print("Setup fully configured. Generating real charts from logs...")
            import subprocess
            subprocess.run([sys.executable, "scripts/meso_analyzer.py"])
        else:
            print("Setup unconfigured/placeholders. Generating premium mock demonstration charts...")
            
            def generate_dummy_charts():
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                import numpy as np
                
                os.makedirs('artifacts', exist_ok=True)
                
                # 1. Volume Plot
                plt.figure(figsize=(6, 4))
                weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
                loads = [18.0, 22.5, 26.0, 12.0]
                plt.bar(weeks, loads, color='#3b82f6')
                plt.title('Rolling 4-Week Volume (Fractional Sets) - Demo')
                plt.ylabel('Fractional Sets')
                plt.savefig('artifacts/temp_vol_plot.png', bbox_inches='tight')
                plt.close()
                
                # 2. Intensity Plot
                plt.figure(figsize=(6, 4))
                labels = ['Low (<7)', 'Medium (7-8.4)', 'High (8.5+)']
                sizes = [40.0, 45.0, 15.0]
                colors = ['#22c55e', '#eab308', '#ef4444']
                plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
                plt.title('45-Day Intensity Distribution (RPE) - Demo')
                plt.savefig('artifacts/temp_int_plot.png', bbox_inches='tight')
                plt.close()
                
                # 3. e1RM Plot
                plt.figure(figsize=(6, 4))
                colors_dict = {'Squat': '#ef4444', 'Bench Press': '#3b82f6', 'Deadlift': '#22c55e'}
                x = np.array([1, 8, 15, 22, 29, 36])
                
                y_squat = np.array([180, 182, 181, 185, 184, 187])
                plt.scatter(x, y_squat, label='Squat', color=colors_dict['Squat'])
                plt.plot(x, np.poly1d(np.polyfit(x, y_squat, 1))(x), color=colors_dict['Squat'], linestyle='--')
                
                y_bench = np.array([120, 121, 122, 122.5, 123.5, 125])
                plt.scatter(x, y_bench, label='Bench Press', color=colors_dict['Bench Press'])
                plt.plot(x, np.poly1d(np.polyfit(x, y_bench, 1))(x), color=colors_dict['Bench Press'], linestyle='--')
                
                y_dead = np.array([210, 215, 213, 218, 220, 224])
                plt.scatter(x, y_dead, label='Deadlift', color=colors_dict['Deadlift'])
                plt.plot(x, np.poly1d(np.polyfit(x, y_dead, 1))(x), color=colors_dict['Deadlift'], linestyle='--')
                
                plt.title('e1RM Trajectory (45 Days) - Demo')
                plt.xlabel('Days from Start of Block')
                plt.ylabel('e1RM (kg)')
                plt.legend()
                plt.savefig('artifacts/temp_e1rm_plot.png', bbox_inches='tight')
                plt.close()
                print("Demo charts generated successfully.")
            
            generate_dummy_charts()
    except Exception as e:
        print("Warning: Failed to generate initial charts:", e)

    print("Starting Lifty OS Web Console on http://127.0.0.1:8000")
    uvicorn.run("ui_server:app", host="127.0.0.1", port=8000, log_level="info")
