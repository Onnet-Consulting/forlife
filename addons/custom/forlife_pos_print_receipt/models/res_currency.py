from odoo import fields, api, models, tools


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def format(self, amount):
        """Return ``amount`` formatted according to ``self``'s rounding rules, symbols and positions.

           Also take care of removing the minus sign when 0.0 is negative

           :param float amount: the amount to round
           :return: formatted str
        """
        self.ensure_one()
        return tools.format_amount(self.env, amount + 0.0, self)
