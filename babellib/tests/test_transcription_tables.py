from babelsoft.languages.manchu import Manchu
from babelsoft.languages.mongolian import Mongolian


def test_manchu_transcription_characters_match_ascii_sequences() -> None:
    cases = {
        "\u0161": "x",
        "\u010D": "ts",
        "z": "dz",
        "\u0159": "zr",
        "\u016B": "uu",
        "\u2011": "-",
    }

    for transcription, ascii_text in cases.items():
        assert Manchu._expand_transcription(transcription) == ascii_text


def test_mongolian_transcription_characters_match_ascii_sequences() -> None:
    cases = {
        "\u010D": "c",
        "\u01F0": "j",
        "\u0161": "x",
        "k": "q",
        "\u03B3": "g",
        "\u0263": "w",
        "\u00F6": "oe",
        "\u00FC": "ue",
        "\u2011": "-",
    }

    for transcription, ascii_text in cases.items():
        assert Mongolian._expand_transcription(transcription) == ascii_text
