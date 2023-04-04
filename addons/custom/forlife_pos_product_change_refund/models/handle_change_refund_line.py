# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HandleChangeRefundLine(models.Model):
    _name = 'handle.change.refund.line'

    handle_change_refund_id = fields.Many2one('handle.change.refund', _('Handle Change Refund'), ondelete='cascade')
    product_id = fields.Many2one('product.product', _('Product'))
    purchase_price = fields.Monetary(_('Purchase Price'))
    return_price = fields.Monetary(_('Return Price'))
    expire_change_refund_date = fields.Date(_('Expire Change Refund Date'))
    note = fields.Char(_('Note'))
    currency_id = fields.Many2one(related='handle_change_refund_id.currency_id', store=True, string='Currency')
    company_id = fields.Many2one('res.company', related='handle_change_refund_id.company_id', string='Company', store=True)