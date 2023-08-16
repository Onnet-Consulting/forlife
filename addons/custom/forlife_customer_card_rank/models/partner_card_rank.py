# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta
import pytz


class PartnerCardRank(models.Model):
    _name = 'partner.card.rank'
    _description = 'Partner Card Rank'
    _inherit = ['mail.thread']
    _order = 'customer_id, brand_id, card_rank_id'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one("res.partner", string="Customer", required=True, ondelete='restrict')
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    card_rank_id = fields.Many2one('card.rank', string='Rank', tracking=True, compute='compute_value', store=True)
    accumulated_sales = fields.Integer('Accumulated Sales', compute='compute_value', store=True)
    last_order_date = fields.Datetime('Last Order Date', compute='compute_value', store=True)
    line_ids = fields.One2many('partner.card.rank.line', inverse_name='partner_card_rank_id', string='Lines')
    status = fields.Boolean('Status', compute='_compute_status')

    _sql_constraints = [
        ('data_uniq', 'unique (customer_id, brand_id)', 'Brand on Customer must be unique !'),
    ]

    @api.depends('line_ids')
    def _compute_status(self):
        for item in self:
            item.status = False
            if item.line_ids:
                if any(x.status for x in item.line_ids):
                    item.status = True

    @api.depends('line_ids')
    def compute_value(self):
        for line in self:
            line.card_rank_id = line.line_ids and line.line_ids.sorted()[0].new_card_rank_id.id or False
            records = line.line_ids.sorted().filtered(lambda f: f.value_to_upper != 0)
            record = records and records[0] or False
            if record:
                line.last_order_date = record.order_date
                line.accumulated_sales = sum(records.filtered(lambda f: f.order_date >= (
                        record.order_date - timedelta(record.program_cr_id.time_set_rank))).mapped('value_to_upper'))
            else:
                line.last_order_date = False
                line.accumulated_sales = 0

    def generate_card_rank_data(self):
        res = {}
        for line in self:
            _detail = ''
            for detail in line.line_ids:
                _detail += f"<tr style=\"text-align: center;\">" \
                           f"<td>{detail.name or ''}</td>" \
                           f"<td>{detail.order_date and detail.order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</td>" \
                           f"<td style=\"text-align: right !important;\">{'{:,.0f}'.format(detail.value_orders or 0)}</td>" \
                           f"<td style=\"text-align: right !important;\">{'{:,.0f}'.format(detail.value_to_upper or 0)}</td>" \
                           f"<td>{detail.old_card_rank_id.name}</td>" \
                           f"<td>{detail.new_card_rank_id.name}</td>" \
                           f"<td>{'x' if detail.status else ''}</td></tr>"
            value = f"<br/><div class=\"row\">" \
                    f"<div class=\"col-3\"><b>Hạng hiện tại:</b></div><div class=\"col-9\">{line.card_rank_id.name}</div>" \
                    f"<div class=\"col-3\"><b>Doanh số xét hạng hiện tại:</b></div><div class=\"col-9\">{'{:,.0f}'.format(line.accumulated_sales or 0)}</div>" \
                    f"<div class=\"col-3\"><b>Ngày mua gần nhất:</b></div>" \
                    f"<div class=\"col-9\">{line.last_order_date and line.last_order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</div></div>" \
                    f"<br/><table class=\"table table-bordered\">" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\"><th colspan=\"7\">LỊCH SỬ XÉT HẠNG</th></tr>" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\">" \
                    f"<th>Đơn hàng</th><th>Ngày mua hàng</th><th>Giá trị đơn hàng</th><th>Giá trị được xét hạng</th><th>Hạng hiện tại</th><th>Hạng mới</th><th>Trạng Thái</th></tr>" \
                    f"{_detail}</table>"
            res.update({
                f'{line.brand_id.code}-{str(line.customer_id.id)}': value,
            })
        return res

    @api.model
    def create_partner_card_rank(self, pos_order, invoice, value_to_upper_order, program_id, rank_id):
        if pos_order:
            customer_id = pos_order.partner_id.id
            brand_id = pos_order.config_id.store_id.brand_id.id
            name = pos_order.name
            order_id = pos_order.id
            invoice_id = False
            order_date = pos_order.date_order
            real_date = pos_order.create_date
            value_orders = pos_order.amount_total
        elif invoice:
            sale_id = invoice.line_ids.sale_line_ids.order_id
            sale_id = sale_id and sale_id[0] or sale_id
            customer_id = sale_id.order_partner_id.id
            brand_id = sale_id.x_location_id.warehouse_id.brand_id.id
            name = invoice.name or ''
            order_id = False
            invoice_id = invoice.id
            order_date = invoice.invoice_date
            real_date = invoice.invoice_date
            value_orders = invoice.amount_residual
        else:
            return False
        self.sudo().create({
            'customer_id': customer_id,
            'brand_id': brand_id,
            'line_ids': [(0, 0, {
                'name': name,
                'order_id': order_id,
                'invoice_id': invoice_id,
                'order_date': order_date,
                'real_date': real_date,
                'value_orders': value_orders,
                'value_to_upper': value_to_upper_order,
                'old_card_rank_id': rank_id,
                'new_card_rank_id': rank_id,
                'value_up_rank': 0,
                'program_cr_id': program_id,
                'status': True
            })]
        })
        return True


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _description = 'Partner Card Rank Line'
    _order = 'real_date desc, id desc'

    name = fields.Char('Order', default='')
    partner_card_rank_id = fields.Many2one("partner.card.rank", string="Partner Card Rank", required=True, ondelete='restrict')
    order_id = fields.Many2one('pos.order', string="Pos Order", ondelete='restrict')
    invoice_id = fields.Many2one('account.move', string="Nhanh Order", ondelete='restrict')
    order_date = fields.Datetime('Order Date', default=fields.Datetime.now)
    real_date = fields.Datetime('Real Date', default=fields.Datetime.now)
    value_orders = fields.Integer('Value Orders')
    value_to_upper = fields.Integer('Value to upper')
    value_up_rank = fields.Integer('Value up rank')
    old_card_rank_id = fields.Many2one('card.rank', string='Old Rank', required=True, default=lambda self: self.env['card.rank'].search([], order='priority asc', limit=1))
    new_card_rank_id = fields.Many2one('card.rank', string='New Rank', required=True)
    program_cr_id = fields.Many2one('member.card', string='Program Card Rank', required=True)
    status = fields.Boolean('Status', default=False, copy=False)
    is_change_rank = fields.Boolean('Change rank', compute='_compute_change_rank', store=True)

    @api.depends('old_card_rank_id', 'new_card_rank_id')
    def _compute_change_rank(self):
        for line in self:
            line.is_change_rank = True if line.old_card_rank_id != line.new_card_rank_id else False

    @api.onchange('program_cr_id')
    def onchange_program_cr(self):
        self.new_card_rank_id = self.program_cr_id.card_rank_id
        self.status = True

    @api.model_create_multi
    def create(self, vals_list):
        recs = super(PartnerCardRankLine, self).create(vals_list)
        for rec in recs:
            self._update_card_rank_line(rec)
        return recs

    def _update_card_rank_line(self, rec):
        line_ids = self.sudo().search(
            [('id', '!=', rec.id), ('partner_card_rank_id', '=', rec.partner_card_rank_id.id), ('status', '=', True)])
        for line_id in line_ids:
            line_id.write({
                'status': False
            })

    @api.model
    def create_partner_card_rank_detail(self, pos_order, invoice, pcr_id, value_to_upper, old_rank_id, new_rank_id, total_value_to_up, program_id):
        self.sudo().browse(pcr_id).filtered(lambda f: f.status).write({'status': False})
        if pos_order:
            name = pos_order.name
            order_id = pos_order.id
            invoice_id = False
            order_date = pos_order.date_order
            real_date = pos_order.create_date
            value_orders = pos_order.amount_total
        elif invoice:
            name = invoice.name or ''
            order_id = False
            invoice_id = invoice.id
            order_date = invoice.invoice_date
            real_date = invoice.invoice_date
            value_orders = invoice.amount_residual
        else:
            return False
        self.sudo().create({
            'partner_card_rank_id': pcr_id,
            'name': name,
            'order_id': order_id,
            'invoice_id': invoice_id,
            'order_date': order_date,
            'real_date': real_date,
            'value_orders': value_orders,
            'value_to_upper': value_to_upper,
            'old_card_rank_id': old_rank_id,
            'new_card_rank_id': new_rank_id,
            'value_up_rank': total_value_to_up if old_rank_id != new_rank_id else 0,
            'program_cr_id': program_id,
            'status': True if old_rank_id != new_rank_id else False
        })
