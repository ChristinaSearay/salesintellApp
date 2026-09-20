"""Creating a customer we visited who isn't in Unleashed yet.

Christina's process: SALESAI notices the business is new, the rep confirms, we
create it in Unleashed with the bare minimum, and the visit note is filed
against it — so when they do order, everything already lines up.
"""
from enum import Enum

# A rep-typed business name has to look like one before it reaches the ERP.
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 100

# Near-duplicate check before we create anything: "Temple of the Sun" must not
# become a second record when "Temple Of Sun Jewellery" already exists.
DUPLICATE_RATIO = 0.82          # difflib ratio over normalised names
NAME_CONTAINMENT_IS_DUPLICATE = True  # one name wholly inside another also counts
# ...but only for a name with real substance: a one-word customer called
# "Bruno" sits inside "Bruno's Fine Jewels Byron" without being it.
MIN_CONTAINMENT_WORDS = 2
MAX_DUPLICATE_SUGGESTIONS = 5

# Generated codes follow the shape Unleashed already uses (EJ403, MJ001, S141):
# letters from the business name, then the first free number.
CODE_MAX_LETTERS = 3
CODE_FIRST_NUMBER = 1
CODE_MAX_NUMBER = 999
CODE_FALLBACK_LETTERS = "NEW"

# Dropped before comparing names or building initials — legal form and filler
# carry no signal, and "Pty Ltd" would make every business look alike.
NAME_NOISE = frozenset({
    "pty", "ltd", "ltd.", "limited", "inc", "incorporated", "co", "company",
    "trading", "as", "t/a", "the", "and", "of", "a",
})


class ProspectField:
    """Unleashed Customer fields we set. Bare minimum, per Christina."""
    GUID = "Guid"
    CODE = "CustomerCode"
    NAME = "CustomerName"
    CONTACT_FIRST = "ContactFirstName"
    CONTACT_LAST = "ContactLastName"
    EMAIL = "Email"
    PHONE = "PhoneNumber"
    MOBILE = "MobileNumber"


class ProspectOutcome(Enum):
    """What the check endpoint tells the UI to do."""
    NEW = "new"                # nothing like it — safe to create
    POSSIBLE_DUPLICATE = "possible_duplicate"  # show matches, let the rep pick
    EXISTS = "exists"          # an exact normalised match — link, don't create
