from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError


class Location(models.Model):
    _inherit = 'stock.location'

    # partner_id = fields.Many2one('res.partner', string='Công ty', required=True)
    code = fields.Char(string='Mã', required=True)
    type_other = fields.Selection([('incoming', 'Nhập khác'), ('outcoming', 'Xuất khác')], string='Loại khác', required=True)
    valuation_out_account = fields.Many2one("account.account", string="Tài khoản định giá tồn kho (xuất hàng)")
    valuation_in_account = fields.Many2one("account.account", string="Tài khoản định giá tồn kho (nhập hàng)")
    reason_type_id = fields.Many2one('forlife.reason.type')


class StockMove(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.move'

    def _get_accounting_data_for_valuation(self):
        journal_id, acc_src, acc_dest, acc_valuation = super()._get_accounting_data_for_valuation()

        # Thay đổi giá trị của biến acc_valuation trước khi trả về
        acc_valuation = self.picking_id.location_dest_id.valuation_in_account.id if self.picking_id.location_dest_id.type_other else acc_valuation

        return journal_id, acc_src, acc_dest, acc_valuation

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.company_id.currency_id.round(cost)
        credit_value = debit_value

        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        if self.picking_id.location_dest_id.type_other == 'outcoming':
            debit_value = credit_value = self.price_unit * self.quantity_done
        res = [(0, 0, line_vals) for line_vals in self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value,
                                                   debit_account_id, credit_account_id, svl_id, description).values()]

        return res