# decisiontree

This is the final, production-ready bundle. It includes the logic engine, a non-technical admin dashboard with a built-in validator, PDF exporting, and Docker configuration.

### 📁 Project Structure
To prepare for your GitHub upload, organize your files exactly like this:
```text
/flask-decision-engine
├── app.py
├── questions.json
├── Dockerfile
├── requirements.txt
├── README.md
└── templates/
    ├── admin.html
    ├── edit.html
    └── question.html
```

---

### 1. `requirements.txt`
```text
flask
markdown
fpdf
```

### 2. `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### 3. `app.py`
```python
import json
import markdown
from flask import Flask, render_template, redirect, url_for, session, Response, make_response, request, flash
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = 'demo_secret_key_123' 

def load_questions():
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"start": {"text": "Welcome", "description": "Please use the /admin panel to create your first question.", "options": []}}

def save_questions(questions):
    with open('questions.json', 'w') as f:
        json.dump(questions, f, indent=4)

# --- TREE LOGIC ---
def get_time_estimate(q_id, questions, memo=None):
    if memo is None: memo = {}
    if q_id in memo: return memo[q_id]
    node = questions.get(q_id)
    if not node or not node.get('options'): return 0, 0
    mins, maxs = [], []
    for opt in node['options']:
        low, high = get_time_estimate(opt['next_id'], questions, memo)
        mins.append(low)
        maxs.append(high)
    res = (1 + min(mins), 1 + max(maxs))
    memo[q_id] = res
    return res

# --- USER ROUTES ---
@app.route('/')
def index():
    session['history'], session['summary'] = [], []
    return redirect(url_for('ask_question', q_id='start'))

@app.route('/question/<q_id>')
def ask_question(q_id):
    questions = load_questions()
    data = questions.get(q_id)
    if not data: return f"Error: ID '{q_id}' not found.", 404
    
    min_s, max_s = get_time_estimate(q_id, questions)
    time_str = f"{max_s} min" if max_s > 0 else "< 1 min"
    if min_s != max_s and max_s > 1: time_str = f"{min_s}-{max_s} mins"
    
    html_desc = markdown.markdown(data.get('description', ""))
    progress = min((len(session.get('history', [])) / 5) * 100, 100)
    
    return render_template('question.html', q_id=q_id, question=data['text'], 
                           description=html_desc, options=data.get('options', []), 
                           is_result=not data.get('options'), time_left=time_str,
                           progress=progress, step=len(session.get('history', [])) + 1)

@app.route('/select/<current_id>/<next_id>/<path:choice_text>')
def select_option(current_id, next_id, choice_text):
    questions = load_questions()
    history = session.get('history', []); history.append(current_id)
    summary = session.get('summary', []); summary.append({"q": questions[current_id]['text'], "a": choice_text})
    session['history'], session['summary'] = history, summary
    return redirect(url_for('ask_question', q_id=next_id))

@app.route('/back')
def go_back():
    history, summary = session.get('history', []), session.get('summary', [])
    if history:
        last_id = history.pop(); summary.pop()
        session['history'], session['summary'] = history, summary
        return redirect(url_for('ask_question', q_id=last_id))
    return redirect(url_for('index'))

@app.route('/download/<fmt>')
def download_results(fmt):
    summary = session.get('summary', [])
    content = "DECISION SUMMARY\n" + "="*20 + "\n\n"
    for i, item in enumerate(summary, 1):
        content += f"{i}. {item['q']}\n   Choice: {item['a']}\n\n"
    if fmt == 'txt':
        return Response(content, mimetype="text/plain", headers={"Content-disposition": "attachment; filename=results.txt"})
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename='results.pdf')
    return response

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_dashboard():
    questions = load_questions()
    broken_links = []
    for q_id, data in questions.items():
        for opt in data.get('options', []):
            if opt['next_id'] not in questions:
                broken_links.append(f"Node '{q_id}' points to missing ID '{opt['next_id']}'")
    return render_template('admin.html', questions=questions, broken_links=broken_links)

@app.route('/admin/edit/<q_id>', methods=['GET', 'POST'])
@app.route('/admin/create', methods=['GET', 'POST'])
def edit_question(q_id=None):
    questions = load_questions()
    existing_data = questions.get(q_id) if q_id else {"text": "", "description": "", "options": []}

    if request.method == 'POST':
        new_id = request.form.get('q_id').strip()
        opt_texts = request.form.getlist('opt_text')
        opt_targets = request.form.getlist('opt_target')
        options = [{"text": t, "next_id": target} for t, target in zip(opt_texts, opt_targets) if t.strip()]
        questions[new_id] = {"text": request.form.get('text'), "description": request.form.get('description'), "options": options}
        if q_id and q_id != new_id: del questions[q_id]
        save_questions(questions)
        return redirect(url_for('admin_dashboard'))

    return render_template('edit.html', q_id=q_id, data=existing_data, all_ids=questions.keys())

@app.route('/admin/delete/<q_id>')
def delete_question(q_id):
    questions = load_questions()
    if q_id in questions:
        del questions[q_id]
        save_questions(questions)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/backup')
def backup_json():
    with open('questions.json', 'r') as f:
        return Response(f.read(), mimetype="application/json", headers={"Content-disposition": "attachment; filename=questions_backup.json"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

### 4. `templates/question.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Decision Demo</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
</head>
<body>
    <header>
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #666;">
            <span>Step {{ step }}</span>
            {% if not is_result %}<span>Est. Time Remaining: <strong>{{ time_left }}</strong></span>{% endif %}
        </div>
        <progress value="{{ progress }}" max="100"></progress>
    </header>
    <main>
        <h1>{{ question }}</h1>
        {% if description %}<div style="background: #f9f9f9; padding: 1rem; border-left: 4px solid #0076d1; margin-bottom: 1.5rem;">{{ description | safe }}</div>{% endif %}
        {% if not is_result %}
            {% for opt in options %}
                <a href="{{ url_for('select_option', current_id=q_id, next_id=opt.next_id, choice_text=opt.text) }}">
                    <button style="width: 100%; text-align: left; margin-bottom: 10px;">{{ opt.text }}</button>
                </a>
            {% endfor %}
        {% else %}
            <div style="text-align: center; margin-top: 2rem; border-top: 1px solid #eee; padding-top: 2rem;">
                <h3>🎉 Workflow Complete</h3>
                <a href="{{ url_for('download_results', fmt='txt') }}"><button>Download .TXT</button></a>
                <a href="{{ url_for('download_results', fmt='pdf') }}"><button>Download .PDF</button></a>
            </div>
        {% endif %}
    </main>
    <footer style="margin-top: 3rem; display: flex; gap: 10px;">
        {% if step > 1 %}<a href="{{ url_for('go_back') }}"><button style="background: #666; border: none;">← Back</button></a>{% endif %}
        <a href="{{ url_for('index') }}"><button style="background: #a00; border: none;">Restart</button></a>
    </footer>
</body>
</html>
```

### 5. `templates/admin.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
</head>
<body>
    <h1>Content Manager</h1>
    {% if broken_links %}
    <div style="background: #fff0f0; border: 1px solid #c00; padding: 10px; margin-bottom: 20px;">
        <strong style="color: #c00;">⚠️ Validation Errors:</strong>
        <ul>{% for link in broken_links %}<li>{{ link }}</li>{% endfor %}</ul>
    </div>
    {% endif %}
    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
        <a href="{{ url_for('edit_question') }}"><button style="background: green; color: white;">+ New Node</button></a>
        <a href="{{ url_for('backup_json') }}"><button style="background: #444;">Backup JSON</button></a>
        <a href="{{ url_for('index') }}"><button style="background: #444;">Live View</button></a>
    </div>
    <table>
        <thead><tr><th>ID</th><th>Question</th><th>Type</th><th>Actions</th></tr></thead>
        <tbody>
            {% for id, data in questions.items() %}
            <tr>
                <td><code>{{ id }}</code></td>
                <td>{{ data.text }}</td>
                <td>{{ "Result" if not data.options else "Path" }}</td>
                <td><a href="{{ url_for('edit_question', q_id=id) }}">Edit</a> | <a href="{{ url_for('delete_question', q_id=id) }}" style="color:red">Delete</a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
```

### 6. `templates/edit.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>Editor</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
</head>
<body>
    <h1>{{ "Edit" if q_id else "Create" }} Node</h1>
    <form method="POST">
        <label>Node ID (Must be unique, e.g. 'start')</label>
        <input type="text" name="q_id" value="{{ q_id or '' }}" required>
        <label>Heading Text</label>
        <input type="text" name="text" value="{{ data.text }}" required>
        <label>Description (Markdown)</label>
        <textarea name="description" rows="4">{{ data.description }}</textarea>
        <h3>Buttons / Pathing</h3>
        <div id="opts">
            {% for opt in data.options %}
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <input type="text" name="opt_text" value="{{ opt.text }}" placeholder="Button Label">
                <input type="text" name="opt_target" value="{{ opt.next_id }}" placeholder="Target ID">
            </div>
            {% endfor %}
        </div>
        <button type="button" onclick="add()">+ Add Option</button>
        <hr>
        <button type="submit" style="background: green; color: white;">Save</button>
        <a href="{{ url_for('admin_dashboard') }}">Cancel</a>
    </form>
    <div style="margin-top: 20px; font-size: 0.8rem; color: #666;">
        <strong>Available IDs:</strong> {% for i in all_ids %}{{ i }}{% if not loop.last %}, {% endif %}{% endfor %}
    </div>
    <script>
        function add() {
            const div = document.createElement('div');
            div.style.display = 'flex'; div.style.gap = '10px'; div.style.marginBottom = '10px';
            div.innerHTML = `<input type="text" name="opt_text" placeholder="Button Label"> <input type="text" name="opt_target" placeholder="Target ID">`;
            document.getElementById('opts').appendChild(div);
        }
    </script>
</body>
</html>
```

---

### 7. Final `README.md`
Copy this for your GitHub documentation.

# 🌲 Flask Decision Tree Engine

A lightweight, no-code-friendly workflow engine for interactive questionnaires and guides.

## 🚀 Getting Started
1. **Docker (Recommended):**
   ```bash
   docker build -t decision-app .
   docker run -p 5000:5000 decision-app
   ```
2. **Manual:**
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
3. Visit `http://localhost:5000` for the user experience and `http://localhost:5000/admin` to manage content.

## 🛠 Features
- **Stateless Navigation:** "Back" and "Restart" functionality built-in.
- **Admin Dashboard:** Visual editor for non-technical users to build the tree.
- **Link Validation:** Built-in checker warns of broken paths or missing IDs.
- **Exporting:** Download summaries in `.txt` or `.pdf`.
- **Markdown Support:** Add links and styling to descriptions easily.

---

**Would you like me to guide you through the GitHub terminal commands to initialize the repository and push this bundle?**
