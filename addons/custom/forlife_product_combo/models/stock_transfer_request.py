from odoo import fields, models, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class StockTransferRequest(models.Model):
    _inherit = 'stock.transfer.request'
    _description = 'Forlife Stock Transfer'

    def check_wait_confirm_stock_transfer_request(self):
        date_check = datetime.now() - relativedelta(days=7)
        stocks = self.search([('date_planned', '<=', date_check), ('state', '=', 'wait_confirm')])

        # if self.user_has_groups('purchase.group_purchase_user'):
        #     bbb = self.user_has_groups('purchase.group_purchase_user')

        if stocks:
            mail_template = self.env.ref('forlife_product_combo.email_template_warning_unapproved_transfer_application', raise_if_not_found=False)
            for record in stocks:
                email_values = {
                    'email_to': 'ductv@forlife.vn',
                }
                mail_template.send_mail(record.id, force_send=True, email_values=email_values)

