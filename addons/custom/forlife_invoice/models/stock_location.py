from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class Location(models.Model):
    _inherit = 'stock.location'

    expense_item_id = fields.Many2one('expense.item', string='Mã khoản mục')