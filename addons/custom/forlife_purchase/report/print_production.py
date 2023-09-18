from odoo import api, models


class PosOrderPrintReport(models.AbstractModel):
    _name = 'report.forlife_purchase.print_production_tmpl'

    @api.model
    def _get_report_values(self, docids, data=None):
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name(
            'forlife_purchase.print_print_production_action')
        # get the records selected for this rendering of the report
        obj = self.env[report.model].browse(docids)

        # return a custom rendering context
        return {
            'docs': obj
        }
