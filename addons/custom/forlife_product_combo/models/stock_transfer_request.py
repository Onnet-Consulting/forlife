from odoo import fields, models, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class StockTransferRequest(models.Model):
    _inherit = 'stock.transfer.request'
    _description = 'Forlife Stock Transfer'

    def check_wait_confirm_stock_transfer_request(self):
        date_check = datetime.now() - relativedelta(days=7)
        stocks = self.search([('date_planned', '<=', date_check), ('state', '=', 'wait_confirm')])

        user_ids = self.env.ref('purchase_request.admin_purchase_request_group').users.search([('state', '=', 'active')])

        if stocks:
            mail_template = self.env.ref('forlife_product_combo.email_template_warning_unapproved_transfer_application', raise_if_not_found=False)
            for record in stocks:
                for user in user_ids:
                    email_to = user.partner_id.email
                    if email_to:
                        mail_template.with_context(**{
                            'email_to': email_to
                        }).send_mail(record.id)

