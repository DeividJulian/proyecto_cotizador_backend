"""Removes personal data (names, emails, phones) from text before it is sent to an external AI provider.

Adapted from the ATS project. The model only sees placeholders such as [cliente] or [correo 1]; `restore` puts the
real values back in its answer, so a rewritten proposal keeps the client's name.
"""
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Optional country code, then 7 to 10 digits that may be grouped with spaces, dots, dashes or parentheses
PHONE = re.compile(r"(?<![\w@.$])(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{1,3}\)?[\s.-]?)?\d{3}[\s.-]?\d{2,4}[\s.-]?\d{2,4}(?![\w@])")
_YEAR_RANGE = re.compile(r"(?:19|20)\d{2}\s*[-–/]\s*(?:19|20)\d{2}")

# Each letter also matches its accented forms, so "Sebastian" in the text hides "Sebastián" and vice versa
_ACCENTS = {"a": "aáàä", "e": "eéèë", "i": "iíìï", "o": "oóòö", "u": "uúùü", "n": "nñ"}
_PLAIN = {accented: plain for plain, group in _ACCENTS.items() for accented in group}


def looks_like_phone(candidate: str) -> bool:
    """7 to 13 digits, and not a range of years such as 2019-2024."""
    digits = re.sub(r"\D", "", candidate)
    core = re.sub(r"^\D+|\D+$", "", candidate)
    return 7 <= len(digits) <= 13 and not _YEAR_RANGE.fullmatch(core)


def _name_pattern(text: str) -> re.Pattern:
    letters = "".join(
        f"[{_ACCENTS[_PLAIN.get(c, c)]}]" if _PLAIN.get(c, c) in _ACCENTS else (r"\s+" if c == " " else re.escape(c))
        for c in " ".join(text.lower().split())
    )
    return re.compile(rf"(?<!\w){letters}(?!\w)", re.IGNORECASE)


class Redactor:
    """Hides personal data in the texts sent to the model and puts it back in the answers.

    names: placeholder -> real value, e.g. {"[cliente]": "Laura Gómez", "[empresa]": "Café SAS"}.
    Every part of a name (first names and surnames) counts as personal data. Emails and phones are
    detected even when they are not given.
    """

    def __init__(self, names: dict[str, str | None] | None = None, emails: tuple[str | None, ...] = ()):
        self.names = {placeholder: value.strip() for placeholder, value in (names or {}).items() if value and value.strip()}
        self.emails = [e for e in emails if e]
        self._found: dict[str, str] = {}  # numbered placeholder -> original email or phone

    def _numbered(self, kind: str, value: str) -> str:
        for placeholder, original in self._found.items():
            if original.lower() == value.lower():
                return placeholder
        placeholder = f"[{kind} {sum(1 for p in self._found if p.startswith('[' + kind)) + 1}]"
        self._found[placeholder] = value
        return placeholder

    def redact(self, text: str | None) -> str:
        result = text or ""
        for email in self.emails:
            result = re.sub(re.escape(email), lambda m: self._numbered("correo", m.group(0)), result, flags=re.IGNORECASE)
        result = EMAIL.sub(lambda m: self._numbered("correo", m.group(0)), result)
        result = PHONE.sub(lambda m: self._numbered("teléfono", m.group(0)) if looks_like_phone(m.group(0)) else m.group(0), result)
        # The full name first, so "Laura Gómez" becomes one placeholder and not two
        for placeholder, value in self.names.items():
            result = _name_pattern(value).sub(placeholder, result)
        for placeholder, value in self.names.items():
            for part in value.split():
                if len(part) >= 3:
                    result = _name_pattern(part).sub(placeholder, result)
        return result

    def restore(self, text: str | None) -> str:
        result = text or ""
        for placeholder, value in {**self._found, **self.names}.items():
            result = result.replace(placeholder, value)
        return result


def redact_personal_data(text: str, names: tuple[str | None, ...] = (), emails: tuple[str | None, ...] = ()) -> str:
    """One-way version: replaces the given names and any email or phone with neutral placeholders."""
    return Redactor({f"[nombre {i + 1}]": name for i, name in enumerate(names)}, emails).redact(text)
