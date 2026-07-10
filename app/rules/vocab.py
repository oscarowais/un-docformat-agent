"""Static vocabularies for terminology/spelling checks.

Sources (per project brief Section 5): UN Editorial Manual Online, DGACM
Instructions for the Preparation of Official Documents, UNTERM conventions.
These lists are deliberately small and high-confidence — extend as needed,
prefer missing a violation over false positives.
"""

# --- UNTERM country/geographical names -------------------------------------
# Wrong/common form -> UN-approved form. Matched case-insensitively on word
# boundaries; keys with spaces are matched as phrases.
UNTERM_COUNTRIES: dict[str, str] = {
    "Vietnam": "Viet Nam",
    "South Korea": "Republic of Korea",
    "North Korea": "Democratic People's Republic of Korea",
    "Ivory Coast": "Côte d'Ivoire",
    "Burma": "Myanmar",
    "Cape Verde": "Cabo Verde",
    "Swaziland": "Eswatini",
    "Turkey": "Türkiye",
    "Czech Republic": "Czechia",
    "Macedonia": "North Macedonia",
    "Moldova": "Republic of Moldova",
    "Tanzania": "United Republic of Tanzania",
    "Syria": "Syrian Arab Republic",
    "Laos": "Lao People's Democratic Republic",
    "Russia": "Russian Federation",
    "Iran": "Islamic Republic of Iran",
    "Venezuela": "Venezuela (Bolivarian Republic of)",
    "Bolivia": "Bolivia (Plurinational State of)",
    "Micronesia": "Micronesia (Federated States of)",
    "Brunei": "Brunei Darussalam",
    "The Gambia": "Gambia",
}

# --- Never-abbreviate terms in running text ---------------------------------
# Abbreviation -> required full form. "United Nations" and "General Assembly"
# are always spelled out in formal documents.
NEVER_ABBREVIATE: dict[str, str] = {
    "UN": "United Nations",
    "GA": "General Assembly",
    "SC": "Security Council",
    "SG": "Secretary-General",
}

# --- Known UN acronyms and their full forms ---------------------------------
# Used to (a) verify first-use expansion, (b) suggest the expansion text.
KNOWN_ACRONYMS: dict[str, str] = {
    "UNDP": "United Nations Development Programme",
    "UNEP": "United Nations Environment Programme",
    "UNHCR": "Office of the United Nations High Commissioner for Refugees",
    "UNICEF": "United Nations Children's Fund",
    "UNESCO": "United Nations Educational, Scientific and Cultural Organization",
    "WHO": "World Health Organization",
    "WFP": "World Food Programme",
    "FAO": "Food and Agriculture Organization of the United Nations",
    "ILO": "International Labour Organization",
    "IMF": "International Monetary Fund",
    "IOM": "International Organization for Migration",
    "OCHA": "Office for the Coordination of Humanitarian Affairs",
    "OHCHR": "Office of the United Nations High Commissioner for Human Rights",
    "UNFPA": "United Nations Population Fund",
    "UNODC": "United Nations Office on Drugs and Crime",
    "UNRWA": ("United Nations Relief and Works Agency for Palestine Refugees "
              "in the Near East"),
    "NGO": "non-governmental organization",
    "SDG": "Sustainable Development Goal",
    "SDGs": "Sustainable Development Goals",
}

# Acronym-looking tokens that are NOT acronyms needing expansion.
ACRONYM_IGNORE: set[str] = {
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",  # roman numerals
    "A", "B", "C", "D", "E",   # list/section letters
    "OK", "AM", "PM", "US",    # US handled via country-name guidance if needed
    # common words appearing in ALL-CAPS headings (heading rule flags those)
    "AND", "OF", "THE", "FOR", "ON", "IN", "TO", "BY", "AT",
    # ISO currency codes (handled by the currency rule instead)
    "USD", "EUR", "CHF", "GBP", "JPY",
    # everyday technical/document terms — not abbreviations needing expansion
    "README", "API", "APIS", "HTTP", "HTTPS", "URL", "URI", "JSON", "XML",
    "HTML", "CSS", "PDF", "DOCX", "PPTX", "XLSX", "CSV", "FAQ", "GPU",
    "CPU", "RAM", "SSD", "SDK", "CLI", "IDE", "AI", "ML", "LLM", "RAG",
    "MIT", "ISO", "ASCII", "UTF",
}

# --- Oxford/UN spelling ------------------------------------------------------
# US/other form -> UN-preferred form (Concise Oxford, first-listed; -ize kept).
# Lowercase keys; matcher preserves the original casing of the first letter.
UN_SPELLING: dict[str, str] = {
    "program": "programme",       # (computer contexts excepted — warning only)
    "programs": "programmes",
    "judgment": "judgement",
    "judgments": "judgements",
    "center": "centre",
    "centers": "centres",
    "labor": "labour",
    "color": "colour",
    "favor": "favour",
    "behavior": "behaviour",
    "behaviors": "behaviours",
    "neighboring": "neighbouring",
    "defense": "defence",
    "offense": "offence",
    "license": "licence",         # noun form
    "counselor": "counsellor",
    "traveling": "travelling",
    "traveled": "travelled",
    "fulfill": "fulfil",
    "fulfillment": "fulfilment",
    "dialog": "dialogue",
    "catalog": "catalogue",
    "analyze": "analyse",         # NOTE: Oxford keeps -yse for analyse/paralyse
    "analyzed": "analysed",
    "analyzing": "analysing",
    "paralyze": "paralyse",
}

# Words ending in -ise that are legitimately -ise (never -ize) even under
# Oxford spelling. Everything else ending in -ise gets flagged.
ISE_EXCEPTIONS: set[str] = {
    "advertise", "advise", "arise", "chastise", "circumcise", "comprise",
    "compromise", "despise", "devise", "disguise", "excise", "exercise",
    "franchise", "improvise", "incise", "premise", "promise", "revise",
    "supervise", "surmise", "surprise", "televise", "wise", "likewise",
    "otherwise", "clockwise", "merchandise", "enterprise", "expertise",
    "concise", "precise", "demise", "paradise", "raise", "praise", "noise",
}

# Ordinal words for first..ninth (used in suggestions for numbers rule).
ORDINAL_WORDS: dict[int, str] = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth",
}

NUMBER_WORDS: dict[int, str] = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine",
}
