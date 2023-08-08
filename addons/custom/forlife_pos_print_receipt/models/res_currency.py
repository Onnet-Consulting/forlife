from odoo import fields, api, models, tools


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def custom_format(self, amount, no_symbol = False):
        """Return ``amount`` formatted according to ``self``'s rounding rules, symbols and positions.

           Also take care of removing the minus sign when 0.0 is negative

           :param float amount: the amount to round
           :return: formatted str
        """
        self.ensure_one()
        amount = tools.format_amount(self.env, amount + 0.0, self)
        if no_symbol:
            amount = amount.replace(self.symbol, '').strip()
        return amount
