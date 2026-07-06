import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freeflow import textproc


def run(text, **overrides):
    settings = {
        "remove_fillers": True,
        "spoken_commands": True,
        "auto_capitalize": True,
        "dictionary": [],
        "snippets": [],
    }
    settings.update(overrides)
    return textproc.process(text, settings)


def test_removes_um_and_uh():
    assert run("Um, I think, uh, we should ship it.") == "I think, we should ship it."


def test_removes_comma_wrapped_tics():
    assert run("It was, you know, pretty good.") == "It was, pretty good."


def test_keeps_legitimate_like():
    assert run("I like this design.") == "I like this design."


def test_new_paragraph_command():
    assert run("First point. New paragraph. Second point.") == "First point.\n\nSecond point."


def test_new_line_command():
    assert run("Item one, new line item two") == "Item one\nItem two"


def test_bullet_point_command():
    assert run("Item one, bullet point item two") == "Item one\n• Item two"


def test_bullet_point_at_start():
    assert run("Bullet point milk and eggs") == "• Milk and eggs"


def test_dictionary_fixes_casing_whole_word():
    rules = [{"from": "jira", "to": "Jira"}]
    assert run("Update the jira ticket.", dictionary=rules) == "Update the Jira ticket."
    # must not touch substrings
    assert run("The jirafe.", dictionary=rules) == "The jirafe."


def test_snippet_exact_trigger():
    snippets = [{"trigger": "my email", "text": "sheharyarhaq@yahoo.com"}]
    assert run("My email.", snippets=snippets) == "sheharyarhaq@yahoo.com"


def test_snippet_with_insert_prefix():
    snippets = [{"trigger": "my email", "text": "sheharyarhaq@yahoo.com"}]
    assert run("Insert my email", snippets=snippets) == "sheharyarhaq@yahoo.com"


def test_snippet_not_expanded_mid_sentence():
    snippets = [{"trigger": "my email", "text": "x@y.com"}]
    assert run("Send it to my email address.", snippets=snippets) == "Send it to my email address."


def test_capitalizes_sentence_starts():
    assert run("hello there. how are you?") == "Hello there. How are you?"


def test_whitespace_and_punct_tidy():
    assert run("Hello ,  world .") == "Hello, world."


def test_empty_input():
    assert run("") == ""


def test_filler_at_start_capitalized_result():
    assert run("um, hello world.") == "Hello world."
