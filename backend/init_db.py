from backend.database import Base, engine
from backend.models import user_model, resume_model, match_model, job_postings_model

print("Creating database tables.")
Base.metadata.create_all(bind=engine)
print("All tables created successfully.")
