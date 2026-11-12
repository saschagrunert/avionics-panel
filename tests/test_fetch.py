"""pcb/footprints/fetch.py reads the pin names from an EasyEDA symbol: check.py's polarity check depends on them."""
from conftest import load


def test_pin_names_come_with_their_pad_numbers():
    # the two pins of JLC's symbol of the 1N4148W (C81598) as EasyEDA sends them, between two other shapes
    shapes = [
        "PL~-5 8 -5 -8~#880000~1~0~none~gge3~0",
        "P~show~0~2~20~0~0~gge8~0^^20~0^^M 20 0 h -15~#880000^^0~2~3~0~A~end~~~#0000FF^^0~11~-1~0~2~start~~~#0000FF"
        "^^0~8~0^^0~M 5 -3 L 2 0 L 5 3",
        "P~show~0~1~-20~0~180~gge17~0^^-20~0^^M -20 0 h 15~#880000^^0~-2~3~0~K~start~~~#0000FF^^0~-11~-1~0~1~end~~~"
        "#0000FF^^0~-8~0^^0~M -5 3 L -2 0 L -5 -3",
        "PG~5 -8 5 8~#880000~1~0~none~gge20~0",
    ]
    fetch = load("_fetch", "pcb/footprints/fetch.py")
    assert fetch.pins_of({"dataStr": {"shape": shapes}}) == [("1", "K"), ("2", "A")]
