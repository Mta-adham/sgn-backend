"""Validation for member-to-member connection notes.

Two jobs, both of which have to happen on the server because a browser check is a
convenience rather than a control.

**Contact details.** The whole design of connections is that details are exchanged only
when the recipient accepts. A note is the obvious way around that: put your email in it and
the accept step no longer matters. Blocking addresses, numbers and links keeps the gate
meaningful rather than decorative.

**Abuse.** A free-text field delivered to a stranger needs a floor on what can be sent.
The word list here is deliberately short and aimed at unambiguous cases: an aggressive
filter that rejects ordinary messages trains people to give up, and reporting is what
handles the rest.
"""

import re

# A real address, and the usual ways of writing one to dodge a filter.
_EMAIL = re.compile(r"[\w.+-]+\s*(?:@|\(at\)|\[at\]|\bat\b)\s*[\w-]+\s*(?:\.|\bdot\b)\s*\w{2,}", re.I)

# Seven or more digits, however they are spaced or punctuated. Seven is the shortest real
# subscriber number, and a lower threshold would reject things like years and figures.
_PHONE = re.compile(r"(?:\+?\d[\s().-]{0,2}){7,}\d")

_URL = re.compile(r"(?:https?://|www\.)\S+", re.I)

# A bare domain, limited to plausible TLDs so ordinary sentences ending in a full stop and
# a short word are not mistaken for one.
_DOMAIN = re.compile(
    r"\b[\w-]+\.(?:com|co|net|org|io|ai|me|sa|uk|ae|eu|info|biz|app|dev|xyz)\b", re.I
)

# Social handles, which are contact details by another name.
_HANDLE = re.compile(r"(?<![\w.])@[A-Za-z][\w.]{2,}")

# Unambiguous profanity and slurs only. Matched on word boundaries so that innocent words
# containing these as substrings are unaffected.
_BANNED_WORDS = {
    "fuck", "fucking", "fucker", "shit", "bitch", "bastard", "cunt", "dick", "prick",
    "asshole", "whore", "slut", "faggot", "nigger", "retard", "rape", "kill yourself",
}
_PROFANITY = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in sorted(_BANNED_WORDS, key=len, reverse=True)) + r")\b",
    re.I,
)

MAX_LENGTH = 500


def check_message(text: str | None) -> list[str]:
    """Return the reasons a note cannot be sent. An empty list means it is fine.

    Reasons are phrased for the person writing, not for a log, because they are shown
    straight back to them and a vague rejection is worse than no filter at all.
    """
    if not text:
        return []

    note = text.strip()
    if not note:
        return []

    problems: list[str] = []

    if len(note) > MAX_LENGTH:
        problems.append(f"Keep your note under {MAX_LENGTH} characters.")

    if _EMAIL.search(note):
        problems.append(
            "Remove the email address. Contact details are shared automatically once your "
            "request is accepted."
        )

    if _PHONE.search(note):
        problems.append(
            "Remove the phone number. Contact details are shared automatically once your "
            "request is accepted."
        )

    if _URL.search(note) or _DOMAIN.search(note):
        problems.append("Remove the link. Notes are plain text only.")

    if _HANDLE.search(note):
        problems.append("Remove the social handle. Notes are plain text only.")

    if _PROFANITY.search(note):
        problems.append("Please reword this without offensive language.")

    return problems
