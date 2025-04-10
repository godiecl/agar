import os
import re

import pandas as pd
import spacy
from flask import Flask, request, render_template, redirect, url_for, session, send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Definir el nombre del archivo predefinido
PREDEFINED_FILE = "requisitos.xlsx"

# Definitions for ambiguous terms and suggestions
ambiguous_words = {
    "Unclear terms": [
        "TBD", "etc", "unknown", "various", "undetermined", "other", "different",
        "variable", "some", "several"
    ],
    "Vague expressions": [
        "accurate", "appropriate", "easy", "efficient", "essential",
        "immediately", "minimum", "maximum", "periodically", "sufficient",
        "user-friendly", "many", "few", "also", "even", "not", "otherwise",
        "else", "if not", "until", "during", "through", "after", "at", "possibility",
        "could", "should", "might", "usually", "normally", "actually",
        "100%", "fast", "every", "effective", "reliable", "user-centric",
        "user-oriented", "relevant", "preferred", "best", "optimal",
        "desirable", "feasible", "eventually", "sooner", "later", "shortly",
        "promptly", "as soon as possible", "a few", "a lot", "plenty",
        "limited", "numerous", "if applicable", "if necessary", "if possible",
        "unless stated otherwise", "manage", "handle", "process", "ensure",
        "facilitate", "allow", "provide", "support", "consider", "better",
        "approximately", "satisfactory", "scalable", "interactive", "secure", "expected",
        "may be", "posibiliity"

    ],
    "Adjectives": [
        "beautiful", "critical", "helpful", "normal", "acceptable",
        "important", "necessary", "complete", "simple", "flexible",
        "powerful", "robust", "dynamic", "intelligent", "general",
        "standard", "basic", "advanced", "additional", "exclusive",
        "primary", "secondary", "initial", "final", "optimized",
        "user-centric", "secure", "interactive", "generalized", "ideally"
    ],
    "Adverbs": [
        "quickly", "slowly", "carefully", "easily", "totally",
        "frequently", "occasionally", "sometimes", "seldom",
        "rarely", "often", "always", "appropriately", "adequately",
        "correctly", "clearly", "precisely", "generally", "potentially",
        "reasonably", "commonly", "readily", "immediately", "extensively",
        "merely", "lightly"
    ]
}

ambiguity_explanations = {
    "Unclear terms": "These terms are too vague or undefined, making it difficult to determine the intended meaning or scope.",
    "Vague expressions": "These expressions lack precision, leading to multiple interpretations or miscommunication.",
    "Adjectives": "Subjective descriptors that vary based on individual perception and lack measurable criteria.",
    "Adverbs": "Modifiers that introduce uncertainty by failing to define exact specifications or thresholds.",

}

suggestions = {
    "appropriate": "Define what 'appropriate' means with specific criteria or examples.",
    "fast": "Provide a measurable definition, e.g., 'respond within a specific timeframe'.",
    "accurate": "Clarify the acceptable range of error or precision for 'accurate'.",
    "periodically": "Specify the interval or frequency, e.g., 'every 6 hours' or 'weekly'.",
    "not": "Clearly state what is unavailable or restricted, avoiding general negations.",
    "user-friendly": "Describe the exact characteristics that make it user-friendly, such as ease of navigation or minimal learning time.",
    "efficient": "Provide a measurable standard, e.g., 'process 1,000 transactions per minute'.",
    "secure": "Specify the required level of security or protocols to be implemented.",
    "interactive": "Define what 'interactive' entails, e.g., 'enables real-time updates and feedback'.",
    "manage": "Clearly state the scope of 'manage', e.g., 'track, allocate, and report resources'."
}

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def save_dataframe_to_excel(df, filename):
    """Guarda un DataFrame en un archivo Excel en la carpeta de uploads."""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df.to_excel(file_path, index=False, engine='openpyxl')
    return file_path


def determine_severity(category):
    if category in ["Unclear terms", "Vague expressions"]:
        return "High"
    elif category in ["Adjectives", "Adverbs"]:
        return "Medium"
    return "Low"


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Carga automáticamente el archivo 'Requisitos.xlsx' y guarda la información del usuario antes de avanzar."""
    file_path = os.path.join(os.getcwd(), PREDEFINED_FILE)

    if not os.path.exists(file_path):
        return "Error: El archivo 'requisitos.xlsx' no se encontró en la carpeta raíz del proyecto.", 404

    # Leer el archivo Excel automáticamente
    df = pd.read_excel(file_path)
    session['uploaded_data'] = df.to_dict()
    session['current_index'] = 0
    session['user_judgments'] = []
    session['modifications'] = []

    if request.method == 'POST':
        # Guardar datos del usuario en la sesión
        session['user_info'] = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'education_level': request.form.get('education_level'),
            'software_knowledge': request.form.get('software_knowledge'),
            'requirements_knowledge': request.form.get('requirements_knowledge')
        }

        return redirect(url_for('instructions'))  # Redirigir a instrucciones

    return render_template('upload.html', file_loaded=True)


@app.route('/instructions', methods=['GET', 'POST'])
def instructions():
    if request.method == 'POST':
        return redirect(url_for('first_stage'))  # Continuar al análisis después de las instrucciones
    return render_template('instructions.html')  # Mostrar instrucciones detalladas


@app.route('/first_stage', methods=['GET', 'POST'])
def first_stage():
    if 'uploaded_data' not in session:
        return redirect(url_for('upload_file'))

    data = pd.DataFrame(session['uploaded_data'])
    current_index = session.get('current_index', 0)
    user_judgments = session.get('user_judgments', [])

    ambiguity_levels = {
        "None": "No Ambiguity",
        "Low": "Low Ambiguity",
        "Medium": "Medium Ambiguity",
        "High": "High Ambiguity"
    }

    if request.method == 'POST':
        ambiguity_level_key = request.form.get('ambiguity_level')  # Captura la clave del nivel de ambigüedad
        ambiguity_level_text = ambiguity_levels.get(ambiguity_level_key,
                                                    "No Ambiguity")  # Obtiene el texto correspondiente

        user_judgments.append({
            'Requirement': data.iloc[current_index]['Requirement'],
            'Ambiguity Level': ambiguity_level_text
        })
        session['user_judgments'] = user_judgments

        if current_index + 1 < len(data):
            session['current_index'] = current_index + 1
            return redirect(url_for('first_stage'))
        else:
            session['current_index'] = 0
            save_dataframe_to_excel(pd.DataFrame(user_judgments), 'user_judgments.xlsx')
            return redirect(url_for('process_file'))

    current_req = data.iloc[current_index]['Requirement']
    return render_template('first_stage.html', current_req=current_req)


@app.route('/process', methods=['GET', 'POST'])
def process_file():
    if 'uploaded_data' not in session:
        return redirect(url_for('upload_file'))

    data = pd.DataFrame(session['uploaded_data'])
    current_index = session.get('current_index', 0)
    modifications = session.get('modifications', [])

    detected_terms = {}

    if request.method == 'POST':
        original_req = data.iloc[current_index]['Requirement']
        edit_option = request.form.get('edit_option')
        modified_req = original_req

        # Detect ambiguous terms
        for category, terms in ambiguous_words.items():
            for term in terms:
                term_pattern = rf'\b{re.escape(term)}\b'
                matches = re.findall(term_pattern, original_req, re.IGNORECASE)
                for match in matches:
                    if match.lower() not in detected_terms:
                        detected_terms[match.lower()] = category

        if edit_option == 'term':
            for term, category in detected_terms.items():
                input_name = f'input_{current_index}_{term}'
                input_text = request.form.get(input_name, '').strip()
                if input_text:  # solo sustituye si el usuario ingresó texto
                    term_pattern = rf'\b{re.escape(term)}\b'
                    modified_req = re.sub(
                        term_pattern,
                        lambda match: preserve_case(match.group(), input_text),  # Fix aquí
                        modified_req,
                        flags=re.IGNORECASE
                    )
                # Si está vacío (bloqueado), no hacer nada

        elif edit_option == 'requirement':
            modified_req = request.form.get('new_requirement', '').strip()

        modifications.append({
            'Original Requirement': original_req,
            'Modified Requirement': modified_req,
            'Detected Terms': ', '.join(
                [f"{term} ({category})" for term, category in detected_terms.items()]
            ) if detected_terms else "",
            'Edit Option': 'Term Modification' if edit_option == 'term' else 'Full Rewrite'
        })

        session['modifications'] = modifications

        if current_index + 1 < len(data):
            session['current_index'] = current_index + 1
            return redirect(url_for('process_file'))
        else:
            session.pop('current_index', None)
            save_dataframe_to_excel(pd.DataFrame(modifications), 'modifications.xlsx')
            return redirect(url_for('results'))

    original_req = data.iloc[current_index]['Requirement']
    for category, terms in ambiguous_words.items():
        for term in terms:
            term_pattern = rf'\b{re.escape(term)}\b'
            matches = re.findall(term_pattern, original_req, re.IGNORECASE)
            for match in matches:
                if match.lower() not in detected_terms:
                    detected_terms[match.lower()] = category

    term_data = []
    for term, category in detected_terms.items():
        term_data.append({
            'term': term,
            'index': current_index,
            'requisito': original_req,
            'category': category,
            'explanation': ambiguity_explanations.get(category, "No explanation available."),
            'suggestion': suggestions.get(term.lower(), "Provide a clearer alternative.")
        })

    return render_template('process.html', term_data=term_data, original_req=original_req)


def preserve_case(original, replacement):
    if original.isupper():
        return replacement.upper()
    elif original.islower():
        return replacement.lower()
    elif original.istitle():
        return replacement.capitalize()
    return replacement


@app.route('/results', methods=['GET', 'POST'])
def results():
    user_info = session.get('user_info', {})
    filename = f"{user_info.get('first_name', 'user')}_results.xlsx"
    file_path = os.path.join(os.getcwd(), 'downloads', filename)

    user_judgments = pd.DataFrame(session.get('user_judgments', []))
    modifications = pd.DataFrame(session.get('modifications', []))

    feedback_text = "No comments provided."

    if request.method == 'POST':
        feedback = request.form.get('feedback', '').strip()
        feedback_text = feedback if feedback else "No comments provided."
        session['feedback'] = feedback_text

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            pd.DataFrame([user_info]).to_excel(writer, sheet_name='User Information', index=False)
            user_judgments.to_excel(writer, sheet_name='First Stage Analysis', index=False)
            modifications.to_excel(writer, sheet_name='Second Stage Analysis', index=False)
            pd.DataFrame([{'User Feedback': feedback_text}]).to_excel(writer, sheet_name='Feedback', index=False)

        session['download_file'] = filename

        return redirect(url_for('thank_you'))  # Va directo a la vista de agradecimiento

    session['download_file'] = filename

    return render_template(
        'results.html',
        user_judgments_table=user_judgments.to_html(index=False, classes="table table-striped table-bordered"),
        modifications_table=modifications.to_html(index=False, classes="table table-striped table-bordered"),
        download_filename=filename
    )


@app.route('/thank_you')
def thank_you():
    filename = session.get('download_file', None)
    return render_template('thank_you.html', filename=filename)


@app.route('/save_feedback', methods=['POST'])
def save_feedback():
    feedback = request.form.get('feedback', '')
    session['feedback'] = feedback  # Guarda temporalmente en sesión

    filename = session.get('download_file')
    file_path = os.path.join(os.getcwd(), filename)

    # Abre el archivo Excel existente para añadir la nueva hoja
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
        pd.DataFrame([{'User Feedback': feedback}]).to_excel(writer, sheet_name='Feedback', index=False)

    return redirect(url_for('results'))


@app.route('/download/<filename>')
def download_file(filename):
    # Descargar el archivo desde la carpeta downloads
    file_path = os.path.join(os.getcwd(), 'downloads', filename)
    if not os.path.exists(file_path):
        return f"The file {filename} was not found.", 404
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
