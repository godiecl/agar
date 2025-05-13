import os
import re

import pandas as pd
import spacy
from flask import Flask, redirect, render_template, request, send_file, session, url_for

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

# the requirements
PREDEFINED_FILE = "requisitos.xlsx"

# Definitions for ambiguous terms and suggestions
ambiguous_words = {
    "Unclear terms": [
        "TBD",
        "different",
        "etc",
        "other",
        "several",
        "some",
        "undetermined",
        "unknown",
        "variable",
        "various",
    ],
    "Vague expressions": [
        "100%",
        "a few",
        "a lot",
        "accurate",
        "actually",
        "after",
        "allow",
        "also",
        "appropriate",
        "approximately",
        "as soon as possible",
        "at",
        "best",
        "better",
        "consider",
        "could",
        "desirable",
        "during",
        "easy",
        "effective",
        "efficient",
        "else",
        "ensure",
        "essential",
        "even",
        "eventually",
        "every",
        "expected",
        "facilitate",
        "fast",
        "feasible",
        "few",
        "handle",
        "if applicable",
        "if necessary",
        "if not",
        "if possible",
        "immediately",
        "interactive",
        "later",
        "limited",
        "manage",
        "many",
        "maximum",
        "may be",
        "might",
        "minimum",
        "normally",
        "not",
        "numerous",
        "optimal",
        "otherwise",
        "periodically",
        "plenty",
        "posibiliity",
        "possibility",
        "preferred",
        "process",
        "promptly",
        "provide",
        "relevant",
        "reliable",
        "satisfactory",
        "scalable",
        "secure",
        "shortly",
        "should",
        "sooner",
        "sufficient",
        "support",
        "through",
        "unless stated otherwise",
        "until",
        "user-centric",
        "user-friendly",
        "user-oriented",
        "usually",
    ],
    "Adjectives": [
        "acceptable",
        "additional",
        "advanced",
        "basic",
        "beautiful",
        "complete",
        "critical",
        "dynamic",
        "exclusive",
        "final",
        "flexible",
        "general",
        "generalized",
        "helpful",
        "ideally",
        "important",
        "initial",
        "intelligent",
        "interactive",
        "necessary",
        "normal",
        "optimized",
        "powerful",
        "primary",
        "robust",
        "secondary",
        "secure",
        "simple",
        "standard",
        "user-centric",
    ],
    "Adverbs": [
        "adequately",
        "always",
        "appropriately",
        "carefully",
        "clearly",
        "commonly",
        "correctly",
        "easily",
        "extensively",
        "frequently",
        "generally",
        "immediately",
        "lightly",
        "merely",
        "occasionally",
        "often",
        "potentially",
        "precisely",
        "quickly",
        "rarely",
        "readily",
        "reasonably",
        "seldom",
        "slowly",
        "sometimes",
        "totally",
    ],
}

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def save_dataframe_to_excel(df, filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    df.to_excel(file_path, index=False, engine="openpyxl")
    return file_path


@app.route("/", methods=["GET", "POST"])
def upload_file():
    file_path = os.path.join(os.getcwd(), PREDEFINED_FILE)

    if not os.path.exists(file_path):
        return (
            "Error: El archivo 'requisitos.xlsx' no se encontró en la carpeta raíz del proyecto.",
            404,
        )

    df = pd.read_excel(file_path)
    session["uploaded_data"] = df.to_dict()
    session["current_index"] = 0
    session["user_judgments"] = []
    session["modifications"] = []

    if request.method == "POST":
        session["user_info"] = {
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "education_level": request.form.get("education_level"),
            "software_knowledge": request.form.get("software_knowledge"),
            "requirements_knowledge": request.form.get("requirements_knowledge"),
        }
        return redirect(url_for("instructions"))

    return render_template("upload.html", file_loaded=True)


@app.route("/instructions", methods=["GET", "POST"])
def instructions():
    if request.method == "POST":
        return redirect(url_for("first_stage"))
    return render_template("instructions.html")


@app.route("/first_stage", methods=["GET", "POST"])
def first_stage():
    if "uploaded_data" not in session:
        return redirect(url_for("upload_file"))

    data = pd.DataFrame(session["uploaded_data"])
    current_index = session.get("current_index", 0)
    user_judgments = session.get("user_judgments", [])

    ambiguity_levels = {
        "None": "No Ambiguity",
        "Low": "Low Ambiguity",
        "Medium": "Medium Ambiguity",
        "High": "High Ambiguity",
    }

    if request.method == "POST":
        ambiguity_level_key = request.form.get("ambiguity_level")
        ambiguity_level_text = ambiguity_levels.get(ambiguity_level_key, "No Ambiguity")

        user_judgments.append(
            {
                "Requirement": data.iloc[current_index]["Requirement"],
                "Ambiguity Level": ambiguity_level_text,
            }
        )
        session["user_judgments"] = user_judgments

        if current_index + 1 < len(data):
            session["current_index"] = current_index + 1
            return redirect(url_for("first_stage"))
        else:
            session["current_index"] = 0
            save_dataframe_to_excel(pd.DataFrame(user_judgments), "user_judgments.xlsx")
            return redirect(url_for("process_file"))

    current_req = data.iloc[current_index]["Requirement"]
    return render_template("first_stage.html", current_req=current_req)


@app.route("/process", methods=["GET", "POST"])
def process_file():
    if "uploaded_data" not in session:
        return redirect(url_for("upload_file"))

    data = pd.DataFrame(session["uploaded_data"])
    current_index = session.get("current_index", 0)
    modifications = session.get("modifications", [])

    original_req = data.iloc[current_index]["Requirement"]

    # Detectar los términos ambiguos:
    detected_terms = []
    for category, terms in ambiguous_words.items():
        for term in terms:
            term_pattern = rf"\b{re.escape(term)}\b"
            matches = re.findall(term_pattern, original_req, re.IGNORECASE)
            for match in matches:
                if match.lower() not in detected_terms:
                    detected_terms.append(match)

    if request.method == "POST":
        modified_req = request.form.get("modified_requirement", "").strip()
        modifications.append(
            {"Original Requirement": original_req, "Modified Requirement": modified_req}
        )
        session["modifications"] = modifications

        if current_index + 1 < len(data):
            session["current_index"] = current_index + 1
            return redirect(url_for("process_file"))
        else:
            session.pop("current_index", None)
            save_dataframe_to_excel(pd.DataFrame(modifications), "modifications.xlsx")
            return redirect(url_for("results"))

    return render_template(
        "process.html", original_req=original_req, detected_terms=detected_terms
    )


@app.route("/results", methods=["GET", "POST"])
def results():
    user_info = session.get("user_info", {})
    filename = f"{user_info.get('first_name', 'user')}_results.xlsx"
    file_path = os.path.join(os.getcwd(), "downloads", filename)

    user_judgments = pd.DataFrame(session.get("user_judgments", []))
    modifications = pd.DataFrame(session.get("modifications", []))

    if request.method == "POST":
        feedback = request.form.get("feedback", "").strip()
        session["feedback"] = feedback if feedback else "No comments provided."

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            pd.DataFrame([user_info]).to_excel(
                writer, sheet_name="User Information", index=False
            )
            user_judgments.to_excel(
                writer, sheet_name="First Stage Analysis", index=False
            )
            modifications.to_excel(
                writer, sheet_name="Second Stage Analysis", index=False
            )
            pd.DataFrame([{"User Feedback": session["feedback"]}]).to_excel(
                writer, sheet_name="Feedback", index=False
            )

        session["download_file"] = filename
        return redirect(url_for("thank_you"))

    session["download_file"] = filename
    return render_template(
        "results.html",
        user_judgments_table=user_judgments.to_html(
            index=False, classes="table table-striped table-bordered"
        ),
        modifications_table=modifications.to_html(
            index=False, classes="table table-striped table-bordered"
        ),
        download_filename=filename,
    )


@app.route("/thank_you")
def thank_you():
    filename = session.get("download_file", None)
    return render_template("thank_you.html", filename=filename)


@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(os.getcwd(), "downloads", filename)
    if not os.path.exists(file_path):
        return f"The file {filename} was not found.", 404
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
