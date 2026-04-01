"""
Run once to seed the skills taxonomy:
    python seed_skills.py
"""

import asyncio
from database import AsyncSessionLocal, create_tables
from models.skill import Skill, SkillDomain


SKILLS = [
    # Engineering
    ("Python",                "Backend",      SkillDomain.engineering),
    ("JavaScript",            "Frontend",     SkillDomain.engineering),
    ("TypeScript",            "Frontend",     SkillDomain.engineering),
    ("React",                 "Frontend",     SkillDomain.engineering),
    ("Next.js",               "Frontend",     SkillDomain.engineering),
    ("Node.js",               "Backend",      SkillDomain.engineering),
    ("FastAPI",               "Backend",      SkillDomain.engineering),
    ("Django",                "Backend",      SkillDomain.engineering),
    ("PostgreSQL",            "Database",     SkillDomain.engineering),
    ("MongoDB",               "Database",     SkillDomain.engineering),
    ("Redis",                 "Infrastructure", SkillDomain.engineering),
    ("Docker",                "DevOps",       SkillDomain.engineering),
    ("Kubernetes",            "DevOps",       SkillDomain.engineering),
    ("AWS",                   "Cloud",        SkillDomain.engineering),
    ("Machine Learning",      "AI/ML",        SkillDomain.engineering),
    ("Deep Learning",         "AI/ML",        SkillDomain.engineering),
    ("LLM Integration",       "AI/ML",        SkillDomain.engineering),
    ("React Native",          "Mobile",       SkillDomain.engineering),
    ("Swift",                 "Mobile",       SkillDomain.engineering),
    ("Kotlin",                "Mobile",       SkillDomain.engineering),
    ("Go (Golang)",           "Backend",      SkillDomain.engineering),
    ("Rust",                  "Systems",      SkillDomain.engineering),
    ("SQL",                   "Database",     SkillDomain.engineering),
    ("GraphQL",               "API",          SkillDomain.engineering),
    ("REST API Design",       "API",          SkillDomain.engineering),

    # Design
    ("Figma",                 "UI/UX Tools",  SkillDomain.design),
    ("Adobe XD",              "UI/UX Tools",  SkillDomain.design),
    ("Sketch",                "UI/UX Tools",  SkillDomain.design),
    ("UI Design",             "Visual",       SkillDomain.design),
    ("UX Research",           "Research",     SkillDomain.design),
    ("Design Systems",        "Systems",      SkillDomain.design),
    ("Interaction Design",    "UX",           SkillDomain.design),
    ("Motion Design",         "Visual",       SkillDomain.design),
    ("Brand Identity",        "Branding",     SkillDomain.design),
    ("Typography",            "Visual",       SkillDomain.design),
    ("Prototyping",           "Process",      SkillDomain.design),
    ("User Testing",          "Research",     SkillDomain.design),
    ("Accessibility Design",  "Standards",    SkillDomain.design),
    ("Illustration",          "Visual",       SkillDomain.design),
    ("3D Design",             "Visual",       SkillDomain.design),

    # Business
    ("Market Research",       "Strategy",     SkillDomain.business),
    ("Go-To-Market Strategy", "Strategy",     SkillDomain.business),
    ("Financial Modeling",    "Finance",      SkillDomain.business),
    ("Pitch Deck Creation",   "Fundraising",  SkillDomain.business),
    ("Business Development",  "Sales",        SkillDomain.business),
    ("Product Management",    "Product",      SkillDomain.business),
    ("Growth Hacking",        "Marketing",    SkillDomain.business),
    ("SEO/SEM",               "Marketing",    SkillDomain.business),
    ("Content Marketing",     "Marketing",    SkillDomain.business),
    ("Sales Strategy",        "Sales",        SkillDomain.business),
    ("Operations",            "Operations",   SkillDomain.business),
    ("Legal/Compliance",      "Legal",        SkillDomain.business),
    ("Fundraising",           "Fundraising",  SkillDomain.business),
    ("Lean Canvas",           "Framework",    SkillDomain.business),
    ("Customer Discovery",    "Framework",    SkillDomain.business),

    # Cross-disciplinary
    ("Agile/Scrum",           "Process",      SkillDomain.cross),
    ("Technical Writing",     "Communication", SkillDomain.cross),
    ("Data Analysis",         "Analytics",    SkillDomain.cross),
    ("Product Strategy",      "Strategy",     SkillDomain.cross),
    ("Public Speaking",       "Communication", SkillDomain.cross),
]


async def seed():
    await create_tables()
    async with AsyncSessionLocal() as db:
        for name, category, domain in SKILLS:
            from sqlalchemy import select
            existing = await db.execute(select(Skill).where(Skill.skill_name == name))
            if not existing.scalar_one_or_none():
                db.add(Skill(skill_name=name, category=category, domain=domain))
        await db.commit()
        print(f"✓ Seeded {len(SKILLS)} skills into taxonomy")


if __name__ == "__main__":
    asyncio.run(seed())
