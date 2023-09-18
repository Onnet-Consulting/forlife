# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.account.wizard.accrued_orders import AccruedExpenseRevenue as AccruedExpenseRevenueInherit


def create_entries(self):
    self.ensure_one()

    if self.reversal_date <= self.date:
        raise UserError(_('Reversal date must be posterior to date.'))

    move_vals, orders_with_entries = self._compute_move_vals()
    move = self.env['account.move'].create(move_vals)
    move._post()
    for order in orders_with_entries:
        body = _(
            'Accrual entry created on %(date)s: %(accrual_entry)s',
            date=self.date,
            accrual_entry=move._get_html_link()
        )
        order.message_post(body=body)
    return {
        'name': _('Accrual Moves'),
        'type': 'ir.actions.act_window',
        'res_model': 'account.move',
        'view_mode': 'tree,form',
        'domain': [('id', '=', move.id)],
    }

AccruedExpenseRevenueInherit.create_entries = create_entries

