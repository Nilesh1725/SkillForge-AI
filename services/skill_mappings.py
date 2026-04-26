"""
Deterministic skill synonym / equivalence mappings.

Replaces FAISS char-frequency matching with explicit, curated synonym groups.
Each canonical skill maps to a set of known aliases.  Lookup is O(1) via a
reverse index built at import time.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Canonical skill → aliases
# ──────────────────────────────────────────────

SKILL_SYNONYMS: dict[str, list[str]] = {
    # --- Programming Languages ---
    "Python": ["python3", "python 3", "py"],
    "JavaScript": ["js", "ecmascript", "es6", "es2015", "vanilla js"],
    "TypeScript": ["ts"],
    "Java": [],
    "C++": ["cpp", "c plus plus"],
    "C#": ["csharp", "c sharp", "dotnet", ".net"],
    "R": ["r language", "r programming"],
    "Go": ["golang"],
    "Rust": [],
    "PHP": [],
    "Ruby": [],
    "Swift": [],
    "Kotlin": [],
    "Scala": [],
    "MATLAB": [],

    # --- SQL & Databases ---
    "SQL": [
        "mysql", "postgresql", "postgres", "sqlite", "mssql",
        "sql server", "mariadb", "t-sql", "pl/sql", "plsql",
        "oracle db", "oracle database", "relational database",
        "database management", "rdbms",
    ],
    "NoSQL": ["mongodb", "mongo", "cassandra", "couchdb", "dynamodb", "redis", "firebase"],

    # --- Data Science & ML ---
    "Machine Learning": [
        "ml", "machine-learning", "supervised learning",
        "unsupervised learning", "classification", "regression",
        "clustering", "random forest", "decision tree", "svm",
        "support vector machine", "xgboost", "gradient boosting",
        "ai model", "ai models", "predictive modeling",
        "predictive analytics",
    ],
    "Deep Learning": [
        "dl", "neural network", "neural networks", "cnn", "rnn",
        "lstm", "transformer", "transformers", "gan", "gans",
        "convolutional neural network", "recurrent neural network",
    ],
    "Natural Language Processing": [
        "nlp", "text mining", "text analytics", "sentiment analysis",
        "named entity recognition", "ner", "tokenization",
        "language model", "language models", "llm", "llms",
    ],
    "Computer Vision": [
        "cv", "image processing", "image recognition",
        "object detection", "image classification",
    ],
    "Data Analysis": [
        "data analytics", "data analyst", "exploratory data analysis",
        "eda", "statistical analysis", "business analytics",
    ],
    "Data Science": ["data scientist"],

    # --- Python Data Ecosystem ---
    "Pandas": [],
    "NumPy": ["numpy"],
    "Scikit-Learn": ["sklearn", "scikit learn"],
    "TensorFlow": ["tf"],
    "PyTorch": ["torch"],
    "Keras": [],
    "Matplotlib": [],
    "Seaborn": [],

    # --- Data Visualization ---
    "Data Visualization": [
        "data viz", "data visualisation", "dashboard",
        "dashboards", "charting", "data presentation",
        "business intelligence", "bi",
    ],
    "Tableau": [],
    "Power BI": ["powerbi", "power-bi", "microsoft power bi"],
    "Plotly": [],
    "Grafana": [],

    # --- Spreadsheets ---
    "Excel": [
        "microsoft excel", "ms excel", "spreadsheet",
        "spreadsheets", "xlsx", "pivot table", "pivot tables",
        "vlookup", "xlookup",
    ],
    "Google Sheets": ["gsheets"],

    # --- Web Frameworks ---
    "FastAPI": [],
    "Django": [],
    "Flask": [],
    "Express.js": ["express", "expressjs"],
    "React": ["reactjs", "react.js"],
    "Angular": ["angularjs", "angular.js"],
    "Vue.js": ["vue", "vuejs"],
    "Next.js": ["nextjs", "next"],
    "Node.js": ["nodejs", "node"],
    "Spring Boot": ["spring", "spring framework"],

    # --- Cloud & DevOps ---
    "AWS": [
        "amazon web services", "amazon aws", "ec2", "s3",
        "lambda", "sagemaker", "aws cloud",
    ],
    "Azure": ["microsoft azure", "azure cloud"],
    "GCP": ["google cloud", "google cloud platform"],
    "Docker": ["containerization", "containers", "dockerfile"],
    "Kubernetes": ["k8s"],
    "CI/CD": [
        "cicd", "ci cd", "continuous integration",
        "continuous deployment", "continuous delivery",
        "jenkins", "github actions", "gitlab ci",
    ],
    "Git": ["github", "gitlab", "bitbucket", "version control"],
    "Linux": ["ubuntu", "centos", "debian", "bash", "shell scripting"],
    "Terraform": ["iac", "infrastructure as code"],

    # --- APIs & Communication ---
    "REST API": ["rest", "restful", "restful api", "api development"],
    "GraphQL": [],
    "gRPC": [],

    # --- Testing ---
    "Manual Testing": [
        "test case", "test cases", "test plan", "test plans",
        "functional testing", "regression testing", "qa testing",
        "quality assurance",
    ],
    "Automation Testing": [
        "test automation", "automated testing", "selenium",
        "cypress", "playwright",
    ],
    "JIRA": ["jira software", "atlassian jira"],

    # --- Big Data ---
    "Apache Spark": ["spark", "pyspark"],
    "Hadoop": ["hdfs", "mapreduce"],
    "Apache Kafka": ["kafka"],

    # --- Other Tools ---
    "Jupyter": ["jupyter notebook", "jupyter lab", "ipython"],
    "VS Code": ["visual studio code", "vscode"],
    "Postman": [],
    "Figma": [],
    "Agile": ["scrum", "kanban", "sprint", "agile methodology"],

    # --- Soft Skills ---
    "Problem Solving": [
        "problem-solving", "problem solving skills",
        "analytical problem solving", "complex problem solving",
    ],
    "Critical Thinking": [
        "critical-thinking", "critical thinking skills",
        "analytical thinking",
    ],
    "Communication": [
        "communication skills", "verbal communication",
        "written communication", "interpersonal skills",
        "interpersonal communication",
    ],
    "Teamwork": [
        "team work", "team-work", "team player",
        "team collaboration", "collaborative",
        "cross-functional collaboration",
    ],
    "Leadership": [
        "team leadership", "technical leadership",
        "people management", "team management",
    ],
    "Time Management": [
        "time-management", "time management skills",
        "deadline management", "prioritization",
    ],
    "Adaptability": [
        "flexibility", "adaptable", "quick learner",
        "fast learner", "willingness to learn",
    ],
    "Attention to Detail": [
        "detail-oriented", "detail oriented",
        "meticulous", "thoroughness",
    ],
    "Reporting": [
        "report generation", "report writing",
        "business reporting", "data reporting",
        "generating reports",
    ],
}


# ──────────────────────────────────────────────
#  Reverse index: alias (lower) → canonical name
# ──────────────────────────────────────────────

_REVERSE_INDEX: dict[str, str] = {}


def _build_reverse_index() -> None:
    """Build a reverse lookup from every alias to its canonical skill name."""
    for canonical, aliases in SKILL_SYNONYMS.items():
        key = canonical.lower().strip()
        _REVERSE_INDEX[key] = canonical
        for alias in aliases:
            alias_key = alias.lower().strip()
            if alias_key in _REVERSE_INDEX:
                # First mapping wins — log conflict
                logger.debug(
                    "Alias '%s' already mapped to '%s', skipping '%s'",
                    alias_key, _REVERSE_INDEX[alias_key], canonical,
                )
            else:
                _REVERSE_INDEX[alias_key] = canonical


_build_reverse_index()


# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
#  Base Word Normalization (Safe Modifiers)
# ──────────────────────────────────────────────

SAFE_MODIFIERS = {
    "team", "cross-functional", "skills", "advanced", "basic",
    "tools", "framework", "software", "process", "processes",
    "understanding", "knowledge", "experience"
}

def clean_skill_modifiers(name: str) -> str:
    """
    Remove common safe modifiers from a skill name to extract its base words.
    E.g. 'team collaboration' -> 'collaboration'
         'problem solving skills' -> 'problem solving'
    """
    import re
    s = name.lower().replace("-", " ")
    s = re.sub(r'[^a-z0-9\s]', '', s)
    words = s.split()
    
    cleaned = [w for w in words if w not in SAFE_MODIFIERS]
    if not cleaned:
        return name.strip() # fallback if all words are modifiers
    return " ".join(cleaned)

# ──────────────────────────────────────────────
#  Public helpers
# ──────────────────────────────────────────────

def normalize_skill(name: str) -> str:
    """
    Map a skill name to its canonical form.

    Examples:
        normalize_skill("mysql")       → "SQL"
        normalize_skill("Pandas")      → "Pandas"
        normalize_skill("power bi")    → "Power BI"
        normalize_skill("unknown xyz") → "unknown xyz" (returned as-is)
    """
    key = name.lower().strip()
    return _REVERSE_INDEX.get(key, name.strip())


def are_semantically_equivalent(a: str, b: str) -> bool:
    """
    Check whether two skill names refer to the same canonical skill,
    or have the same base words after removing safe modifiers.

    Examples:
        ("MySQL", "SQL")                → True
        ("Team Collaboration", "Collaboration") → True
    """
    if normalize_skill(a) == normalize_skill(b):
        return True
        
    # Fallback: base word matching
    if clean_skill_modifiers(a) == clean_skill_modifiers(b):
        return True
        
    return False


def get_canonical(name: str) -> str | None:
    """Return canonical name if the skill is known, else None."""
    key = name.lower().strip()
    return _REVERSE_INDEX.get(key)


def is_known_skill(name: str) -> bool:
    """Check if a skill name (or alias) is in our knowledge base."""
    return name.lower().strip() in _REVERSE_INDEX


# ──────────────────────────────────────────────
#  Category grouping (for related-but-different skills)
# ──────────────────────────────────────────────

SKILL_CATEGORIES: dict[str, list[str]] = {
    "Data Visualization": ["Tableau", "Power BI", "Plotly", "Matplotlib", "Seaborn", "Grafana"],
    "SQL": ["SQL"],  # aliases already handled via SKILL_SYNONYMS
    "Python Ecosystem": ["Python", "Pandas", "NumPy", "Scikit-Learn", "Matplotlib", "Seaborn"],
    "Machine Learning": ["Machine Learning", "Deep Learning", "Scikit-Learn", "TensorFlow", "PyTorch", "Keras"],
    "Cloud": ["AWS", "Azure", "GCP"],
    "Web Development": ["React", "Angular", "Vue.js", "Next.js", "Node.js"],
    "Backend": ["FastAPI", "Django", "Flask", "Express.js", "Spring Boot"],
}


def get_category_for_skill(skill: str) -> str | None:
    """Return the category name a skill belongs to, or None."""
    canonical = normalize_skill(skill)
    for category, members in SKILL_CATEGORIES.items():
        if canonical in members:
            return category
    return None


# ──────────────────────────────────────────────
#  Skill hierarchy: parent skill → sub-skills
#  Used to detect when a resume sub-skill satisfies a JD parent skill.
# ──────────────────────────────────────────────

SKILL_HIERARCHY: dict[str, list[str]] = {
    "data analysis": ["pandas", "numpy", "sql", "excel", "matplotlib", "seaborn"],
    "machine learning": ["scikit-learn", "xgboost", "lightgbm", "catboost"],
    "deep learning": ["tensorflow", "pytorch", "keras"],
    "data visualization": ["matplotlib", "seaborn", "plotly", "tableau", "power bi", "grafana"],
    "web development": ["react", "angular", "vue.js", "next.js", "node.js"],
    "backend": ["fastapi", "django", "flask", "express.js", "spring boot"],
    "cloud": ["aws", "azure", "gcp"],
    "data science": ["pandas", "numpy", "scikit-learn", "matplotlib", "seaborn"],
}

# Pre-built reverse index: sub-skill (lower) → set of parent skills (lower)
_HIERARCHY_REVERSE: dict[str, set[str]] = {}

def _build_hierarchy_reverse() -> None:
    """Build reverse lookup from sub-skill → parent skills."""
    for parent, children in SKILL_HIERARCHY.items():
        parent_lower = parent.lower().strip()
        for child in children:
            child_lower = child.lower().strip()
            _HIERARCHY_REVERSE.setdefault(child_lower, set()).add(parent_lower)

_build_hierarchy_reverse()


def is_sub_skill_of(child: str, parent: str) -> bool:
    """
    Check if `child` is a sub-skill of `parent` in the hierarchy.

    Checks both the raw lowered name and the canonical name, because
    some sub-skills (e.g. "xgboost") are also aliases in SKILL_SYNONYMS
    and would canonicalize to their parent ("Machine Learning").

    Examples:
        is_sub_skill_of("Pandas", "Data Analysis")  → True
        is_sub_skill_of("XGBoost", "Machine Learning") → True
        is_sub_skill_of("Python", "Data Analysis")   → False
    """
    child_raw_lower = child.lower().strip()
    child_canonical = normalize_skill(child).lower().strip()
    parent_canonical = normalize_skill(parent).lower().strip()

    # Check raw name first, then canonical
    for key in {child_raw_lower, child_canonical}:
        parents = _HIERARCHY_REVERSE.get(key, set())
        if parent_canonical in parents:
            return True
    return False


def get_parent_skills(skill: str) -> set[str]:
    """Return the set of parent skills (lowercase) for a given skill, or empty set."""
    raw_lower = skill.lower().strip()
    canonical = normalize_skill(skill).lower().strip()
    # Merge parents from both raw and canonical lookups
    parents = set()
    parents.update(_HIERARCHY_REVERSE.get(raw_lower, set()))
    parents.update(_HIERARCHY_REVERSE.get(canonical, set()))
    return parents


# ──────────────────────────────────────────────
#  Semantic relations: contextual keyword matching
#  Looser than SKILL_SYNONYMS — used ONLY for project-scoped matching.
#  If any keyword appears in a project name/description, the JD skill
#  is considered contextually satisfied.
# ──────────────────────────────────────────────
#NOTE:Should use a Big Dictionary in production or transformers/embeddings
SEMANTIC_RELATIONS: dict[str, list[str]] = {
    # --- Existing Domains ---
    "Predictive Analysis": [
        "classification", "regression", "forecasting",
        "predictive modeling", "predictive analytics",
        "tumor classification", "fraud detection",
        "churn prediction", "risk assessment",
        "prediction", "predictive", "prognosis",
    ],
    "Reporting": [
        "report generation", "reports", "insights",
        "business reporting", "data reporting",
        "generating reports", "generated insights",
        "dashboards", "dashboard",
        "decision-making", "decision making",
        "kpi tracking", "metrics",
    ],
    "Problem Solving": [
        "analytical thinking", "critical thinking",
        "troubleshooting", "debugging", "root cause analysis",
        "optimization", "algorithm design",
        "problem-solving", "solutions",
    ],
    "Communication": [
        "presentation", "presentations",
        "stakeholder management", "stakeholder communication",
        "team collaboration", "cross-functional",
        "documentation", "technical writing",
        "interpersonal", "client interaction",
    ],
    "Data Analysis": [
        "insights", "trend analysis", "statistical analysis",
        "data-driven", "data driven decisions",
        "exploratory analysis", "data interpretation",
        "analysis of data", "analyzed data",
    ],
    "Research": [
        "literature review", "research paper",
        "research methodology", "experimental design",
        "hypothesis testing", "survey analysis",
    ],
    "Model Building": [
        "model building", "model evaluation", "model training",
        "classification pipeline", "pipeline", "ensemble",
        "ensemble techniques", "feature engineering",
        "model deployment", "hyperparameter tuning",
        "training models", "building models",
        "machine learning pipeline", "ml pipeline",
    ],
    "Project Management": [
        "led a team", "team lead", "project planning",
        "milestone tracking", "deadline management",
        "sprint planning", "agile management",
    ],
    "Data Visualization": [
        "charts", "graphs", "visual insights",
        "interactive dashboard", "data presentation",
        "visualization of data", "plotted",
    ],

    # --- New Technical Domains ---
    "Web Development": [
        "built a website", "developed web app", "frontend implementation",
        "full-stack", "full stack", "web application", "web portal",
    ],
    "Backend Development": [
        "server-side", "rest api", "graphql backend", "microservices architecture",
        "database integration", "backend logic", "api endpoints",
    ],
    "Frontend Development": [
        "user interface", "ui components", "responsive design", "client-side",
        "single page application", "spa", "frontend architecture",
    ],
    "Cloud Computing": [
        "cloud infrastructure", "migrated to cloud", "cloud deployment",
        "serverless", "cloud architecture", "iac", "infrastructure as code",
    ],
    "DevOps": [
        "ci/cd", "continuous integration", "continuous deployment",
        "automated pipelines", "infrastructure provisioning", "containerization",
    ],
    "Database Management": [
        "schema design", "database tuning", "query optimization",
        "data modeling", "database migration", "sql queries",
    ],
    "System Design": [
        "scalable architecture", "system architecture", "high availability",
        "distributed systems", "load balancing", "fault tolerance",
    ],
    "Software Testing": [
        "unit testing", "integration testing", "test automation", "qa",
        "quality assurance", "test coverage", "tdd", "bdd",
    ],
    "Mobile Development": [
        "ios app", "android app", "mobile application", "cross-platform mobile",
        "mobile ui", "app store deployment",
    ],
    "Cybersecurity": [
        "vulnerability assessment", "penetration testing", "security audit",
        "threat modeling", "data encryption", "secure coding",
    ],
    "UI/UX Design": [
        "wireframing", "prototyping", "user research", "user experience",
        "user testing", "visual design", "usability",
    ],
    "Data Engineering": [
        "etl pipelines", "data warehouse", "data lake", "data pipeline",
        "data ingestion", "data transformation", "batch processing",
    ],
    "API Design": [
        "restful apis", "api endpoints", "api documentation", "swagger",
        "api gateway", "webhook integration",
    ],
    "Version Control": [
        "git repository", "pull requests", "code review", "branching strategy",
        "version history", "source control",
    ],
    "Agile Methodology": [
        "sprint planning", "scrum meetings", "kanban board", "agile ceremonies",
        "sprint retrospective", "daily standups",
    ],
    "Performance Optimization": [
        "reduced latency", "improved performance", "memory leak fix",
        "profiling", "caching strategy", "optimized code",
    ],
    "Natural Language Processing": [
        "text generation", "sentiment classification", "named entity recognition",
        "language models", "chatbot development", "text processing", "nlp pipeline",
    ],
    "Computer Vision": [
        "image classification", "object detection", "image segmentation",
        "facial recognition", "video analysis", "cv pipeline",
    ],
    "Deep Learning": [
        "neural networks", "cnn", "rnn", "transformers", "training deep models",
        "deep learning architecture", "fine-tuning",
    ],
    "Machine Learning": [
        "trained models", "ml algorithms", "supervised learning",
        "unsupervised learning", "ml pipeline", "clustering",
    ],
    "Big Data": [
        "hadoop cluster", "spark jobs", "distributed computing",
        "processing large datasets", "petabyte scale", "real-time streaming",
    ],
    "Automation": [
        "automated scripts", "workflow automation", "process automation",
        "robotic process automation", "rpa", "task automation",
    ],
    "Networking": [
        "tcp/ip", "dns configuration", "network security", "firewall rules",
        "routing protocols", "vpc configuration",
    ],
    "IoT (Internet of Things)": [
        "sensor data", "connected devices", "embedded systems", "iot architecture",
        "edge computing", "telemetry",
    ],

    # --- New Soft / Process Skills ---
    "Mentoring": [
        "guided junior", "mentored team", "knowledge sharing",
        "conducted training", "onboarding", "peer programming",
    ],
    "Leadership": [
        "led the project", "directed a team", "spearheaded", "team lead",
        "managed developers", "technical lead",
    ],
    "Conflict Resolution": [
        "resolved disputes", "mediated conflicts", "handled escalations",
        "negotiated solutions", "conflict management",
    ],
    "Client Facing": [
        "client communication", "client presentations", "gathered client requirements",
        "customer relationship", "stakeholder engagement",
    ],
    "Strategic Planning": [
        "long-term roadmap", "strategic vision", "business strategy",
        "product roadmap", "technical strategy",
    ],
    "Negotiation": [
        "vendor negotiation", "contract negotiation", "deal structuring",
        "resource allocation",
    ],
    "Empathy": [
        "user empathy", "customer-centric", "empathetic leadership",
        "understanding user needs",
    ],
    "Creativity": [
        "innovative solutions", "creative problem solving", "novel approach",
        "out-of-the-box thinking", "innovation",
    ],
    "Time Management": [
        "delivered on time", "met strict deadlines", "prioritized tasks",
        "efficient scheduling", "time tracking",
    ],
    "Adaptability": [
        "adapted to new", "quickly learned", "flexible approach",
        "handled changing requirements", "fast learner",
    ],
    "Teamwork": [
        "collaborated with", "worked cross-functionally", "team environment",
        "joint effort", "team player",
    ],
    "Critical Thinking": [
        "evaluated alternatives", "logical reasoning", "objective analysis",
        "assessed risks", "analytical mindset",
    ],
    "Attention to Detail": [
        "thorough review", "meticulous testing", "error-free delivery",
        "quality control", "high accuracy",
    ],
    "Customer Success": [
        "improved customer satisfaction", "nps score", "reduced churn",
        "customer retention", "customer support",
    ],
    "Public Speaking": [
        "conference speaker", "tech talk", "presented to audience",
        "keynote presentation", "webinar host",
    ],
    "Technical Writing": [
        "wrote documentation", "api docs", "architectural diagrams",
        "user manuals", "technical blog", "wiki documentation",
    ],
    "Requirement Gathering": [
        "gathered requirements", "stakeholder interviews", "business requirements",
        "user stories", "product specs",
    ],
    "Risk Management": [
        "identified risks", "mitigated risks", "contingency planning",
        "risk analysis", "compliance",
    ],
    "Product Management": [
        "product lifecycle", "feature prioritization", "backlog grooming",
        "market research", "go-to-market",
    ],
    "Quality Assurance": [
        "bug tracking", "defect resolution", "quality metrics",
        "test scenarios", "qa testing",
    ],
}

# Pre-built reverse: keyword (lower) → set of JD skills (lower) it can satisfy
_SEMANTIC_REVERSE: dict[str, set[str]] = {}


def _build_semantic_reverse() -> None:
    """Build reverse lookup from contextual keyword → parent JD skills."""
    for skill, keywords in SEMANTIC_RELATIONS.items():
        skill_lower = skill.lower().strip()
        for kw in keywords:
            kw_lower = kw.lower().strip()
            _SEMANTIC_REVERSE.setdefault(kw_lower, set()).add(skill_lower)


_build_semantic_reverse()


def are_contextually_related(text: str, jd_skill: str) -> bool:
    """
    Check if `text` contains contextual keywords that relate to `jd_skill`.

    This is a LOOSE match — only use for scoped contexts (e.g. project
    descriptions) to avoid false positives.

    Args:
        text: A text snippet (e.g. project name or description).
        jd_skill: The JD skill to check against.

    Examples:
        are_contextually_related("Brain Tumor Classification using ML", "Predictive Analysis") → True
        are_contextually_related("Generated insights and reports", "Reporting") → True
    """
    jd_lower = normalize_skill(jd_skill).lower().strip()
    # Also check the raw jd_skill name
    jd_raw_lower = jd_skill.lower().strip()

    text_lower = text.lower()

    keywords = SEMANTIC_RELATIONS.get(jd_skill, []) + SEMANTIC_RELATIONS.get(
        normalize_skill(jd_skill), []
    )

    # Deduplicate
    seen: set[str] = set()
    for entry_key in [jd_raw_lower, jd_lower]:
        for skill_name, kw_list in SEMANTIC_RELATIONS.items():
            if skill_name.lower() == entry_key:
                for kw in kw_list:
                    if kw.lower() not in seen:
                        seen.add(kw.lower())

    # Check if any keyword appears in the text
    for kw in seen:
        if kw in text_lower:
            return True

    return False
