# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HandleChangeRefundLine(models.Model):
    _name = 'handle.change.refund.line'
    _description = 'Handle Change refund line'

    handle_change_refund_id = fields.Many2one('handle.change.refund', _('Handle Change Refund'), ondelete='cascade')
    product_id = fields.Many2one('product.product', _('Product'))
    purchase_price = fields.Monetary(_('Purchase Price'))
    return_price = fields.Monetary(_('Return Price'))
    expire_change_refund_date = fields.Date(_('Expire Change Refund Date'))
    note = fields.Char(_('Note'))
    currency_id = fields.Many2one(related='handle_change_refund_id.currency_id', store=True, string='Currency')
    company_id = fields.Many2one('res.company', related='handle_change_refund_id.company_id', string='Company', store=True)
    reason_refund_id = fields.Many2one('pos.reason.refund', 'Reason Refund')
    pos_order_line_id = fields.Many2one('pos.order.line', string='Pos Order Line')

    def action_open_lines_root(self):
        view_id = self.env.ref('forlife_pos_product_change_refund.pos_order_line_handle_change_refund_form_view').id
        context = dict(self.env.context)
        # context.update({'create': 0, 'edit': 0})
        return {
            'name': _('Pos Order Line'),
            'res_model': 'pos.order.line',
            'view_mode': 'form',
            'res_id': self.pos_order_line_id.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new'
        }