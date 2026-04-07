import os
import re
import sys
from html import escape

import requests
import streamlit as st


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend helpers available when streamlit runs this page directly
    sys.path.append(project_root)

try:
    from backend.services.cvService import compare_matching_methods
except ImportError:
    compare_matching_methods = None


def highlight_keywords(text, keywords):
    # highlight useful keywords inside long text blocks
    if not text:
        return "No text available."

    escaped = [re.escape(keyword) for keyword in keywords]
    if not escaped:
        return text

    pattern = r"(?i)(" + "|".join(escaped) + ")"
    return re.sub(pattern, r"<mark style='background-color:#ffeb3b;'>\1</mark>", text)


def format_skills(skills):
    # show skills in a short readable line
    if not skills:
        return "None"
    return ", ".join(skills)


def shorten_text(text, limit=140):
    # keep long text short inside small cards
    if not text:
        return "No explanation available."
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def highlight_matching_skills(text, matching_skills):
    # highlight matched skills in a block of text without breaking other words
    safe_text = escape(text or "")

    for skill in sorted(set(matching_skills or []), key=len, reverse=True):
        escaped_skill = re.escape(skill)
        pattern = re.compile(rf"(?<!\w)({escaped_skill})(?!\w)", re.IGNORECASE)
        safe_text = pattern.sub(r"<mark>\1</mark>", safe_text)

    return safe_text


def unique_by_id(items, id_key):
    # keep only one item for each id
    unique_items = []
    seen_ids = set()

    for item in items:
        item_id = item.get(id_key)
        if item_id in seen_ids:
            continue

        seen_ids.add(item_id)
        unique_items.append(item)

    return unique_items


def fetch_json(url, headers=None, timeout=20):
    # load json from the backend in a simple way
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json(), None
        return None, response.text
    except requests.RequestException:
        return None, "Backend unavailable."


def load_resume_matches(backend_url, headers, resume_id):
    # load detailed matches for one resume and keep the response shape consistent
    matches_data, matches_error = fetch_json(
        f"{backend_url}/matches/search/{resume_id}",
        headers=headers,
    )

    if matches_error:
        return [], matches_error

    return unique_by_id(matches_data or [], "job_id"), None


def get_latest_resume_id_with_matches(top_matches, resume_id_by_filename):
    # choose the most recent resume that already has stored matches
    latest_resume_id = None
    latest_generated_at = ""

    for top_match in top_matches:
        resume_name = top_match.get("resume")
        resume_id = resume_id_by_filename.get(resume_name)
        generated_at = str(top_match.get("generated_at", ""))

        if not resume_id:
            continue

        if generated_at >= latest_generated_at:
            latest_generated_at = generated_at
            latest_resume_id = resume_id

    return latest_resume_id


def replace_current_match_results(resume_id, matches, match_error=None):
    # replace old match state so every tab reads the same fresh results
    cleaned_matches = unique_by_id(matches or [], "job_id")

    st.session_state["search_resume_id"] = resume_id
    st.session_state["search_matches"] = cleaned_matches
    st.session_state["match_load_error"] = match_error

    if cleaned_matches:
        best_match = sort_matches(cleaned_matches)[0]
        st.session_state["compare_job_id"] = best_match.get("job_id")
        st.session_state["skill_analysis_match_selector"] = best_match
    else:
        st.session_state["compare_job_id"] = None
        st.session_state["skill_analysis_match_selector"] = None


def sort_matches(matches):
    # keep the shared match list in one consistent order
    return sorted(
        matches,
        key=get_match_sort_score,
        reverse=True,
    )


def get_match_sort_score(match):
    # sort by the true stored final score used across the portal
    if not match:
        return 0.0

    if match.get("final_score") is not None:
        return float(match.get("final_score", 0.0))

    if match.get("score") is not None:
        return float(match.get("score", 0.0))

    return float(match.get("percentage_score", 0)) / 100.0


def get_selected_match(matches, selected_job_id):
    # read the selected job directly from the shared match list
    sorted_matches = sort_matches(matches)

    if not sorted_matches:
        return None

    for match in sorted_matches:
        if match.get("job_id") == selected_job_id:
            return match

    return sorted_matches[0]


def get_score_display(match):
    # format the final backend score fields the same way in every tab
    if not match:
        return {
            "percentage_score": "0%",
            "rating_score": "0/10",
            "match_label": "No label",
        }

    return {
        "percentage_score": f"{match.get('percentage_score', 0)}%",
        "rating_score": f"{match.get('rating_score', 0)}/10",
        "match_label": match.get("match_label", "No label"),
    }


def build_skill_improvement_suggestions(missing_skills):
    # turn missing skills into simple cv improvement advice
    suggestion_lines = []

    for skill in missing_skills[:3]:
        lowered_skill = skill.lower()

        if lowered_skill == "communication":
            suggestion_lines.append("Add examples of communication in your experience section.")
        elif lowered_skill == "problem solving":
            suggestion_lines.append("Strengthen your CV with examples of problem solving.")
        elif lowered_skill == "office tools":
            suggestion_lines.append("Mention office tools if you have used them in class, work, or projects.")
        else:
            suggestion_lines.append(f"Add clear evidence of {skill} if you have used it in your work, projects, or studies.")

    if not suggestion_lines:
        suggestion_lines.append("Your current CV already covers the main skill gaps for this job.")

    return suggestion_lines


def summary_card(title, value, text):
    # build a simple dashboard summary card
    return f"""
    <div style="
        background:#ffffff;
        border:1px solid #e5e7eb;
        border-radius:14px;
        padding:1rem 1.1rem;
        min-height:122px;
        text-align:left;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
    ">
        <div style="
            font-size:0.78rem;
            text-transform:uppercase;
            letter-spacing:0.08em;
            color:#6b7280;
            margin-bottom:0.55rem;
            min-height:1.2rem;
        ">{title}</div>
        <div style="
            font-size:1.85rem;
            font-weight:700;
            color:#111827;
            margin-bottom:0.35rem;
            line-height:1.1;
        ">{value}</div>
        <div style="
            font-size:0.9rem;
            color:#6b7280;
            line-height:1.35;
            min-height:2.4rem;
        ">{text}</div>
    </div>
    """


# load shared css file
css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "styles.css")
with open(css_path, encoding="utf-8") as file:
    st.markdown(f"<style>{file.read()}</style>", unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        mark {
            background-color: #ffe066;
            padding: 2px 4px;
            border-radius: 4px;
            font-weight: 500;
        }

        .text-box {
            background: #ffffff;
            padding: 16px;
            border-radius: 10px;
            border: 1px solid #ddd;
            color: #222;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# set page settings
st.set_page_config(page_title="Job Seeker Portal", page_icon="briefcase", layout="wide")
backend_url = "http://127.0.0.1:8000"


# block page if user is not logged in
if "token" not in st.session_state or st.session_state["token"] is None:
    st.warning("Please log in first.")
    st.stop()

# block page if logged user is not a job seeker
if st.session_state.get("role") != "job_seeker":
    st.error("Access denied.")
    st.stop()


token = st.session_state["token"]
headers = {"Authorization": f"Bearer {token}"}

if "search_resume_id" not in st.session_state:
    st.session_state["search_resume_id"] = None
if "search_matches" not in st.session_state:
    st.session_state["search_matches"] = []
if "compare_job_id" not in st.session_state:
    st.session_state["compare_job_id"] = None
if "skill_analysis_match_selector" not in st.session_state:
    st.session_state["skill_analysis_match_selector"] = None
if "skill_analysis_notice" not in st.session_state:
    st.session_state["skill_analysis_notice"] = None
if "latest_upload_status" not in st.session_state:
    st.session_state["latest_upload_status"] = None
if "match_load_error" not in st.session_state:
    st.session_state["match_load_error"] = None


# load shared page data
resumes_data, _ = fetch_json(f"{backend_url}/resumes/", headers=headers)
top_matches_data, top_matches_error = fetch_json(f"{backend_url}/matches/top/", headers=headers)

all_resumes = unique_by_id(resumes_data or [], "id")
all_resumes = sorted(all_resumes, key=lambda item: item.get("filename", "").lower())
shared_matches = unique_by_id(st.session_state.get("search_matches", []), "job_id")
search_resume_id = st.session_state.get("search_resume_id")
top_matches = unique_by_id((top_matches_data or {}).get("top_matches", []), "resume")
top_matches = sorted(
    top_matches,
    key=get_match_sort_score,
    reverse=True,
)
top_matches = top_matches[:5]
resume_id_by_filename = {resume["filename"]: resume["id"] for resume in all_resumes}


if not search_resume_id and not shared_matches:
    latest_resume_id_with_matches = get_latest_resume_id_with_matches(top_matches, resume_id_by_filename)

    if top_matches_error:
        st.session_state["match_load_error"] = top_matches_error
    elif latest_resume_id_with_matches:
        loaded_matches, load_error = load_resume_matches(backend_url, headers, latest_resume_id_with_matches)
        replace_current_match_results(latest_resume_id_with_matches, loaded_matches, load_error)
    else:
        replace_current_match_results(None, [], None)

    shared_matches = unique_by_id(st.session_state.get("search_matches", []), "job_id")
    search_resume_id = st.session_state.get("search_resume_id")


# build summary values for the dashboard
shared_matches = unique_by_id(st.session_state.get("search_matches", []), "job_id")
current_matches = sort_matches(shared_matches)
selected_match = get_selected_match(shared_matches, st.session_state.get("compare_job_id"))

top_match_percentage = current_matches[0].get("percentage_score", 0) if current_matches else 0
all_matching_skills = []
all_missing_skills = []
for match in shared_matches:
    reasoning = match.get("reasoning", {})
    all_matching_skills.extend(reasoning.get("matching_skills", []))
    all_missing_skills.extend(reasoning.get("missing_skills", []))

matching_skills_count = len(set(all_matching_skills))
missing_skills_count = len(set(all_missing_skills))


# page header
with st.container():
    st.title("Job Seeker Dashboard")
    st.markdown(
        "Track your matches, review skill gaps, and understand how your CV fits each role in one clean workspace."
    )

with st.container(border=True):
    # make the upload section feel like the first step of the dashboard
    st.caption("Step 1")
    st.markdown("### Upload Your CV")
    st.markdown("Start by adding your latest CV to refresh your profile and unlock better match insights.")
    st.caption("After upload, your CV is saved, text is extracted from the PDF, and your dashboard can use it for matching and skill analysis.")

    uploaded_file = st.file_uploader("Choose a PDF CV", type=["pdf"], label_visibility="collapsed")

    if uploaded_file:
        with st.container(border=True):
            st.markdown("**Selected File**")
            st.write(uploaded_file.name)

    upload_clicked = st.button("Upload CV", type="primary")

    if upload_clicked:
        if not uploaded_file:
            st.warning("Please choose a PDF CV first.")
        else:
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            response = requests.post(f"{backend_url}/resumes/upload/", headers=headers, files=files)

            if response.status_code == 200:
                upload_result = response.json()
                uploaded_resume_id = upload_result.get("resume_id")
                uploaded_filename = upload_result.get("filename", uploaded_file.name)
                extracted_text_status = "Unknown"

                if uploaded_resume_id:
                    resume_detail, resume_detail_error = fetch_json(
                        f"{backend_url}/resumes/{uploaded_resume_id}",
                        headers=headers,
                    )
                    extracted_text = (resume_detail or {}).get("text_content", "")
                    if resume_detail_error:
                        extracted_text_status = "Saved, but text extraction status could not be checked."
                    elif extracted_text.strip():
                        extracted_text_status = "Text extracted successfully."
                    else:
                        extracted_text_status = "Resume saved, but no extracted text was found."

                st.session_state["latest_upload_status"] = {
                    "filename": uploaded_filename,
                    "resume_id": uploaded_resume_id,
                    "extracted_text_status": extracted_text_status,
                }
                refreshed_matches = []
                refreshed_matches_error = None

                if uploaded_resume_id:
                    refreshed_matches, refreshed_matches_error = load_resume_matches(
                        backend_url,
                        headers,
                        uploaded_resume_id,
                    )

                replace_current_match_results(
                    uploaded_resume_id,
                    refreshed_matches,
                    refreshed_matches_error,
                )
                st.rerun()
            else:
                st.error(f"Upload failed: {response.text}")

    latest_upload_status = st.session_state.get("latest_upload_status")
    if latest_upload_status:
        st.markdown("**Latest Upload Status**")
        with st.container(border=True):
            status_col_1, status_col_2 = st.columns(2, gap="large")

            with status_col_1:
                st.markdown("**Uploaded File**")
                st.write(latest_upload_status.get("filename", "Unknown file"))

            with status_col_2:
                st.markdown("**Extracted Text Status**")
                st.write(latest_upload_status.get("extracted_text_status", "Unknown"))


st.markdown("<div style='height:1.25rem;'></div>", unsafe_allow_html=True)


# main dashboard tabs
dashboard_tab, matches_tab, skills_tab, compare_tab = st.tabs(
    ["Dashboard", "Matches", "Skill Analysis", "Job Comparison"]
)


with dashboard_tab:
    st.markdown("### Overview")
    st.markdown("Use this dashboard to see your summary and top matches at a glance.")

    if st.session_state.get("match_load_error"):
        st.error(st.session_state["match_load_error"])
    elif not shared_matches:
        with st.container(border=True):
            st.markdown("**No Match Results Yet**")
            st.write("Upload your latest CV above to generate job matches for your profile.")
            st.write("After your results are ready, this dashboard will automatically show your summary cards, top matches, and short CV feedback.")
    else:
        # keep the dashboard focused on summary information only
        summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4, gap="medium")

        with summary_col_1:
            st.markdown(
                summary_card("Total Matches", len(shared_matches), "Current unique matches loaded for review."),
                unsafe_allow_html=True,
            )

        with summary_col_2:
            st.markdown(
                summary_card("Top Match", f"{top_match_percentage}%", "Highest Final AI Match in the current results."),
                unsafe_allow_html=True,
            )

        with summary_col_3:
            st.markdown(
                summary_card("Matching Skills", matching_skills_count, "Unique matching skills found across current matches."),
                unsafe_allow_html=True,
            )

        with summary_col_4:
            st.markdown(
                summary_card("Missing Skills", missing_skills_count, "Unique missing skills found across current matches."),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("**Top Matches**")
            st.caption("These are your top 3 matches based on the highest final ai match.")

            for match in current_matches[:3]:
                score_display = get_score_display(match)

                with st.container(border=True):
                    top_card_left, top_card_right = st.columns([2, 1], gap="medium")

                    with top_card_left:
                        st.markdown(f"**{match.get('title', 'Unknown Job')}**")

                    with top_card_right:
                        st.metric("Final AI Match", score_display["percentage_score"])
                        st.caption(score_display["match_label"])

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            # keep this feedback short so it does not overlap with skill analysis
            st.markdown("**Short CV Feedback**")
            feedback_title = selected_match.get("title", "Selected Job")
            feedback_reasoning = selected_match.get("reasoning", {})
            feedback_matching_skills = feedback_reasoning.get("matching_skills", [])
            feedback_missing_skills = feedback_reasoning.get("missing_skills", [])

            if feedback_matching_skills:
                st.write(
                    f"For {feedback_title}, your CV already matches skills like {format_skills(feedback_matching_skills[:3])}."
                )
            else:
                st.write(f"For {feedback_title}, there are no strong matching skills yet.")

            if feedback_missing_skills:
                st.write(
                    f"To improve this match, add clearer evidence of {format_skills(feedback_missing_skills[:3])} if you have used these skills."
                )
            else:
                st.write("You already cover the main extracted skills for this match, so focus on clearer examples and stronger impact.")


with matches_tab:
    st.markdown("### Match Results")
    st.markdown("Review all of your current match results in one place.")

    if not shared_matches:
        st.info("No match results are available yet. Upload your CV to generate matches and view the detailed results here.")
    else:
        for index, match in enumerate(current_matches):
            score_display = get_score_display(match)
            title = match.get("title", "Unknown")
            job_id = match.get("job_id")
            reasoning = match.get("reasoning", {})
            matching_skills = reasoning.get("matching_skills", [])
            missing_skills = reasoning.get("missing_skills", [])
            explanation = reasoning.get("explanation", "No explanation available.")

            with st.container(border=True):
                top_left, top_right = st.columns([2, 1], gap="medium")

                with top_left:
                    st.subheader(title)
                    st.markdown("**Explanation**")
                    st.write(explanation)

                with top_right:
                    st.metric("Final AI Match", score_display["percentage_score"])
                    st.markdown(f"**Match Label:** {score_display['match_label']}")
                    st.caption(f"Rating: {score_display['rating_score']}")

                skills_col_1, skills_col_2 = st.columns(2, gap="large")

                with skills_col_1:
                    with st.container(border=True):
                        st.markdown("**Matching Skills**")
                        if matching_skills:
                            st.write(format_skills(matching_skills))
                        else:
                            st.info("No matching skills were found for this job yet.")

                with skills_col_2:
                    with st.container(border=True):
                        st.markdown("**Missing Skills**")
                        if missing_skills:
                            st.write(format_skills(missing_skills))
                        else:
                            st.success("No missing skills were found for this job.")

                compare_clicked = st.button("Open Skill Analysis", key=f"compare_btn_{index}", type="secondary")

                if compare_clicked:
                    st.session_state["compare_job_id"] = job_id
                    st.session_state["skill_analysis_match_selector"] = match
                    st.session_state["skill_analysis_notice"] = (
                        f"Skill Analysis is ready for {title}. Open the Skill Analysis tab to review it."
                    )
                    st.rerun()


with skills_tab:
    st.markdown("### Skill Analysis")
    st.markdown("Review how your CV matches one selected job, including skills, score, and explanation.")

    if not shared_matches:
        st.info("No matched jobs are available yet. Upload your CV to generate match results and review them here.")
    else:
        skill_review_matches = sorted(
            shared_matches,
            key=lambda item: item.get("title", "").lower(),
        )

        selected_skill_default = get_selected_match(
            shared_matches,
            st.session_state.get("compare_job_id"),
        )
        current_skill_selector = st.session_state.get("skill_analysis_match_selector")
        current_skill_selector_job_id = (current_skill_selector or {}).get("job_id")
        if (
            selected_skill_default
            and current_skill_selector_job_id != selected_skill_default.get("job_id")
        ):
            st.session_state["skill_analysis_match_selector"] = selected_skill_default

        skill_analysis_notice = st.session_state.pop("skill_analysis_notice", None)
        if skill_analysis_notice:
            st.success(skill_analysis_notice)

        default_skill_index = 0
        saved_compare_job_id = st.session_state.get("compare_job_id")
        for index, item in enumerate(skill_review_matches):
            if item.get("job_id") == saved_compare_job_id:
                default_skill_index = index
                break

        selected_skill_match = st.selectbox(
            "Select a matched job to review",
            skill_review_matches,
            index=default_skill_index,
            format_func=lambda item: item.get("title", "Unknown"),
            key="skill_analysis_match_selector",
        )

        selected_job_id = selected_skill_match.get("job_id")
        st.session_state["compare_job_id"] = selected_job_id

        selected_skill_match = get_selected_match(shared_matches, selected_job_id) or {}
        selected_reasoning = selected_skill_match.get("reasoning", {})
        selected_score_display = get_score_display(selected_skill_match)
        selected_matching_skills = selected_reasoning.get("matching_skills", [])
        selected_missing_skills = sorted(set(selected_reasoning.get("missing_skills", [])))
        selected_explanation = selected_reasoning.get("explanation", "No explanation available.")
        improvement_suggestions = build_skill_improvement_suggestions(selected_missing_skills)

        top_skill_col_1, top_skill_col_2 = st.columns(2, gap="large")

        with top_skill_col_1:
            with st.container(border=True):
                st.markdown("**Selected Job**")
                st.write(selected_skill_match.get("title", "Selected Job"))

        with top_skill_col_2:
            with st.container(border=True):
                st.markdown("**Score Summary**")
                st.metric("Final AI Match", selected_score_display["percentage_score"])
                st.markdown(f"**Match Label:** {selected_score_display['match_label']}")
                st.caption(f"Rating: {selected_score_display['rating_score']}")

        middle_skill_col_1, middle_skill_col_2 = st.columns(2, gap="large")

        with middle_skill_col_1:
            with st.container(border=True):
                st.markdown("**Matching Skills**")
                if selected_matching_skills:
                    st.write(format_skills(selected_matching_skills))
                else:
                    st.info("No matching skills were found for this job yet.")

        with middle_skill_col_2:
            with st.container(border=True):
                st.markdown("**Missing Skills**")
                if selected_missing_skills:
                    st.write(format_skills(selected_missing_skills))
                else:
                    st.success("No missing skills were found for the selected job.")

        with st.container(border=True):
            st.markdown("**Improvement Suggestions**")
            if selected_missing_skills:
                for suggestion in improvement_suggestions:
                    st.write(f"- {suggestion}")
            else:
                st.success("Your current skill set already covers the main skill gaps for this job.")

        with st.container(border=True):
            st.markdown("**Explanation**")
            st.write(selected_explanation)


with compare_tab:
    st.markdown("### Job Comparison")
    st.markdown("Review your CV and the selected job description side by side.")
    if not search_resume_id or not shared_matches:
        st.info("No matched jobs are available to compare yet. Upload your CV to generate match results first.")
    else:
        sorted_compare_matches = sorted(
            shared_matches,
            key=lambda item: item.get("title", "").lower(),
        )

        default_compare_index = 0
        saved_compare_job_id = st.session_state.get("compare_job_id")
        for index, item in enumerate(sorted_compare_matches):
            if item.get("job_id") == saved_compare_job_id:
                default_compare_index = index
                break

        selected_compare_match = st.selectbox(
            "Choose a matched job to compare with your CV",
            sorted_compare_matches,
            index=default_compare_index,
            format_func=lambda item: item.get("title", "Unknown"),
        )

        compare_job_id = selected_compare_match.get("job_id")
        st.session_state["compare_job_id"] = compare_job_id

        compare_match_data = get_selected_match(shared_matches, compare_job_id) or {}
        compare_job_title = compare_match_data.get("title", "Selected Job")

        resume_data, resume_error = fetch_json(f"{backend_url}/resumes/{search_resume_id}", headers=headers)
        job_data, job_error = fetch_json(f"{backend_url}/jobs/{compare_job_id}")

        if resume_error:
            st.error(resume_error)
        elif job_error:
            st.error(job_error)
        else:
            resume_text = (resume_data or {}).get("text_content", "")
            job_text = (job_data or {}).get("description", "")
            reasoning = compare_match_data.get("reasoning", {})
            score_display = get_score_display(compare_match_data)
            missing_skills = reasoning.get("missing_skills", [])
            matching_skills = reasoning.get("matching_skills", [])
            explanation = reasoning.get("explanation", "No explanation available.")
            highlighted_resume_text = highlight_matching_skills(resume_text, matching_skills)
            highlighted_job_text = highlight_matching_skills(job_text, matching_skills)

            secondary_scores = None
            if compare_matching_methods and resume_text and job_text:
                secondary_scores = compare_matching_methods(resume_text, job_text)

            summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4, gap="medium")

            with summary_col_1:
                with st.container(border=True):
                    st.markdown("**Final AI Match**")
                    st.metric("Score", score_display["percentage_score"])

            with summary_col_2:
                with st.container(border=True):
                    st.markdown("**ATS Score**")
                    if secondary_scores:
                        st.metric("Score", f"{round(secondary_scores.get('ats_score', 0) * 100)}%")
                    else:
                        st.write("Not available")

            with summary_col_3:
                with st.container(border=True):
                    st.markdown("**TF-IDF Score**")
                    if secondary_scores:
                        st.metric("Score", f"{round(secondary_scores.get('tfidf_score', 0) * 100)}%")
                    else:
                        st.write("Not available")

            with summary_col_4:
                with st.container(border=True):
                    st.markdown("**Match Label**")
                    st.write(score_display["match_label"])
                    st.caption(f"Rating: {score_display['rating_score']}")

            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            compare_text_col_1, compare_text_col_2 = st.columns(2, gap="large")

            with compare_text_col_1:
                with st.container(border=True):
                    st.markdown("**Your CV Text**")
                    if resume_text.strip():
                        st.markdown(
                            f"<div class='text-box'>{highlighted_resume_text}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.info("No CV text is available for this resume yet.")

            with compare_text_col_2:
                with st.container(border=True):
                    st.markdown(f"**Job Description: {compare_job_title}**")
                    if job_text.strip():
                        st.markdown(
                            f"<div class='text-box'>{highlighted_job_text}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.info("No job description text is available for this job yet.")

            st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

            skills_col_1, skills_col_2 = st.columns(2, gap="large")

            with skills_col_1:
                with st.container(border=True):
                    st.markdown("**Matching Skills**")
                    if matching_skills:
                        st.write(format_skills(matching_skills))
                    else:
                        st.info("No matching skills were found for this job.")

            with skills_col_2:
                with st.container(border=True):
                    st.markdown("**Missing Skills**")
                    if missing_skills:
                        st.write(format_skills(missing_skills))
                    else:
                        st.success("No missing skills were found for this job.")


st.markdown("---")


# logout button
if st.button("Logout", type="secondary"):
    # clear login data and send user back to the home page
    st.session_state.clear()
    home_page_path = os.path.join(os.path.dirname(__file__), "home.py")
    st.switch_page(home_page_path)
