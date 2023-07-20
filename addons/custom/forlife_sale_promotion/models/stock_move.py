# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, OrderedSet

import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        self = self.with_company(self.company_id)
        accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        acc_src = self._get_src_account(accounts_data)
        acc_dest = self._get_dest_account(accounts_data)

        order_line = self.sale_line_id.order_id.order_line

        # begin inherit
        # kiểm tra đơn hàng nếu tất cả sp đều check là hàng tặng thì lấy tk hàng tặng trong sp ngược lại phụ thuộc vào
        # đơn online hay bán buôn để lấy tk chi phí bán buôn hoặc chi online
        if order_line and all(line.x_free_good for line in order_line):
            if self.product_id.categ_id.product_gift_account_id:
                acc_dest = self.product_id.categ_id.product_gift_account_id.id
        elif self.picking_id.sale_id.x_sale_chanel == "online":
            if self.product_id.categ_id.expense_online_account_id:
                acc_dest = self.product_id.categ_id.expense_online_account_id.id
        elif self.picking_id.sale_id.x_sale_chanel == "wholesale":
            if self.product_id.categ_id.expense_sale_account_id:
                acc_dest = self.product_id.categ_id.expense_sale_account_id.id

        # end inherit====================#

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation