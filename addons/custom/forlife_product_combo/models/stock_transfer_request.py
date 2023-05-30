from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class StockTransferRequest(models.Model):
    _inherit = 'stock.transfer.request'
    _description = 'Forlife Stock Transfer'

    def check_wait_confirm_stock_transfer_request(self):

        template = self.env.ref('purchase.email_template_edi_purchase_reminder', raise_if_not_found=False)
        #
        date_check = datetime.now() - relativedelta(days=7)

        stocks = self.search(
            [('date_planned', '<', date_check), ('state', '=', 'wait_confirm')])

