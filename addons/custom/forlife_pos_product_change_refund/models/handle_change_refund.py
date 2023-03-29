# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HandleChangeRefund(models.Model):
    _name = 'handle.change.refund'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Handle Change And Refund Product'
    _order = 'create_date desc'

    # name = fields.Char(_('Name'))
    origin_order = fields.Char(_('Origin Order'))
    pos_order_id = fields.Many2one('pos.order', string=_('Pos Order'))
    send_approval_date = fields.Date(_('Send Approval Date'))
    store_id = fields.Many2one('store', _('Store'))
    state = fields.Selection(
        [('draft', _('Draft')),
         ('approved', _('Approved')),
         ('refuse', _('Refuse')),
         ('cancelled', _('Cancelled'))],
        default='draft', string=_('State'))
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)


    line_ids = fields.One2many('handle.change.refund.line', 'handle_change_refund_id', _('Details'))

    @api.model
    def create_from_ui(self, data):
        lst_line = []
        vals = {
            'pos_order_id': data.get('pos_order_id'),
            'origin_order': data.get('name'),
            'send_approval_date': fields.Date.today(),
            'store_id': data.get('store'),
            'state': 'draft',
        }
        for line in data.get('lines'):
            lst_line.append((0, 0, {
                'product_id': line.get('product_id'),
                'purchase_price': line.get('price'),
                # 'expire_change_refund_date':
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
