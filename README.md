My project, AI Career Advisor, is an AI-driven web application that supports both job seekers and recruiters.

For jobseekers, the idea is that they can upload their CV and the system will analyse the CV with Natural Language Processing to extract key information such as key skills, education and work experience. It will then compare that to job descriptions from the job market and give them feedback, like what roles they might fit into, what skills they’re missing and what areas they could improve in.

On the recruiter side of the applications, they will be able to upload job postings for the system to learn from and use as recommendations and also upload multiple CVs to be analysed. The AI will automatically summarize and visualise key information from each CV which are skills, experience, fit score, etc. in a dashboard with an option to shortlist that application.

The goal is to make recruitment and job seeking more transparent, ethical and data driven, by giving users useful insights into decision making.

The final deliverable will be a working prototype with a functional AI backend, a clean accessible UI and a working dashboard for data visualisation.

Backend Folder
backend/main.py

This is the entry point for the backend API. It starts the FastAPI server, loads the routes, and enables communication between the frontend and the backend.

backend/database/

Stores everything related to application data storage.

database.py
Sets up the database connection and creates the tables. Handles communication with the SQLite database file.

models.py
Defines the structure of database tables, for example resumes, job posts or extracted text chunks. This is where SQLAlchemy models live.

backend/routers/

Contains route handlers for different features of the backend.

resume_router.py
Contains the endpoints for uploading, storing and processing resumes.

job_router.py
Contains the endpoints for uploading job descriptions and returning matched candidates.

analysis_router.py
Contains the endpoints that run AI processing, such as generating summaries, extracting skills or performing job matching.

backend/services/

Contains the logic that the routers call. These files do the heavy lifting.

nlp_service.py
Handles natural language processing such as extracting skills, experience or generating summaries.

matching_service.py
Responsible for comparing applicant CVs with job descriptions and generating match scores.

file_service.py
Manages file uploads and temporary storage for the resumes.

backend/utils/

Small helper functions used across the backend.

parsers.py
Extracts text from PDFs, Word documents or other resume formats.

helpers.py
Shared utility functions, for example cleaning text, formatting output or checking file types.

Frontend Folder
frontend/app.py

The main entry point for the Streamlit interface. This file controls page navigation and UI structure.

frontend/pages/

Contains each page of the web app, shown separately in Streamlit.

Home.py
The landing page users see first. Introduces the system and provides navigation.

Login.py
Page where recruiters or job seekers log into the system.

Register.py
Page that allows new users to create an account.

Upload_CV.py
Page for job seekers to upload their resume to be analysed.

Job_Postings.py
Page for recruiters to upload job descriptions.

Analysis_Results.py
Shows the AI’s extracted skills, summaries and feedback after a CV is uploaded.

Recruiter_Dashboard.py
Displays candidate scores, sorted lists and match visualisations for recruiters.

frontend/components/

Reusable UI components shared across different pages.

navbar.py
Controls the navigation bar at the top of each page.

cards.py
Contains small UI widgets that show results like extracted skills, match scores or job summaries.

frontend/assets/

Stores static UI resources.

styles.css
Styles the Streamlit pages, giving them custom colours, spacing and layout.

images/
Contains icons, logos and illustrations displayed across the pages.
