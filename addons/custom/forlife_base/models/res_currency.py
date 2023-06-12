from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)
try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class Currency(models.Model):
    _inherit = "res.currency"

    # thư viện num2words đang định nghĩa lang_code Việt Nam là vi_VN
    # hàm amount_to_text của base odoo truyền tham số lang_code từ trường iso_code (của Việt Nam là vi)
    # chính vì vậy phải custom lại hàm amount_to_text

    def amount_to_text(self, amount):
        self.ensure_one()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()

        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(self.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        if self._context.get('lang') == 'vi_VN':
            lang = 'vi_VN'
        else:
            lang = tools.get_lang(self.env).iso_code
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
            amt_value=_num2words(integer_value, lang=lang),
            amt_word=self.currency_unit_label,
        )
        if not self.is_zero(amount - integer_value):
            amount_words += ' ' + _('and') + tools.ustr(' {amt_value} {amt_word}').format(
                amt_value=_num2words(fractional_value, lang=lang),
                amt_word=self.currency_subunit_label,
            )
        return amount_words
