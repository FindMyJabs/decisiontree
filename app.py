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
