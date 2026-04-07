import os
import sys
from contextlib import redirect_stdout
from io import StringIO


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.services.cvService import compare_matching_methods, multi_step_match_analysis


def run_case(name, cv_text, job_text):
    # use the shared scoring helpers so the test matches the real project logic
    method_scores = compare_matching_methods(cv_text, job_text)

    with redirect_stdout(StringIO()):
        analysis = multi_step_match_analysis(
            cv_text,
            job_text,
            embedding_score=method_scores.get("embedding_score", 0.0),
        )

    print(f"\n{name}")
    print(f"ats score: {method_scores.get('ats_score', 0.0):.2f}")
    print(f"tfidf score: {method_scores.get('tfidf_score', 0.0):.2f}")
    print(f"embedding score: {method_scores.get('embedding_score', 0.0):.2f}")
    print(f"final score: {analysis.get('final_score', 0.0):.2f}")
    print(f"match label: {analysis.get('match_label', 'weak match')}")
    print(f"matching skills: {analysis.get('matching_skills', [])}")
    print(f"missing skills: {analysis.get('missing_skills', [])}")


def main():
    # keep the examples small and easy to inspect
    test_cases = [
        {
            "name": "1. strong match",
            "cv_text": (
                "Data analyst with strong Python, SQL, Tableau, Power BI, Excel, "
                "data visualization, machine learning, communication, and teamwork skills."
            ),
            "job_text": (
                "We need a data analyst with Python, SQL, Tableau, Excel, data visualization, "
                "machine learning, communication, and teamwork."
            ),
        },
        {
            "name": "2. moderate match",
            "cv_text": (
                "Business analyst with Excel, SQL, communication, reporting, office tools, "
                "data processing, and customer support experience."
            ),
            "job_text": (
                "Looking for an operations analyst with Excel, SQL, data analysis, "
                "communication, office tools, and problem solving."
            ),
        },
        {
            "name": "3. weak match",
            "cv_text": (
                "Creative photographer with experience in portrait shoots, editing, "
                "lighting, event coverage, and social media content."
            ),
            "job_text": (
                "Hiring an accountant with budgeting, financial reporting, payroll, "
                "tax preparation, Excel, and bookkeeping."
            ),
        },
        {
            "name": "4. semantic match",
            "cv_text": (
                "Worked on analytical reporting, visualisation dashboards, spreadsheet tools, "
                "business reporting, communication skills, and presenting insights to teams "
                "using Tableau and Google Sheets."
            ),
            "job_text": (
                "Role requires data analysis, data visualization, spreadsheet tools, "
                "communication, and business reporting."
            ),
        },
        {
            "name": "5. keyword-heavy misleading match",
            "cv_text": (
                "Python SQL cloud machine learning React FastAPI Excel Tableau. "
                "Keyword summary only with no real examples, no communication, and no teamwork."
            ),
            "job_text": (
                "Senior project coordinator needed with communication, teamwork, leadership, "
                "planning, scheduling, office tools, and stakeholder management."
            ),
        },
    ]

    for case in test_cases:
        run_case(case["name"], case["cv_text"], case["job_text"])


if __name__ == "__main__":
    main()
