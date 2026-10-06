"""Measure the grounding check on a small hand-written set.

Each case is a short passage and answer sentences written by me, labelled 1 if the passage
supports the sentence and 0 if it adds a claim, changes a detail or contradicts it.
The set is tiny and written by the author of the checker, so treat the numbers as a smoke
test, not a benchmark.

    python eval_grounding.py
"""

from config import Settings
from grounding import Grounder, NLIScorer

CASES = [
    (
        "Photosynthesis takes place in the chloroplasts of plant cells. Chlorophyll absorbs light, mostly in the red and blue parts of the spectrum. "
        "The process turns carbon dioxide and water into glucose and releases oxygen.",
        [
            ("Photosynthesis happens in the chloroplasts.", 1),
            ("Chlorophyll absorbs mostly red and blue light.", 1),
            ("Oxygen is released as a by-product.", 1),
            ("Photosynthesis happens in the mitochondria.", 0),
            ("Chlorophyll mostly absorbs green light.", 0),
            ("The process was first described by Jan van Helmont in 1648.", 0),
        ],
    ),
    (
        "Gradient descent updates the weights of a model step by step in the direction that lowers the loss. "
        "The learning rate sets the size of each step. If the learning rate is too large, training can overshoot the minimum and diverge.",
        [
            ("Gradient descent lowers the loss by updating the weights.", 1),
            ("The learning rate controls the step size.", 1),
            ("A learning rate that is too large can make training diverge.", 1),
            ("A larger learning rate always makes training converge faster.", 0),
            ("Gradient descent was invented by Google.", 0),
            ("Gradient descent updates the weights in the direction that raises the loss.", 0),
        ],
    ),
    (
        "The French Revolution began in 1789. The Bastille was stormed on 14 July of that year. "
        "In 1793 the king, Louis XVI, was executed by guillotine.",
        [
            ("The revolution started in 1789.", 1),
            ("The Bastille was stormed in July.", 1),
            ("Louis XVI was executed in 1793.", 1),
            ("The revolution began in 1799.", 0),
            ("Napoleon crowned himself emperor in 1804.", 0),
            ("Louis XVI escaped to Austria.", 0),
        ],
    ),
    (
        "A stack is a data structure that follows last in, first out order. Push adds an element to the top and pop removes the top element. "
        "Both operations take constant time.",
        [
            ("A stack is last in, first out.", 1),
            ("Pop removes the top element.", 1),
            ("Push and pop run in constant time.", 1),
            ("A stack is first in, first out.", 0),
            ("Pop removes the bottom element.", 0),
            ("Stacks are always implemented with linked lists.", 0),
        ],
    ),
    (
        "Osmosis is the movement of water across a semi-permeable membrane from a region of low solute concentration to a region of high solute concentration. "
        "It does not need energy from the cell.",
        [
            ("Water moves across a semi-permeable membrane in osmosis.", 1),
            ("Osmosis does not use cellular energy.", 1),
            ("Water moves toward the side with more solute.", 1),
            ("Osmosis moves solutes across the membrane using ATP.", 0),
            ("Water moves toward the side with less solute.", 0),
            ("Osmosis was discovered by Louis Pasteur.", 0),
        ],
    ),
    (
        "TCP provides reliable, ordered delivery of bytes between two hosts. It sets up a connection with a three-way handshake. "
        "UDP does not set up a connection and does not guarantee delivery.",
        [
            ("TCP delivers bytes reliably and in order.", 1),
            ("TCP uses a three-way handshake.", 1),
            ("UDP does not guarantee delivery.", 1),
            ("UDP guarantees ordered delivery.", 0),
            ("TCP is connectionless.", 0),
            ("TCP runs on port 80 only.", 0),
        ],
    ),
    (
        "The Sutherland-Hodgman algorithm clips a polygon against one boundary of the clip window at a time. "
        "The output of one stage becomes the input of the next. It works for convex clip windows only, and the result can contain extra edges when a concave polygon is clipped.",
        [
            ("The polygon is clipped against the window boundaries one after another.", 1),
            ("Each stage feeds its output to the next stage.", 1),
            ("A concave polygon can come out with extra edges.", 1),
            ("The algorithm handles concave clip windows.", 0),
            ("The polygon is clipped against all four boundaries at the same time.", 0),
            ("The algorithm needs exactly three stages.", 0),
        ],
    ),
    (
        "Mitosis produces two genetically identical daughter cells. Meiosis produces four cells with half the number of chromosomes, and it takes place only in the formation of gametes.",
        [
            ("Mitosis gives two identical cells.", 1),
            ("Meiosis halves the chromosome number.", 1),
            ("Meiosis happens when gametes are formed.", 1),
            ("Mitosis gives four cells.", 0),
            ("Meiosis happens in all body cells.", 0),
            ("Mitosis halves the chromosome number.", 0),
        ],
    ),
]


def main() -> None:
    settings = Settings.from_env()
    rows = [(passage, s, label) for passage, items in CASES for s, label in items]
    for name, grounder in (
        ("lexical overlap", Grounder(None)),
        (f"NLI {settings.nli_model}", Grounder(NLIScorer(settings.nli_model), settings.nli_threshold)),
    ):
        tp = fp = tn = fn = 0
        for passage, sentence, label in rows:
            verdict = grounder.check(sentence, [passage])
            supported = bool(verdict and verdict[0].supported)
            if label and supported:
                tp += 1
            elif label:
                fn += 1
            elif supported:
                fp += 1
            else:
                tn += 1
        total = tp + fp + tn + fn
        print(f"{name}: {total} sentences, accuracy {(tp + tn) / total:.2f}")
        print(f"  supported kept: {tp}/{tp + fn}   unsupported flagged: {tn}/{tn + fp}   (missed unsupported: {fp}, wrongly flagged: {fn})")


if __name__ == "__main__":
    main()
