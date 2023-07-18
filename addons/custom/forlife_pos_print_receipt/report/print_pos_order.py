from odoo import api, models


class PosOrderPrintReport(models.AbstractModel):
    _name = 'report.forlife_pos_print_receipt.print_order_pos_tmpl'

    @api.model
    def _get_report_values(self, docids, data=None):
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name(
            'forlife_pos_print_receipt.print_order_pos_tmpl')
        # get the records selected for this rendering of the report
        obj = self.env[report.model].browse(docids)

        # return a custom rendering context
        return {
            'docs': obj,
        }
