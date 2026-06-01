from syntra.agents.intake import IntakeAgent


def test_intake_parses_multiline_slack_command():
    payload = """project=crm-web
title=Login button broken
description=Clicking login does nothing
priority=medium"""

    bug = IntakeAgent().parse(payload)

    assert bug.project == "crm-web"
    assert bug.title == "Login button broken"
    assert bug.description == "Clicking login does nothing"
    assert bug.priority == "medium"


def test_intake_parses_single_line_slack_command():
    payload = (
        "project=Mukul-Fitness title=Fix typo in README "
        "description=There is a typo in README. Replace wrong spelling priority=low"
    )

    bug = IntakeAgent().parse(payload)

    assert bug.project == "Mukul-Fitness"
    assert bug.title == "Fix typo in README"
    assert bug.description == "There is a typo in README. Replace wrong spelling"
    assert bug.priority == "low"
