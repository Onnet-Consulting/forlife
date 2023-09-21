from odoo import fields, models, api


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    def _inverse_partner_id(self):
        for invoice in self:
            if invoice.is_invoice(True):
                for line in invoice.line_ids + invoice.invoice_line_ids:
                    if line.product_id.product_tmpl_id.voucher or line.display_type == 'product' and line.journal_id.company_consignment_id and line.pos_order_line_id:
                        continue
                    if line.partner_id != invoice.commercial_partner_id:
                        line.partner_id = invoice.commercial_partner_id
                        line._inverse_partner_id()


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_state_registration = fields.Boolean(string='State Registration', store=False)
    pos_order_line_id = fields.Many2one(comodel_name='pos.order.line', string='POS Order Line', index=True)

    def write(self, values):
        if isinstance(values, dict) and 'partner_id' in values:
            self = self.filtered(lambda aml: not aml.partner_id or (
                    aml.partner_id.id != values['partner_id']
                    and not (
                        aml.display_type == 'product'
                        and aml.journal_id.company_consignment_id
                        and aml.pos_order_line_id
                        or aml.product_id.product_tmpl_id.voucher)))
        return super(InheritAccountMoveLine, self).write(values)

    def _compute_partner_id(self):
        for line in self:
            if line.display_type == 'product' and line.journal_id.company_consignment_id and line.pos_order_line_id:
                line.partner_id = line.journal_id.company_consignment_id
            elif (line.display_type == 'product' and line.product_id.product_tmpl_id.voucher
                  and line.move_id.company_id.accounting_voucher_partner_id and line.pos_order_line_id):
                line.partner_id = line.move_id.company_id.accounting_voucher_partner_id
            else:
                line.partner_id = line.move_id.partner_id.commercial_partner_id

    def _inverse_partner_id(self):
        record = self.filtered(lambda aml: not (aml.product_id.product_tmpl_id.voucher or aml.display_type == 'product' and aml.journal_id.company_consignment_id and aml.pos_order_line_id))
        res = super(InheritAccountMoveLine, record)._inverse_partner_id()
        return res
