# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class UpdateInvoiceStatus(models.Model):
    _inherit = 'account.move'

    def bravo_get_update_invoice_status_values(self):
        res = []
        columns = self.bravo_get_update_invoice_status_columns()
        for record in self:
            res.extend(record.bravo_get_update_invoice_status_value())
        return columns, res

    @api.model
    def bravo_get_update_invoice_status_columns(self):
        return ["BranchCode", "DocCode", "DocNo", "DocDate", "Stt", "MadeDate", "PushDate", "EInvoiceStatus"]

    def bravo_get_update_invoice_status_value(self):
        self.ensure_one()
        origin_invoice = self.debit_origin_id or self.reversed_entry_id
        doc_code = 'HC' if self.issue_invoice_type == 'adjust' else 'H2'
        doc_no = origin_invoice.invoice_no or origin_invoice.name or None
        return [{
            "BranchCode": self.company_id.code or None,
            "DocCode": doc_code,
            "DocNo": doc_no,
            "DocDate": origin_invoice.invoice_date or None,
            "Stt": doc_no,
            "MadeDate": self.invoice_date or None,
            "PushDate": self.create_date or None,
            "EInvoiceStatus": 3 if (self.debit_origin_id or self.refund_method == 'refund') else 4,
        }]
