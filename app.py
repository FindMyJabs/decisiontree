import json
import markdown
from flask import Flask, render_template, redirect, url_for, session, Response, make_response, request, flash
from fpdf import FPDF
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
s
app = Flask(__name__)
app.secret_key = 'demo_secret_key_123' 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_questions():
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"start": {"text": "Welcome", "description": "Use /admin to create content.", "options": []}}

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
    
    html_desc = markdown.markdown(data.get('description', ""))
    progress = min((len(session.get('history', [])) / 5) * 100, 100)
    
    return render_template('question.html', q_id=q_id, question=data['text'], 
                           description=html_desc, options=data.get('options', []), 
                           is_result=not data.get('options'), progress=progress,
                           step=len(session.get('history', [])) + 1)

@app.route('/select/<current_id>/<next_id>/<path:choice_text>')
def select_option(current_id, next_id, choice_text):
    questions = load_questions()
    # Save to history for 'Back' and summary for 'Download'
    history = session.get('history', []); history.append(current_id)
    summary = session.get('summary', []); summary.append({"q": questions[current_id]['text'], "a": choice_text})
    session['history'], session['summary'] = history, summary
    return redirect(url_for('ask_question', q_id=next_id)    {
      "evidence_node": {
        "text": "Upload your vaccination records",
        "description": "Please upload your vaccination certificate or records.",
        "upload_enabled": true,
        "options": [
          {"text": "Continue", "next_id": "next_step"}
        ]
      }
    })

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
    uploads = session.get('uploads', [])
    
    content = "DECISION SUMMARY\n" + "="*20 + "\n\n"
    for i, item in enumerate(summary, 1):
        content += f"{i}. {item['q']}\n   Choice: {item['a']}\n\n"
    
    if uploads:
        content += "UPLOADED EVIDENCE:\n" + "-"*18 + "\n"
        for upload in uploads:
            content += f"• {upload['original_name']} (for question: {upload['q_id']})\n"
        content += "\n*Note: Files are stored locally and referenced in this summary*\n"
    
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
    lines = ["graph TD"]
    for qid, d in questions.items():
        lines.append(f' {qid}["{d["text"][:30]}..."]')
        for o in d.get('options', []):
            lines.append(f' {qid} -- "{o["text"]}" --> {o["next_id"]}')
    flowchart = "\n".join(lines)
    
    broken_links = [f"'{qid}' links to missing '{o['next_id']}'" 
                    for qid, d in questions.items() 
                    for o in d.get('options', []) if o['next_id'] not in questions]
    return render_template('admin.html', questions=questions, flowchart=flowchart, broken_links=broken_links)

@app.route('/admin/edit/<q_id>', methods=['GET', 'POST'])
@app.route('/admin/create', methods=['GET', 'POST'])
def edit_question(q_id=None):
    questions = load_questions()
    existing_data = questions.get(q_id) if q_id else {"text": "", "description": "", "options": []}

    if request.method == 'POST':
        new_id = request.form.get('q_id').strip()
        texts, targets = request.form.getlist('opt_text'), request.form.getlist('opt_target')
        options = [{"text": t, "next_id": tar} for t, tar in zip(texts, targets) if t.strip()]
        
        questions[new_id] = {"text": request.form.get('text'), "description": request.form.get('description'), "options": options}
        if q_id and q_id != new_id: del questions[q_id]
        save_questions(questions)
        return redirect(url_for('admin_dashboard'))

    return render_template('edit.html', q_id=q_id, data=existing_data, all_ids=sorted(questions.keys()))

@app.route('/admin/clone/<q_id>')
def clone_question(q_id):
    questions = load_questions()
    if q_id in questions:
        new_id = f"{q_id}_copy"
        while new_id in questions: new_id += "_1"
        questions[new_id] = questions[q_id].copy()
        save_questions(questions)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<q_id>')
def delete_question(q_id):
    questions = load_questions()
    if q_id in questions:
        del questions[q_id]
        save_questions(questions)
    return redirect(url_for('admin_dashboard'))

# --- FILE UPLOAD ROUTE ---
@app.route('/upload/<q_id>', methods=['GET', 'POST'])
def upload_file(q_id):
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create unique filename with session ID
            session_id = session.get('session_id', 'default')
            unique_filename = f"{session_id}_{q_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Store file reference in session
            uploads = session.get('uploads', [])
            uploads.append({
                'q_id': q_id,
                'filename': unique_filename,
                'original_name': file.filename
            })
            session['uploads'] = uploads
            
            flash('File uploaded successfully')
            return redirect(url_for('ask_question', q_id=q_id))
    
    return render_template('upload.html', q_id=q_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
