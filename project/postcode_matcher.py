import re
import pandas as pd

class PostcodeMatcher:
    def __init__(self):
        # Define dictionary mapping country ISO codes to their postcode regex patterns
        self.postcode_patterns = {
            "GBR": r"^(GIR\s0AA|[A-PR-UWYZ]([0-9]{1,2}|([A-HK-Y][0-9]|[A-HK-Y][0-9]([0-9]|[ABEHMNPRV-Y]))|[0-9][A-HJKS-UW])[0-9][ABD-HJLNP-UW-Z]{2})$",
            "IRL": r"^[A-Za-z]\d{2}\s[A-Za-z]\d[A-Za-z]\d$", 
            # Add more countries and their postcode patterns as needed
        }

    def validate_postcode_for_country(self, postcode, iso_code):
        """
        Validates a postcode for a specific country ISO code.

        :param postcode: The postcode to validate.
        :param iso_code: The ISO code of the country.
        :return: True if the postcode is valid for the country, False otherwise.
        """
        if isinstance(iso_code, str) and iso_code in self.postcode_patterns:
            pattern = self.postcode_patterns[iso_code]
            return bool(re.match(pattern, postcode))
        else:
            # Handle the case where the ISO code is not found or is not a string
            return False

