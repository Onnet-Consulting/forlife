# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from contextlib import contextmanager

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _convert_to_tax_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.
        :return: A python dictionary.
        """
        self.ensure_one()
        if self.filtered(lambda r: r.move_id.origin_invoice_id):
            sign = 1 if self.move_id.invoice_type == 'increase' else -1
            return self.env['account.tax']._convert_to_tax_line_dict(
                self,
                partner=self.partner_id,
                currency=self.currency_id,
                taxes=self.tax_ids,
                tax_tags=self.tax_tag_ids,
                tax_repartition_line=self.tax_repartition_line_id,
                group_tax=self.group_tax_id,
                account=self.account_id,
                analytic_distribution=self.analytic_distribution,
                tax_amount=sign * self.amount_currency,
            )
        else:
            return super()._convert_to_tax_line_dict()
