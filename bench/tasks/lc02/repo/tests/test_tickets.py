from app.prompts import SUMMARY_PROMPT, TRANSLATE_PROMPT
from app.tickets import Ticket, ticket_text


def test_ticket_text_layout():
    ticket = Ticket(id=17, customer="Globex", subject=" Login loop ", body="\nUsers are sent back to login.\n")
    assert ticket_text(ticket) == "Ticket #17 from Globex\nSubject: Login loop\n\nUsers are sent back to login."


def test_prompts():
    assert "{" not in SUMMARY_PROMPT
    assert TRANSLATE_PROMPT.format(language="German", text="Hi").endswith("\n\nHi")
