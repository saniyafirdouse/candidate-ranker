"""
jd_parser.py
------------
Parses the Job Description into a structured dict.
Every other module uses this output — nothing else reads the JD directly.
"""


def get_jd_profile() -> dict:
    """
    Returns a hardcoded structured profile of the JD.

    Why hardcoded and not parsed dynamically?
    - The JD is fixed for the entire competition
    - Dynamic parsing with docx/NLP adds complexity and failure points
    - Hardcoding lets us be precise about what the JD *means*, not just what it says
    - This is the 'gap between what the JD says and what it means' the JD warned about

    Returns:
        dict: structured JD profile
    """
    return {

        # ── Target titles ──────────────────────────────────────────────────
        # Titles that indicate a genuine fit. Partial matches count.
        "target_titles": [
            "ai engineer",
            "ml engineer",
            "machine learning engineer",
            "applied scientist",
            "applied ml",
            "research engineer",
            "nlp engineer",
            "search engineer",
            "ranking engineer",
            "retrieval engineer",
            "recommendation systems engineer",
            "data scientist",
            "senior engineer",                 # only if paired with ML context
        ],

        # ── Required skills (must-haves from JD) ───────────────────────────
        # These are the "things you absolutely need" section of the JD
        "required_skills": [
            "python",
            "embeddings",
            "vector database",
            "vector search",
            "semantic search",
            "retrieval",
            "ranking",
            "rag",
            "faiss",
            "pinecone",
            "weaviate",
            "qdrant",
            "milvus",
            "opensearch",
            "elasticsearch",
            "sentence transformers",
            "dense retrieval",
            "hybrid search",
            "ndcg",
            "mrr",
            "evaluation framework",
        ],

        # ── Preferred skills (nice-to-haves from JD) ───────────────────────
        "preferred_skills": [
            "fine-tuning",
            "lora",
            "qlora",
            "peft",
            "llm",
            "large language model",
            "transformers",
            "hugging face",
            "xgboost",
            "learning to rank",
            "a/b testing",
            "mlflow",
            "kubeflow",
            "pytorch",
            "tensorflow",
            "spark",
            "distributed systems",
            "inference optimization",
            "open source",
        ],

        # ── Skills that appear in career descriptions (evidence keywords) ──
        # Used by feature_extractor to find career-backed evidence
        "evidence_keywords": [
            "rag", "retrieval", "embedding", "embeddings", "vector",
            "search", "ranking", "ranker", "recommendation", "semantic",
            "faiss", "pinecone", "weaviate", "qdrant", "milvus",
            "opensearch", "elasticsearch", "dense retrieval",
            "fine-tun", "lora", "qlora", "peft", "fine tuning",
            "llm", "language model", "transformer", "bert", "gpt",
            "hugging face", "sentence-transformer",
            "ndcg", "mrr", "map", "precision@", "recall@",
            "a/b test", "ab test", "online experiment",
            "pytorch", "tensorflow", "xgboost",
            "production", "deployed", "shipped", "scaled",
            "inference", "latency", "throughput",
        ],

        # ── Experience range ────────────────────────────────────────────────
        "experience_min": 5,
        "experience_max": 9,
        # sweet spot the JD calls out explicitly
        "experience_sweet_spot_min": 6,
        "experience_sweet_spot_max": 8,

        # ── Preferred locations ─────────────────────────────────────────────
        "preferred_locations": [
            "pune",
            "noida",
            "delhi",
            "ncr",
            "gurugram",
            "gurgaon",
            "hyderabad",
            "mumbai",
            "bangalore",
            "bengaluru",
        ],
        # candidates outside India are lower priority
        "preferred_countries": ["india"],

        # ── Notice period ───────────────────────────────────────────────────
        # JD says: love sub-30 days, can buy out up to 30, 30+ still ok but bar is higher
        "notice_ideal_days": 30,
        "notice_acceptable_days": 60,

        # ── Company type preferences ────────────────────────────────────────
        "prefer_product_companies": True,

        # ── Explicit disqualifiers from JD ──────────────────────────────────
        # These don't auto-disqualify but apply a scoring penalty
        "consulting_firms": [
            "tcs", "infosys", "wipro", "accenture", "cognizant",
            "capgemini", "hcl", "tech mahindra", "mphasis", "mindtree",
            "hexaware", "ltimindtree", "coforge", "persistent",
            "niit technologies", "zensar",
        ],

        # Titles that are red flags regardless of skills listed
        "disqualifying_titles": [
            "marketing manager",
            "hr manager",
            "operations manager",
            "accountant",
            "civil engineer",
            "mechanical engineer",
            "customer support",
            "content writer",
            "business analyst",
            "project manager",
            "sales",
            "frontend engineer",   # unless paired with strong ML career evidence
        ],

        # Domains the JD explicitly says are NOT a fit
        "wrong_domains": [
            "computer vision",     # penalise only if NO nlp/retrieval exposure
            "speech recognition",  # same
            "robotics",
        ],

        # ── Seniority ───────────────────────────────────────────────────────
        "seniority_level": "senior",

        # ── Salary range (INR LPA) ──────────────────────────────────────────
        # Not a hard filter but useful for sanity
        "salary_min_lpa": 30,
        "salary_max_lpa": 80,
    }


def get_required_skills() -> list[str]:
    """Convenience: just the required skills list."""
    return get_jd_profile()["required_skills"]


def get_evidence_keywords() -> list[str]:
    """Convenience: just the evidence keywords for career text search."""
    return get_jd_profile()["evidence_keywords"]


def get_consulting_firms() -> list[str]:
    """Convenience: just the consulting firm names."""
    return get_jd_profile()["consulting_firms"]


def get_disqualifying_titles() -> list[str]:
    """Convenience: just the disqualifying titles."""
    return get_jd_profile()["disqualifying_titles"]