# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz


class PartnerCardRank(models.Model):
    _name = 'partner.card.rank'
    _description = 'Partner Card Rank'
    _inherit = ['mail.thread']
    _order = 'customer_id, brand_id, card_rank_id'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one("res.partner", string="Customer", required=True, ondelete='restrict')
    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    card_rank_id = fields.Many2one('card.rank', string='Rank', tracking=True, compute='compute_card_rank', store=True)
    accumulated_sales = fields.Integer('Accumulated Sales')
    last_order_date = fields.Datetime('Last Order Date')
    line_ids = fields.One2many('partner.card.rank.line', inverse_name='partner_card_rank_id', string='Lines')

    _sql_constraints = [
        ('data_uniq', 'unique (customer_id, brand_id)', 'Brand on Customer must be unique !'),
    ]

    @api.depends('line_ids')
    def compute_card_rank(self):
        for line in self:
            line.card_rank_id = line.line_ids and line.line_ids[0].new_card_rank_id.id or self.env.ref('forlife_customer_card_rank.card_rank_member').id

    def generate_card_rank_data(self):
        res = {}
        for line in self:
            _detail = ''
            for detail in line.line_ids:
                _detail += f"<tr style=\"text-align: center;\"><td>{detail.order_id and detail.order_id.name or ''}</td>" \
                         f"<td>{detail.order_date and detail.order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</td>" \
                         f"<td style=\"text-align: right !important;\">{'{:20,.0f}'.format(detail.value_orders or 0)}</td>" \
                         f"<td style=\"text-align: right !important;\">{'{:20,.0f}'.format(detail.value_to_upper or 0)}</td>" \
                         f"<td>{detail.old_card_rank_id.name}</td>" \
                         f"<td>{detail.new_card_rank_id.name}</td></tr>"
            value = f"<div class=\"row\">" \
                    f"<div class=\"col-2\"><b>Hạng:</b></div><div class=\"col-10\">{line.card_rank_id.name}</div>" \
                    f"<div class=\"col-2\"><b>Doanh số tích lũy:</b></div><div class=\"col-10\">{'{:20,.0f}'.format(line.accumulated_sales or 0)}</div>" \
                    f"<div class=\"col-2\"><b>Ngày mua gần nhất:</b></div>" \
                    f"<div class=\"col-10\">{line.last_order_date and line.last_order_date.astimezone(pytz.timezone(self.env.user.tz)).strftime('%d/%m/%Y') or ''}</div></div>" \
                    f"<br/><table class=\"table table-bordered\">" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\"><th colspan=\"6\">Lịch sử nâng hạng</th></tr>" \
                    f"<tr style=\"text-align: center; background: #031d74c7; color: #ffffff;\">" \
                    f"<th>Đơn hàng</th><th>Ngày mua hàng</th><th>Giá trị đơn hàng</th><th>Giá trị xét hạng</th><th>Hạng hiện tại</th><th>Hạng mới</th></tr>" \
                    f"{_detail}</table>"
            res.update({
                f'{line.brand_id.code}-{str(line.customer_id.id)}': value,
            })
        return res


class PartnerCardRankLine(models.Model):
    _name = 'partner.card.rank.line'
    _description = 'Partner Card Rank Line'
    _order = 'date desc'

    partner_card_rank_id = fields.Many2one("partner.card.rank", string="Partner Card Rank", required=True, ondelete='restrict')
    order_id = fields.Many2one('pos.order', string="Pos Order", ondelete='restrict')
    date = fields.Datetime('Date', default=fields.Datetime.now())
    order_date = fields.Datetime('Order Date')
    value_orders = fields.Integer('Value Orders')
    value_to_upper = fields.Integer('Value to upper')
    old_card_rank_id = fields.Many2one('card.rank', string='Old Rank', required=True, default=lambda self: self.env.ref('forlife_customer_card_rank.card_rank_member').id)
    new_card_rank_id = fields.Many2one('card.rank', string='New Rank', required=True)
