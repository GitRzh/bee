"""
Local utilities - zero API calls needed
"""

KNOWN_TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "c++", "c", "r", "scala", "julia", "matlab",
    "rust", "go", "kotlin", "swift", "typescript", "sql", "bash", "shell", "perl",
    # ML / AI Core
    "machine learning", "ml", "deep learning", "dl", "neural networks", "neural network",
    "nlp", "natural language processing", "computer vision", "cv",
    "reinforcement learning", "rl", "supervised learning", "unsupervised learning",
    "semi-supervised", "self-supervised", "generative ai", "gen ai",
    # Architectures
    "transformers", "bert", "gpt", "llm", "large language models",
    "diffusion models", "gans", "gan", "autoencoders", "autoencoder",
    "cnn", "rnn", "lstm", "gru", "attention mechanism", "attention",
    "resnet", "vgg", "vit", "vision transformer", "unet", "yolo",
    # Frameworks / Libs
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "huggingface",
    "opencv", "nltk", "spacy", "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "xgboost", "lightgbm", "catboost", "fastapi", "flask", "django",
    "langchain", "llamaindex", "llama index",
    # Data
    "data science", "data engineering", "data analysis", "feature engineering",
    "data preprocessing", "etl", "nosql", "mongodb", "postgresql", "mysql",
    "redis", "spark", "hadoop", "kafka", "airflow", "dbt", "bigquery",
    # Cloud / MLOps
    "mlops", "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
    "mlflow", "wandb", "git", "devops", "ci/cd", "kubeflow", "sagemaker",
    # Math / Stats
    "statistics", "linear algebra", "calculus", "probability", "optimization",
    "bayesian", "regression", "classification", "clustering",
    # Techniques
    "prompt engineering", "rag", "retrieval augmented generation", "fine-tuning",
    "transfer learning", "few-shot", "zero-shot", "lora", "qlora",
    "recommendation systems", "time series", "anomaly detection",
    "object detection", "image segmentation", "ocr", "speech recognition",
    "text classification", "sentiment analysis", "named entity recognition", "ner",
    "question answering", "word2vec", "glove", "fasttext", "embeddings",
    "pca", "dimensionality reduction", "random forest", "decision tree",
    "svm", "support vector machine", "k-means", "dbscan",
    "gradient boosting", "adaboost", "ensemble methods",
    "hyperparameter tuning", "cross-validation", "regularization",
    "batch normalization", "dropout", "backpropagation", "gradient descent",
    # CS
    "algorithms", "data structures", "system design", "api", "rest", "graphql",
    "microservices", "distributed systems",
}


def _is_gibberish_skill(text: str) -> bool:
    """
    Reject clearly nonsensical input before skill matching.
    Short inputs (<=3 chars) are handled by exact-match only — skip gibberish check.
    """
    t = text.strip().lower()

    # Short inputs (single letters like "r", "c", acronyms like "nlp", "rnn")
    # are handled purely by exact match — no gibberish check needed
    if len(t) <= 3:
        return False

    letters = [c for c in t if c.isalpha()]

    # Must have at least 2 actual letters
    if len(letters) < 2:
        return True

    # Reject if alphanumeric ratio is too low (e.g. @#$%^&*)
    alnum = sum(c.isalnum() for c in t)
    if alnum / len(t) < 0.6:
        return True

    # For 4-5 char inputs (e.g. "lstm", "bert"), use a relaxed repeated-char threshold
    # For longer inputs, use a strict threshold (catches r4r4r4r4, jjjsjjs)
    threshold = 0.80 if len(t) <= 5 else 0.55
    most_common_ratio = max(letters.count(c) for c in set(letters)) / len(letters)
    if most_common_ratio > threshold:
        return True

    # Vowel check only for inputs longer than 5 chars (avoids flagging "gru", "lstm")
    if len(t) > 5:
        vowels = sum(1 for c in letters if c in "aeiou")
        if vowels / len(letters) < 0.10:
            return True

    return False


def validate_skills_local(skills: list) -> tuple:
    """
    Returns (valid_skills, invalid_skills).
    Checks against known tech/AI/ML skills locally.
    """
    valid = []
    invalid = []
    for skill in skills:
        skill_clean = skill.lower().strip()
        if not skill_clean:
            continue

        # Gibberish pre-check before any matching
        if _is_gibberish_skill(skill_clean):
            invalid.append(skill.strip())
            continue

        matched = False
        for known in KNOWN_TECH_SKILLS:
            if len(known) <= 2:
                # Short skills (r, c, go) must be exact match only
                if skill_clean == known:
                    matched = True
                    break
            else:
                # Normal substring matching for longer skills
                if skill_clean == known or skill_clean in known or known in skill_clean:
                    matched = True
                    break

        if matched:
            valid.append(skill.strip())
        else:
            invalid.append(skill.strip())
    return valid, invalid


def classify_response_local(question: str, answer: str) -> str:
    """
    Classify if answer is off-topic or meta without any API call.
    Returns: ANSWER, OFF_TOPIC, or META
    """
    answer_lower = answer.lower().strip()

    # META: refusing / challenging the interview itself
    meta_patterns = [
        "don't want to answer", "not answering", "refuse to answer",
        "skip this", "next question", "i refuse", "won't answer",
        "not relevant", "this is irrelevant", "bad question",
        "why are you asking", "what does this have to do",
        "this is unfair", "stupid question", "wrong question",
        "stop asking", "i won't", "i will not answer",
    ]
    if any(p in answer_lower for p in meta_patterns):
        return "META"

    # Too short = likely evasive / off-topic
    if len(answer.strip()) < 8 or len(answer.strip().split()) < 3:
        return "OFF_TOPIC"

    return "ANSWER"