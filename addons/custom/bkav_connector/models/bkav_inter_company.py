# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountMoveInter(models.Model):
    _inherit = 'account.move'


    def write(self, vals):
        res = super(AccountMoveInter, self).write(vals)
        if vals.get('po_source_id') and self.state == 'posted':
            if self.po_source_id.is_inter_company:
                self.create_an_invoice_and_publish_invoice_bkav()
        return res


    def create_an_invoice_and_publish_invoice_bkav(self):
        for invoice in self:
            try:
                invoice.create_invoice_bkav()
            except Exception as e:
                pass


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def approve_company_sale(self, company_sale):
        sale, invoice, picking = super(PurchaseOrder, self).approve_company_sale(company_sale)
        for line in invoice:
            line.write(
                {
                    "po_source_id": self.id
                }
            )
        return sale, invoice, picking