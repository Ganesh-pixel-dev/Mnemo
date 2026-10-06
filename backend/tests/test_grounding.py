from grounding import Grounder, is_refusal, split_sentences, windows
from tests.conftest import OverlapScorer

PASSAGES = [
    "Gradient descent updates the weights of a model in the direction that lowers the loss. "
    "The learning rate controls the size of each step.",
    "Backpropagation applies the chain rule backwards through the layers to get the gradient.",
]


def test_split_sentences_handles_bullets_and_citations():
    text = "Gradient descent lowers the loss [1]. The learning rate sets the step size [1, 2].\n- A third point here.\n2. A fourth point here."
    assert split_sentences(text) == [
        "Gradient descent lowers the loss [1].",
        "The learning rate sets the step size [1, 2].",
        "A third point here.",
        "A fourth point here.",
    ]


def test_refusal_is_recognised():
    assert is_refusal("Your notes don't cover this.")
    assert is_refusal("Your notes don’t cover this")
    assert not is_refusal("Gradient descent lowers the loss.")


def test_windows_are_short_sentences_and_neighbour_pairs():
    parts = windows("First sentence here. Second sentence here. Third one.")
    assert parts[:3] == ["First sentence here.", "Second sentence here.", "Third one."]
    assert "First sentence here. Second sentence here." in parts
    assert windows("short") == ["short"]


def test_unpunctuated_text_is_cut_into_pieces():
    parts = windows(" ".join(f"w{i}" for i in range(300)))
    assert len(parts) == 5 and all(len(p.split()) <= 60 for p in parts)


def test_nli_grounder_flags_the_unsupported_sentence():
    answer = (
        "The learning rate controls the size of each step [1]. "
        "Gradient descent was invented by Cauchy in 1847 and used by NASA."
    )
    verdicts = Grounder(OverlapScorer(), threshold=0.5).check(answer, PASSAGES)
    assert [v.supported for v in verdicts] == [True, False]
    assert verdicts[0].source == 0


def test_lexical_fallback_flags_the_unsupported_sentence():
    grounder = Grounder(None)
    assert grounder.method == "lexical"
    answer = "Backpropagation applies the chain rule backwards through the layers. Transformers use rotary embeddings for position."
    verdicts = grounder.check(answer, PASSAGES)
    assert [v.supported for v in verdicts] == [True, False]
    assert verdicts[0].source == 1


def test_refusals_and_fragments_are_not_checked():
    assert Grounder(None).check("Your notes don't cover this.", PASSAGES) == []
    assert Grounder(None).check("Yes. See [1].", PASSAGES) == []


def test_no_passages_means_unsupported():
    verdicts = Grounder(None).check("Gradient descent lowers the loss.", [])
    assert [v.supported for v in verdicts] == [False]
