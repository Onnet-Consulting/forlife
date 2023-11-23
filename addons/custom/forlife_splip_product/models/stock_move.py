# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round, float_is_zero, float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    split_line_sub_id = fields.Many2one('split.product.line.sub', string='Sản phẩm phân rã')