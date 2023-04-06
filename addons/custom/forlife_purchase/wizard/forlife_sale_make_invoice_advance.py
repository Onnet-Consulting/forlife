import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import json

class PurchaseOrder(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def forlife_create_invoices(self):
        invoice = self._create_invoices(self.sale_order_ids)

        if self.env.context.get('open_invoices'):
            return self.sale_order_ids.action_view_invoice()
        return invoice