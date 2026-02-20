"""
Static resource mapping for learning materials
"""

LEARNING_RESOURCES = {
    "machine_learning": [
        "https://scikit-learn.org/stable/documentation.html",
        "https://www.coursera.org/learn/machine-learning",
        "https://developers.google.com/machine-learning/crash-course"
    ],
    "deep_learning": [
        "https://pytorch.org/tutorials/",
        "https://www.deeplearning.ai/",
        "https://www.tensorflow.org/tutorials"
    ],
    "neural_networks": [
        "https://cs231n.github.io/",
        "https://pytorch.org/tutorials/beginner/basics/intro.html",
        "https://www.3blue1brown.com/topics/neural-networks"
    ],
    "nlp": [
        "https://huggingface.co/learn/nlp-course/chapter1/1",
        "https://web.stanford.edu/class/cs224n/",
        "https://www.nltk.org/book/"
    ],
    "computer_vision": [
        "https://cs231n.stanford.edu/",
        "https://pytorch.org/vision/stable/index.html",
        "https://opencv.org/university/"
    ],
    "transformers": [
        "https://huggingface.co/docs/transformers/index",
        "https://jalammar.github.io/illustrated-transformer/",
        "https://arxiv.org/abs/1706.03762"
    ],
    "reinforcement_learning": [
        "https://spinningup.openai.com/en/latest/",
        "http://incompleteideas.net/book/the-book.html",
        "https://www.deepmind.com/learning-resources"
    ],
    "statistics": [
        "https://www.khanacademy.org/math/statistics-probability",
        "https://online.stat.psu.edu/statprogram/",
        "https://seeing-theory.brown.edu/"
    ],
    "linear_algebra": [
        "https://www.khanacademy.org/math/linear-algebra",
        "https://www.3blue1brown.com/topics/linear-algebra",
        "http://cs229.stanford.edu/section/cs229-linalg.pdf"
    ],
    "python": [
        "https://docs.python.org/3/tutorial/",
        "https://realpython.com/",
        "https://www.python.org/about/gettingstarted/"
    ],
    "data_structures": [
        "https://www.geeksforgeeks.org/data-structures/",
        "https://www.coursera.org/specializations/data-structures-algorithms",
        "https://visualgo.net/en"
    ],
    "algorithms": [
        "https://www.geeksforgeeks.org/fundamentals-of-algorithms/",
        "https://visualgo.net/en",
        "https://leetcode.com/problemset/all/"
    ]
}

def get_resources_for_topics(topics):
    """
    Map topics to learning resources
    """
    resources = []
    topics_lower = [t.lower().replace(" ", "_") for t in topics]
    
    for topic in topics_lower:
        for key in LEARNING_RESOURCES:
            if key in topic or topic in key:
                resources.extend(LEARNING_RESOURCES[key])
                break
    
    # Add general ML resources if nothing matched
    if not resources:
        resources.extend(LEARNING_RESOURCES["machine_learning"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_resources = []
    for r in resources:
        if r not in seen:
            seen.add(r)
            unique_resources.append(r)
    
    return unique_resources[:10]  # Limit to 10 resources