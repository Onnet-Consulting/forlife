# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HandleChangeRefund(models.Model):
    _name = 'handle.change.refund'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Handle Change And Refund Product'
    _rec_name = 'origin_order'
    _order = 'create_date desc'

    # name = fields.Char(_('Name'))
    pos_order_id = fields.Many2one('pos.order', string=_('Pos Order'))
    origin_order = fields.Char(_('Origin Order'), related='pos_order_id.pos_reference')
    send_approval_date = fields.Date(_('Send Approval Date'))
    store_id = fields.Many2one('store', _('Store'))
    state = fields.Selection(
        [('draft', _('Draft')),
         ('approved', _('Approved')),
         ('refuse', _('Refuse')),
         ('cancelled', _('Cancelled'))],
        default='draft', string=_('State'), tracking=True)
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    type = fields.Selection([('exchange_goods', 'Exchange Goods'), ('refund_goods', 'Refund Goods')], string=_('Type'))


    line_ids = fields.One2many('handle.change.refund.line', 'handle_change_refund_id', _('Details'))

    @api.model
    def create_from_ui(self, data):
        lst_line = []
        vals = {
            'pos_order_id': data.get('pos_order_id'),
            'send_approval_date': fields.Date.today(),
            'store_id': data.get('store'),
            'state': 'draft',
        }
        if data.get('is_change_product', False):
            vals.update({'type': 'exchange_goods'})
        if data.get('is_refund_product', False):
            vals.update({'type': 'refund_goods'})

        for line in data.get('lines'):
            lst_line.append((0, 0, {
                'product_id': line.get('product_id'),
                'purchase_price': line.get('price'),
                'expire_change_refund_date': line.get('expire_change_refund_date'),
                'reason_refund_id': line.get('reason_refund_id'),
                'pos_order_line_id': line.get('refunded_orderline_id')
            }))
        vals.update({'line_ids': lst_line})
        handle_change_refund_id = self.create(vals)
        self._send_mail_done(handle_change_refund_id.id)
        return handle_change_refund_id.id

    @api.model
    def _send_mail_done(self, id):
        mailTemplateModel = self.env['mail.template']
        irModelData = self.env['ir.model.data']
        templXmlId = irModelData._xmlid_to_res_id('forlife_pos_product_change_refund.email_template_handle_change_refund')
        baseUrl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirectUrl = baseUrl + '/web#id=%d&view_type=form&model=%s' % (id, self._name)
        if templXmlId:
            mailTmplObj = mailTemplateModel.browse(templXmlId)
            ctx = {
                'redirectUrl': redirectUrl,
            }
            mailTmplObj.with_context(**ctx).send_mail(id, force_send=True)

    def action_approve(self):
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refuse'

    @api.model
    def cancel_rc_handle_change_refund(self, data):
        if data.get('id'):
            handle_change_refund_id = self.browse(data.get('id'))
            handle_change_refund_id.write({
                'state': 'cancelled'
            })
        return True

    @api.model
    def get_data_update(self, data):
        return_price = 0
        if data.get('id'):
            handle_change_refund_id = self.browse(data.get('id'))
            for line in handle_change_refund_id.filtered(lambda x: x.state == 'approved').line_ids:
                return_price = line.purchase_price - line.return_price
                return {'price': return_price, 'status': 'approve'}
        return {'price': return_price, 'status': 'not_approve'}
