from backend.database import SessionLocal
from backend.models.match_model import Match

# Create a new session
db = SessionLocal()

print("\n🔍 Displaying all matches:\n")

matches = db.query(Match).all()

if not matches:
    print("No matches found in the database.")
else:
    for match in matches:
        print(f"Match ID: {match.id}")
        print(f" Job Seeker: {match.user.name}")
        print(f" Resume: {match.resume.filename}")
        print(f" Job Posting: {match.job_posting.title}")
        print(f" Match Score: {match.match_score}")
        print("-" * 40)

db.close()
