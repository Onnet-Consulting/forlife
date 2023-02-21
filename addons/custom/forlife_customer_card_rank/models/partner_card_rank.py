# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
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
    accumulated_sales = fields.Integer('Accumulated Sales', default=0)
    last_order_date = fields.Datetime('Last Order Date', compute='compute_value', store=True)
    line_ids = fields.One2many('partner.card.rank.line', inverse_name='partner_card_rank_id', string='Lines')

    _sql_constraints = [
        ('data_uniq', 'unique (customer_id, brand_id)', 'Brand on Customer must be unique !'),
    ]

    @api.depends('line_ids')
    def compute_value(self):
        for line in self:
            line.card_rank_id = line.line_ids and line.line_ids.sorted()[0].new_card_rank_id.id or self.env['card.rank'].search([], order='priority asc', limit=1).id
            order = line.line_ids.sorted().filtered(lambda f: f.order_id)
            line.last_order_date = order and order[0].order_date or False

    def generate_card_rank_data(self):
        res = {}
        for line in self:
            _detail = ''
            for detail in line.line_ids:
                _detail += f"<tr style=\"text-align: center;\">" \
                           f"<td>{detail.order_id and detail.order_id.name or ''}</td>" \
                           f"<td>{detail.order_date and detail.order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</td>" \
                           f"<td style=\"text-align: right !important;\">{'{:,.0f}'.format(detail.value_orders or 0)}</td>" \
                           f"<td style=\"text-align: right !important;\">{'{:,.0f}'.format(detail.value_to_upper or 0)}</td>" \
                           f"<td>{detail.old_card_rank_id.name}</td>" \
                           f"<td>{detail.new_card_rank_id.name}</td></tr>"
            value = f"<br/><div class=\"row\">" \
                    f"<div class=\"col-3\"><b>Hạng hiện tại:</b></div><div class=\"col-9\">{line.card_rank_id.name}</div>" \
                    f"<div class=\"col-3\"><b>Doanh số xét hạng hiện tại:</b></div><div class=\"col-9\">{'{:,.0f}'.format(line.accumulated_sales or 0)}</div>" \
                    f"<div class=\"col-3\"><b>Ngày mua gần nhất:</b></div>" \
                    f"<div class=\"col-9\">{line.last_order_date and line.last_order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</div></div>" \
                    f"<br/><table class=\"table table-bordered\">" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\"><th colspan=\"6\">LỊCH SỬ XÉT HẠNG</th></tr>" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\">" \
                    f"<th>Đơn hàng</th><th>Ngày mua hàng</th><th>Giá trị đơn hàng</th><th>Giá trị được xét hạng</th><th>Hạng hiện tại</th><th>Hạng mới</th></tr>" \
                    f"{_detail}</table>"
            res.update({
                f'{line.brand_id.code}-{str(line.customer_id.id)}': value,
            })
        return res


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _description = 'Partner Card Rank Line'
    _order = 'real_date desc, id desc'

    partner_card_rank_id = fields.Many2one("partner.card.rank", string="Partner Card Rank", required=True, ondelete='restrict')
    order_id = fields.Many2one('pos.order', string="Pos Order", ondelete='restrict')
    order_date = fields.Datetime('Order Date', default=fields.Datetime.now())
    real_date = fields.Datetime('Real Date', default=fields.Datetime.now())
    value_orders = fields.Integer('Value Orders')
    value_to_upper = fields.Integer('Value to upper')
    old_card_rank_id = fields.Many2one('card.rank', string='Old Rank', required=True, default=lambda self: self.env['card.rank'].search([], order='priority asc', limit=1))
    new_card_rank_id = fields.Many2one('card.rank', string='New Rank', required=True)
