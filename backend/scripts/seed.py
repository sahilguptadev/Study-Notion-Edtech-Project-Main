"""Fill MongoDB with realistic demo data for every collection and role.

    cd backend
    .venv/bin/python scripts/seed.py                  # seed (refuses if already seeded)
    .venv/bin/python scripts/seed.py --reset          # WIPE every collection, then seed
    .venv/bin/python scripts/seed.py --enroll me@x.com   # also enrol an existing user in a few courses

Uses the same MONGODB_URL as the backend (backend/.env). Deterministic: same data every run.
All seeded accounts share the password  Password@123
"""
import argparse
import asyncio
import random
import sys
import urllib.parse
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from beanie import PydanticObjectId  # noqa: E402

from app import database  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    ALL_MODELS, Category, Course, CourseProgress, Profile, RatingAndReview, Section, SubSection, User,
)
from app.models.base import utcnow  # noqa: E402

PASSWORD = "Password@123"
rnd = random.Random(42)

FIRST = ["Aarav", "Diya", "Rohan", "Meera", "Kabir", "Ananya", "Vihaan", "Isha", "Arjun", "Saanvi", "Reyansh", "Kavya",
         "Ishaan", "Tara", "Aditya", "Nisha", "Dev", "Riya", "Karan", "Pooja", "Neil", "Sara", "Omar", "Leah", "Mateo"]
LAST = ["Sharma", "Verma", "Patel", "Iyer", "Reddy", "Nair", "Gupta", "Mehta", "Singh", "Khan", "Das", "Joshi", "Rao",
        "Kapoor", "Bose", "Menon", "Chopra", "Malhotra", "Ghosh", "Pillai"]
ABOUT = ["Passionate about learning new technologies.", "Career switcher exploring tech.", "Final-year engineering student.",
         "Self-taught developer building side projects.", "Love turning ideas into working software.",
         "Preparing for interviews and upskilling.", "Hobbyist who enjoys solving problems."]
INSTRUCTOR_ABOUT = ["10+ years in the industry, now teaching full time.", "Ex-FAANG engineer who loves mentoring.",
                    "Built products used by millions; here to share the playbook.", "Bootcamp lead and open-source contributor.",
                    "Consultant and conference speaker.", "Principal engineer turned educator."]

VIDEOS = [  # (url, seconds-ish placeholder). Real clips are short; durations below are shown in the UI.
    "https://res.cloudinary.com/demo/video/upload/dog.mp4",
    "https://res.cloudinary.com/demo/video/upload/elephants.mp4",
    "https://res.cloudinary.com/demo/video/upload/sea_turtle.mp4",
    "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
]

# category -> (description, section pool [(section name, [lectures])])
CATALOG = {
    "Web Development": ("Build modern websites and web apps.", [
        ("HTML & CSS Foundations", ["Tags and elements", "Box model and layout", "Flexbox in practice", "Responsive design"]),
        ("JavaScript Essentials", ["Variables and types", "Functions and scope", "DOM manipulation", "Async and promises"]),
        ("Working with APIs", ["Fetch and JSON", "REST principles", "Error handling", "Authentication basics"]),
        ("Frameworks & Tooling", ["Components and props", "State management", "Routing", "Build and deploy"]),
        ("Capstone Project", ["Planning the app", "Building the UI", "Connecting the backend", "Launch checklist"]),
    ], [("The Complete Web Developer Bootcamp", 799, ["html", "css", "javascript"]),
        ("React from Zero to Hero", 999, ["react", "javascript", "frontend"]),
        ("Node.js and Express Masterclass", 899, ["nodejs", "express", "backend"]),
        ("Full-Stack with the MERN Stack", 1299, ["mern", "mongodb", "fullstack"])]),
    "Data Science": ("Turn data into decisions with Python and ML.", [
        ("Python for Data", ["NumPy arrays", "Pandas dataframes", "Cleaning messy data", "Visualisation with Matplotlib"]),
        ("Statistics Primer", ["Descriptive statistics", "Probability basics", "Hypothesis testing", "Correlation vs causation"]),
        ("Machine Learning", ["Regression", "Classification", "Model evaluation", "Feature engineering"]),
        ("Deep Learning Intro", ["Neural networks", "Training loops", "CNNs", "Transfer learning"]),
        ("Real-World Projects", ["Problem framing", "Exploratory analysis", "Modelling", "Presenting results"]),
    ], [("Python for Data Science", 699, ["python", "pandas", "data"]),
        ("Machine Learning A-Z", 1199, ["ml", "scikit-learn", "python"]),
        ("SQL for Analysts", 499, ["sql", "analytics", "databases"])]),
    "Mobile Development": ("Ship apps to iOS and Android.", [
        ("Getting Started", ["Setting up the toolchain", "Project structure", "Your first screen", "Running on a device"]),
        ("UI Building Blocks", ["Layouts", "Lists and navigation", "Forms and input", "Theming"]),
        ("Data and Networking", ["Local storage", "Calling APIs", "Offline support", "State management"]),
        ("Publishing", ["App signing", "Store listing", "Beta testing", "Release and updates"]),
    ], [("React Native: Build iOS and Android Apps", 999, ["react-native", "mobile", "javascript"]),
        ("Flutter in 30 Days", 899, ["flutter", "dart", "mobile"]),
        ("Android with Kotlin", 849, ["android", "kotlin", "mobile"])]),
    "DevOps and Cloud": ("Automate, deploy and scale reliably.", [
        ("Linux and Shell", ["Filesystem and permissions", "Shell scripting", "Processes and services", "Networking tools"]),
        ("Containers", ["Docker images", "Compose multi-service apps", "Registries", "Container security"]),
        ("CI/CD", ["Pipelines as code", "Automated testing", "Deployment strategies", "Rollbacks"]),
        ("Cloud Foundations", ["Compute and storage", "Networking and IAM", "Monitoring", "Cost control"]),
    ], [("Docker and Kubernetes Essentials", 1099, ["docker", "kubernetes", "devops"]),
        ("AWS Cloud Practitioner Prep", 749, ["aws", "cloud", "certification"]),
        ("CI/CD with GitHub Actions", 599, ["cicd", "github", "automation"])]),
    "UX Design": ("Design products people love to use.", [
        ("Design Principles", ["Hierarchy and contrast", "Typography", "Colour theory", "Spacing and grids"]),
        ("User Research", ["Interviews", "Personas", "Journey maps", "Usability testing"]),
        ("Prototyping", ["Wireframes", "Components in Figma", "Interactive prototypes", "Design handoff"]),
        ("Design Systems", ["Tokens", "Component libraries", "Documentation", "Governance"]),
    ], [("UI/UX Design Fundamentals", 649, ["ux", "ui", "design"]),
        ("Figma for Beginners", 399, ["figma", "prototyping", "design"])]),
    "Cybersecurity": ("Protect systems and learn to think like an attacker.", [
        ("Security Foundations", ["The CIA triad", "Threat modelling", "Cryptography basics", "Secure authentication"]),
        ("Web Application Security", ["OWASP Top 10", "Injection attacks", "XSS and CSRF", "Secure headers"]),
        ("Network Security", ["Firewalls", "TLS in depth", "Intrusion detection", "VPNs"]),
        ("Hands-on Labs", ["Setting up a lab", "Reconnaissance", "Exploitation basics", "Writing a report"]),
    ], [("Ethical Hacking for Beginners", 899, ["security", "hacking", "networking"]),
        ("Web Security and the OWASP Top 10", 749, ["owasp", "websecurity", "appsec"])]),
}

REVIEWS = {
    5: ["Excellent course, explained very clearly!", "Best money I've spent on learning this year.",
        "Loved the hands-on projects. Highly recommended.", "The instructor is fantastic and the pacing is perfect."],
    4: ["Really good content, a few lectures could go deeper.", "Great for beginners, well structured.",
        "Solid course. Learned a lot and built something real."],
    3: ["Decent overview but I wanted more advanced topics.", "Okay course, audio quality could be better."],
}
INSTRUCTIONS = ["A laptop with internet access", "No prior experience needed", "Willingness to practise daily",
                "Basic computer skills", "A free GitHub account"]
LEARN = ["You will be able to build real-world projects from scratch, understand the core concepts deeply, and apply them "
         "confidently in your career."]


def avatar(first, last):
    return "https://api.dicebear.com/5.x/initials/svg?seed=" + urllib.parse.quote(f"{first} {last}")


def thumb(title):
    text = urllib.parse.quote_plus(title)
    return f"https://placehold.co/640x360/161D29/FFD60A/png?text={text}"


def past(days_max, days_min=0):
    return utcnow() - timedelta(days=rnd.uniform(days_min, days_max), seconds=rnd.uniform(0, 80000))


async def wipe():
    for model in ALL_MODELS:
        await model.get_motor_collection().delete_many({})


async def main(reset: bool, enroll_email: str | None):
    await database.connect()
    if reset:
        await wipe()
        print("• wiped all collections")
    elif await User.find_one(User.email == "admin@studynotion.local"):
        print("Already seeded (admin@studynotion.local exists). Use --reset to wipe and reseed.")
        return
    pw_hash = await hash_password(PASSWORD)

    # ── users + profiles ────────────────────────────────────────────────
    async def make_user(first, last, email, role, about, created):
        profile = Profile(
            gender=rnd.choice(["Male", "Female", "Other"]),
            dateOfBirth=f"{rnd.randint(1980, 2005)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}",
            about=about, contactNumber=float(rnd.randint(7000000000, 9999999999)),
        )
        await profile.insert()
        user = User(firstName=first, lastName=last, email=email, password=pw_hash, accountType=role,
                    additionalDetails=profile.id, image=avatar(first, last), createdAt=created, updatedAt=created)
        await user.insert()
        return user

    admin = await make_user("Admin", "User", "admin@studynotion.local", "Admin", "Platform administrator.", past(365, 200))
    names = [(f, l) for f in FIRST for l in LAST]
    rnd.shuffle(names)
    instructors = [await make_user(*names[i], f"instructor{i + 1}@studynotion.local", "Instructor",
                                   INSTRUCTOR_ABOUT[i % len(INSTRUCTOR_ABOUT)], past(300, 150)) for i in range(6)]
    students = [await make_user(*names[10 + i], f"student{i + 1}@studynotion.local", "Student",
                                rnd.choice(ABOUT), past(140, 1)) for i in range(30)]

    # ── categories, courses, sections, lectures ────────────────────────────
    categories, courses, lecture_ids = {}, [], {}
    course_no = 0
    for cat_name, (cat_desc, pool, course_defs) in CATALOG.items():
        cat = Category(name=cat_name, description=cat_desc)
        await cat.insert()
        categories[cat_name] = cat
        for title, price, tags in course_defs:
            instructor = instructors[course_no % len(instructors)]
            course_no += 1
            section_ids, lectures = [], []
            for sec_name, lec_titles in rnd.sample(pool, k=min(len(pool), rnd.randint(3, 4))):
                sub_ids = []
                for lec in lec_titles:
                    sub = SubSection(title=lec, description=f"{lec} — part of '{title}'. Follow along and practise as you watch.",
                                     timeDuration=str(rnd.randint(240, 1500)), videoUrl=rnd.choice(VIDEOS))
                    await sub.insert()
                    sub_ids.append(sub.id)
                    lectures.append(sub.id)
                section = Section(sectionName=sec_name, subSection=sub_ids)
                await section.insert()
                section_ids.append(section.id)
            status = "Draft" if course_no in (5, 13) else "Published"  # a couple of drafts for instructors to finish
            course = Course(
                courseName=title,
                courseDescription=f"{title}: a practical, project-based course taught step by step. "
                                  f"Perfect for learners who want job-ready {cat_name.lower()} skills.",
                instructor=instructor.id, whatYouWillLearn=LEARN[0], courseContent=section_ids,
                price=float(price), thumbnail=thumb(title), tag=tags, category=cat.id,
                instructions=rnd.sample(INSTRUCTIONS, k=3), status=status, createdAt=past(120, 5),
            )
            await course.insert()
            courses.append(course)
            lecture_ids[course.id] = lectures
            cat.courses.append(course.id)
            instructor.courses.append(course.id)
        await cat.save()
    for inst in instructors:
        await inst.save()
    published = [c for c in courses if c.status == "Published"]

    # ── enrolments, progress, reviews ──────────────────────────────────────
    async def enrol(student, course, completed_fraction):
        lectures = lecture_ids[course.id]
        done = lectures[: int(len(lectures) * completed_fraction)]
        progress = CourseProgress(courseID=course.id, userId=student.id, completedVideos=done)
        await progress.insert()
        course.studentsEnroled.append(student.id)
        student.courses.append(course.id)
        student.courseProgress.append(progress.id)

    reviews = 0
    # popular courses get more students
    weights = [3 if i % 3 == 0 else 1 for i in range(len(published))]
    for student in students:
        picks = set()
        while len(picks) < rnd.randint(1, 5):
            picks.add(rnd.choices(range(len(published)), weights)[0])
        for idx in picks:
            course = published[idx]
            frac = rnd.choice([0, 0.25, 0.5, 0.75, 1, 1])
            await enrol(student, course, frac)
            if frac >= 0.5 and rnd.random() < 0.7:
                stars = rnd.choices([5, 4, 3], [6, 3, 1])[0]
                review = RatingAndReview(user=student.id, course=course.id, rating=float(stars), review=rnd.choice(REVIEWS[stars]))
                await review.insert()
                course.ratingAndReviews.append(review.id)
                reviews += 1

    # optionally enrol an existing real account so its dashboard isn't empty
    extra = ""
    if enroll_email:
        me = await User.find_one(User.email == enroll_email)
        if me and me.accountType == "Student":
            for course, frac in zip(rnd.sample(published, 4), [1, 0.5, 0.25, 0]):
                if me.id not in course.studentsEnroled:
                    await enrol(me, course, frac)
                    review = None
                    if frac == 1:
                        review = RatingAndReview(user=me.id, course=course.id, rating=5.0, review="Great course, learned a lot!")
                        await review.insert()
                        course.ratingAndReviews.append(review.id)
                        reviews += 1
            await me.save()
            extra = f" | enrolled {enroll_email} in 4 courses"
        else:
            extra = f" | (--enroll: no Student account with email {enroll_email})"
    for s in students:
        await s.save()
    for c in courses:
        await c.save()

    counts = {m.__name__: await m.count() for m in ALL_MODELS}
    print("✓ seeded:", counts, extra)
    print("\nLogin (password for ALL seeded accounts:", PASSWORD + ")")
    print("  admin       admin@studynotion.local")
    print("  instructors instructor1@studynotion.local … instructor6@studynotion.local")
    print("  students    student1@studynotion.local … student30@studynotion.local")
    print(f"  {len(published)} published courses, {len(courses) - len(published)} drafts, {reviews} reviews")
    await database.disconnect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete ALL data first")
    ap.add_argument("--enroll", metavar="EMAIL", help="also enrol this existing Student in a few courses")
    args = ap.parse_args()
    asyncio.run(main(args.reset, args.enroll))
