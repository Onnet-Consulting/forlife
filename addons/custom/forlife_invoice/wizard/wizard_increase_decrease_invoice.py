# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WizardIncreaseDecreaseInvoice(models.TransientModel):
    _name = 'wizard.increase.decrease.invoice'
    _description = 'Increase Decrease Invoice Wizard'

    origin_invoice_id = fields.Many2one('account.move', string='Move Origin')
    invoice_type = fields.Selection([('increase', 'Tăng'), ('decrease', 'Giảm')], string='Type', default='increase')
    selected_all = fields.Boolean(string='Selected all')
    line_ids = fields.One2many('wizard.increase.decrease.invoice.line', 'parent_id', string='Detail')

    @api.onchange('selected_all')
    def onchange_selected_all(self):
        self.line_ids.write({
            'is_selected': self.selected_all
        })

    @api.onchange('origin_invoice_id')
    def onchange_origin_invoice_id(self):
        for rec in self:
            vals_line = []
            if rec.origin_invoice_id.invoice_line_ids:
                for line in rec.origin_invoice_id.invoice_line_ids:
                    vals_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'tax_ids': line.tax_ids.ids or False,
                        'invoice_line_id': line.id,
                        'quantity': line.quantity,
                        'price_subtotal': line.price_subtotal,
                        'price_total': line.price_total,
                        'discount': line.discount,
                        'currency_id': line.currency_id.id or False,
                        'is_refund': line.is_refund,
                        'tax_amount': line.tax_amount,
                        'vendor_price': line.vendor_price,
                    }))
            if vals_line:
                rec.write({
                    'line_ids': vals_line
                })

    def action_confirm(self):
        if self.line_ids.filtered(lambda x: x.is_selected):
            move_type = 'in_invoice' if (self.origin_invoice_id.move_type == 'in_invoice' and self.invoice_type == 'increase') or (self.invoice_type == 'decrease' and self.origin_invoice_id.move_type == 'in_refund') else 'in_refund'
            move_copy_id = self.origin_invoice_id.copy({
                'invoice_type': self.invoice_type,
                'origin_invoice_id': self.origin_invoice_id.id,
                'move_type': move_type,
                'reference': self.origin_invoice_id.name,
                'cost_line': False,
                'vendor_back_ids': False,
                'invoice_date': fields.Date.today(),
                'pos_order_id': False,
                'direction_sign': 1 if move_type == 'in_invoice' else -1,
            })
            product_ids = self.line_ids.filtered(lambda x: not x.is_selected).mapped('product_id')
            if product_ids:
                line_remove = move_copy_id.line_ids.filtered(lambda x: x.product_id.id in product_ids.ids)
                line_remove.unlink()
            for line_id in move_copy_id.line_ids:
                if line_id.display_type == 'tax' and move_copy_id.move_type == 'in_invoice' and line_id.credit > 0:
                    line_id.update({
                        'debit': line_id.credit,
                        'credit': 0,
                        'amount_tax': line_id.credit,
                        'balance': line_id.credit,
                        'amount_currency': abs(line_id.amount_currency),
                    })

                # if line_id.product_id:
                #     if not line_id.product_id.categ_id.property_stock_account_input_categ_id.id:
                #         raise ValidationError(_('Vui lòng cấu hình tài khoản nhập kho trong Nhóm sản phẩm %s' % line_id.product_id.display_name))
                #     line_id.write({
                #         'account_id': line_id.product_id.categ_id.property_stock_account_input_categ_id.id,
                #         'purchase_line_id': False
                #     })


            # check_move_type = True if (self.invoice_type == 'increase' and self.origin_invoice_id.move_type == 'in_invoice') or \
            #         (self.invoice_type == 'decrease' and self.origin_invoice_id.move_type == 'in_refund') else False
            # move_copy_id.write({
            #     'line_ids': self.prepare_move_line(),
            #     'direction_sign': 1 if check_move_type else -1,
            # })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.move',
                'views': [(self.env.ref('account.view_move_form').id, 'form')],
                'view_id': self.env.ref('account.view_move_form').id,
                'target': 'current',
                'res_id': move_copy_id.id,
            }
        else:
            raise ValidationError(_('Please select at least 1 line to create an Increment/Decrease entry!'))

    def prepare_move_line(self):
        move_line_vals = []
        account_payable_id = self.origin_invoice_id.partner_id.property_account_payable_id
        line_ids = self.line_ids.filtered(lambda x: x.is_selected)
        amount_payable = int(sum(line_ids.mapped('price_subtotal')) + sum(line_ids.mapped('tax_amount')))
        tax_lines = []
        for line in line_ids:
            account_id = line.account_id
            taxes_res = []
            if line.tax_ids:
                line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=self.origin_invoice_id.partner_id,
                    is_refund=line.is_refund,
                )
            if (self.invoice_type == 'increase' and self.origin_invoice_id.move_type == 'in_invoice') or \
                    (self.invoice_type == 'decrease' and self.origin_invoice_id.move_type == 'in_refund'):
                tax_mount = 0
                if taxes_res:
                    for tax in taxes_res['taxes']:
                        if tax['account_id'] and tax['amount']:
                            if tax_lines:
                                update = False
                                for tax_line in tax_lines:
                                    if tax['id'] == tax_line['tax_id']:
                                        tax_line.update({
                                            'balance': tax_line['balance'] + tax['amount'],
                                            'debit': tax_line['debit'] + tax['amount'],
                                            'amount_currency': tax_line['amount_currency'] + tax['amount'],
                                            'tax_base_amount': tax_line['tax_base_amount'] + tax['base'],
                                        })
                                        update = True
                                if not update:
                                    tax_lines.append({
                                        'tax_id': tax['id'],
                                        'name': tax['name'],
                                        'tax_ids': [(6, 0, tax['tax_ids'])],
                                        'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                                        'balance': tax['amount'],
                                        'debit': tax['amount'],
                                        'credit': 0,
                                        'account_id': tax['account_id'] or False,
                                        'amount_currency': tax['amount'],
                                        'tax_base_amount': tax['base'],
                                        'tax_repartition_line_id': tax['tax_repartition_line_id'],
                                        'group_tax_id': tax['group'] and tax['group'].id or False,
                                        'display_type': 'tax',
                                    })
                            else:
                                tax_lines.append({
                                    'tax_id': tax['id'],
                                    'name': tax['name'],
                                    'tax_ids': [(6, 0, tax['tax_ids'])],
                                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                                    'balance': tax['amount'],
                                    'debit': tax['amount'],
                                    'credit': 0,
                                    'account_id': tax['account_id'] or False,
                                    'amount_currency': tax['amount'],
                                    'tax_base_amount': tax['base'],
                                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                                    'group_tax_id': tax['group'] and tax['group'].id or False,
                                    'display_type': 'tax',
                                })
                move_line_vals += [
                    (0, 0, {
                        'account_id': account_id.id,
                        'product_id': line.product_id.id,
                        'debit': int(line.price_subtotal),
                        'credit': 0,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'balance': int(line.price_subtotal),
                        'amount_currency': int(line.price_subtotal),
                        'tax_ids': [(6, 0, line.tax_ids.ids)] or False,
                        'discount': line.discount,
                        'currency_id': line.currency_id.id or False,
                        'is_refund': line.is_refund,
                        'display_type': 'product',
                        'tax_amount': tax_mount,
                        'product_uom_id': line.uom_id.id,
                        'quantity_purchased': line.invoice_line_id.quantity_purchased,
                        'exchange_quantity': line.invoice_line_id.exchange_quantity,
                        'vendor_price': line.invoice_line_id.vendor_price,
                        'discount_percent': line.invoice_line_id.discount_percent,
                        'purchase_uom': line.invoice_line_id.purchase_uom.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                    })
                ]
            else:
                tax_mount = 0
                if taxes_res:
                    for tax in taxes_res['taxes']:
                        if tax['account_id'] and tax['amount']:
                            if tax_lines:
                                update = False
                                for tax_line in tax_lines:
                                    if tax['id'] == tax_line['tax_id']:
                                        tax_line.update({
                                            'balance': tax_line['balance'] - tax['amount'],
                                            'credit': tax_line['credit'] + tax['amount'],
                                            'amount_currency': tax_line['amount_currency'] - tax['amount'],
                                            'tax_base_amount': tax_line['tax_base_amount'] + tax['base'],
                                            'tax_amount': tax_line['tax_amount'] + abs(tax['amount']),
                                        })
                                        update = True
                                if not update:
                                    tax_lines.append({
                                        'tax_id': tax['id'],
                                        'name': tax['name'],
                                        'tax_ids': [(6, 0, tax['tax_ids'])],
                                        'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                                        'balance': -tax['amount'],
                                        'debit': 0,
                                        'credit': tax['amount'],
                                        'account_id': tax['account_id'] or False,
                                        'amount_currency': -tax['amount'],
                                        'tax_amount': abs(tax['amount']),
                                        'tax_base_amount': tax['base'],
                                        'tax_repartition_line_id': tax['tax_repartition_line_id'],
                                        'group_tax_id': tax['group'] and tax['group'].id or False,
                                        'display_type': 'tax',
                                    })
                            else:
                                tax_lines.append({
                                    'tax_id': tax['id'],
                                    'name': tax['name'],
                                    'tax_ids': [(6, 0, tax['tax_ids'])],
                                    'tax_tag_ids': [(6, 0, tax['tag_ids'])],
                                    'balance': -tax['amount'],
                                    'debit': 0,
                                    'credit': tax['amount'],
                                    'account_id': tax['account_id'] or False,
                                    'amount_currency': -tax['amount'],
                                    'tax_amount': abs(tax['amount']),
                                    'tax_base_amount': tax['base'],
                                    'tax_repartition_line_id': tax['tax_repartition_line_id'],
                                    'group_tax_id': tax['group'] and tax['group'].id or False,
                                    'display_type': 'tax',
                                })
                move_line_vals += [
                    (0, 0, {
                        'account_id': account_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'debit': 0,
                        'credit': int(line.price_subtotal),
                        'balance': -int(line.price_subtotal),
                        'amount_currency': -int(line.price_subtotal),
                        'display_type': 'product',
                        'tax_ids': [(6, 0, line.tax_ids.ids)] or False,
                        'discount': line.discount,
                        'currency_id': line.currency_id.id or False,
                        'is_refund': line.is_refund,
                        'tax_amount': tax_mount,
                        'product_uom_id': line.uom_id.id,
                        'quantity_purchased': line.invoice_line_id.quantity_purchased,
                        'exchange_quantity': line.invoice_line_id.exchange_quantity,
                        'vendor_price': line.invoice_line_id.vendor_price,
                        'discount_percent': line.invoice_line_id.discount_percent,
                        'purchase_uom': line.invoice_line_id.purchase_uom.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                    })
                ]

        if tax_lines:
            for value_tax in tax_lines:
                del value_tax['tax_id']
                move_line_vals.append(
                    (0, 0, value_tax)
                )
        if self.invoice_type == 'increase':
            move_line_vals.append(
                (0, 0, {
                    'account_id': account_payable_id.id,
                    'debit': 0,
                    'credit': amount_payable,
                    'balance': -amount_payable,
                    'amount_currency': -amount_payable,
                    'display_type': 'payment_term',
                })
            )
        else:
            move_line_vals.append(
                (0, 0, {
                    'account_id': account_payable_id.id,
                    'debit': amount_payable,
                    'credit': 0,
                    'balance': amount_payable,
                    'amount_currency': amount_payable,
                    'display_type': 'payment_term',
                })
            )
        return move_line_vals


class WizardIncreaseDecreaseInvoiceLine(models.TransientModel):
    _name = 'wizard.increase.decrease.invoice.line'
    _description = 'Increase Decrease Invoice Line Wizard'

    product_id = fields.Many2one(comodel_name='product.product', string='Product', ondelete='restrict', )
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure', )
    parent_id = fields.Many2one('wizard.increase.decrease.invoice', string='Parent')
    price_unit = fields.Float(string='Unit Price', digits='Product Price', )
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", ondelete='restrict')
    invoice_line_id = fields.Many2one('account.move.line', string='Move Line')
    quantity = fields.Float(string='Quantity')
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_totals', )
    price_total = fields.Monetary(string='Total', compute='_compute_totals', )
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0,)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency')
    is_refund = fields.Boolean()
    tax_amount = fields.Float(string='Tax Amount', )
    vendor_price = fields.Float(string="Vendor Price")
    is_selected = fields.Boolean(string='Selected')

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'tax_amount')
    def _compute_totals(self):
        for line in self:
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.parent_id.origin_invoice_id.partner_id,
                    is_refund=line.is_refund,
                )
                line.tax_amount = taxes_res['taxes'][0]['amount']
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal
