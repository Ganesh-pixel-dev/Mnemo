import pytest

from modes import ELABORATION, RECALL, detect_mode


@pytest.mark.parametrize(
    "question",
    [
        "Explain backpropagation",
        "why does the learning rate matter?",
        "How does gradient descent work?",
        "give me an example of overfitting",
        "Can you elaborate on that",
        "tell me more",
        "WHY is the sky blue",
    ],
)
def test_elaboration(question):
    assert detect_mode(question) == ELABORATION


@pytest.mark.parametrize(
    "question",
    [
        "What did my notes say about backpropagation?",
        "Define gradient descent",
        "How many chunks does the pdf have?",
        "how much does the dataset weigh",
        "Show me the formula for the loss",
        "Moreover, list the layers",
        "Somehow the exams are on Friday, when?",
    ],
)
def test_recall(question):
    assert detect_mode(question) == RECALL
