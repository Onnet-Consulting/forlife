# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlrd
import base64


class WizardIncreaseDecreaseInvoice(models.TransientModel):
    _name = 'wizard.increase.decrease.invoice'
    _description = 'Increase Decrease Invoice Wizard'
    _inherit = 'report.base'

    origin_invoice_id = fields.Many2one('account.move', string='Move Origin')
    invoice_type = fields.Selection([('increase', 'Tăng'), ('decrease', 'Giảm')], string='Type', default='increase')
    selected_all = fields.Boolean(string='Selected all')
    line_ids = fields.One2many('wizard.increase.decrease.invoice.line', 'parent_id', string='Detail')
    import_file = fields.Binary(attachment=False, string='File nhập')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='File lỗi')
    error_file_name = fields.Char(default='Tệp lỗi.txt')

    @api.onchange('selected_all')
    def onchange_selected_all(self):
        self.line_ids.write({
            'is_selected': self.selected_all
        })

    @api.onchange('origin_invoice_id')
    def onchange_origin_invoice_id(self):
        for rec in self:
            vals_line = []
            if rec.origin_invoice_id.select_type_inv == 'normal':
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
            else:
                if rec.origin_invoice_id.account_expense_labor_detail_ids:
                    for line in rec.origin_invoice_id.account_expense_labor_detail_ids:
                        vals_line.append((0, 0, {
                            'product_id': line.product_id.id,
                            'uom_id': line.uom_id.id,
                            'quantity': line.qty,
                            'price_subtotal': line.price_subtotal_back,
                            'tax_amount': line.tax_back,
                            'price_total': line.totals_back,
                            'tax_ids': line.tax_percent,
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
                'select_type_inv': self.origin_invoice_id.select_type_inv,
                'move_type': move_type,
                'reference': self.origin_invoice_id.name,
                # 'cost_line': False,
                'vendor_back_ids': False,
                'invoice_date': fields.Date.today(),
                'pos_order_id': False,
                'direction_sign': 1 if move_type == 'in_invoice' else -1,
                'purchase_order_product_id': [(6, 0, self.origin_invoice_id.purchase_order_product_id.ids)],
                'receiving_warehouse_id': [(6, 0, self.origin_invoice_id.receiving_warehouse_id.ids)],
            })
            if self.origin_invoice_id.select_type_inv == 'normal':
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
                    # Daihv: cập nhật giá nhà cung cấp từ popup Tăng/giảm hóa đơn
                    wz_invoice_line_id = self.line_ids.filtered(lambda s: s.product_id.id == line_id.product_id.id and s.quantity == line_id.quantity)
                    if wz_invoice_line_id and line_id.display_type == 'product':
                        line_id.write({'vendor_price': wz_invoice_line_id[0].vendor_price})
                        line_id.onchange_vendor_price()
                total_tax = sum(move_copy_id.line_ids.filtered(lambda f: f.display_type == 'product').mapped('tax_amount'))
                move_copy_id.line_ids.filtered(lambda f: f.display_type == 'tax').write({
                    'debit': total_tax,
                    'balance': total_tax,
                    'amount_currency': total_tax,
                })
            else:
                lst_expense = []
                for line in self.line_ids.filtered(lambda x: x.is_selected):
                    vals_line = {
                        'product_id': line.product_id.id,
                        'uom_id': line.uom_id.id,
                        'qty': line.quantity,
                        'price_subtotal_back': line.price_subtotal,
                        'tax_back': line.tax_amount,
                        'totals_back': line.price_total,
                        'tax_percent': line.tax_ids,
                    }
                    lst_expense.append((0, 0, vals_line))
                move_copy_id.write({
                    'account_expense_labor_detail_ids': lst_expense,
                })
                move_copy_id.create_invoice_expense_purchase()

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
                        'vendor_price': line.vendor_price,
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
                        'vendor_price': line.vendor_price,
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

    def get_filename(self):
        return f"Mẫu nhập tăng_giảm hóa đơn {self.name}"

    def generate_xlsx_report(self, workbook, allowed_company):
        if not self.line_ids:
            raise ValidationError('Dữ liệu Chi tiết hóa đơn trống.')
        sheet = workbook.add_worksheet('Chi tiết')
        formats = self.get_format_workbook(workbook)
        TITLES = [
            'ID', 'Sản phẩm', 'ĐVT', 'Số lượng', 'Tỷ lệ quy đổi', '% chiết khấu',
            'Giá nhà cung cấp', 'Đơn giá', 'Thành tiền', 'Tiền thuế', 'Tổng tiền'
                  ]
        for idx, title in enumerate(TITLES):
            sheet.write(0, idx, title, formats.get('title_format'))
        sheet.set_column(0, len(TITLES) - 1, 20)
        row = 1
        for line in self.line_ids:
            r = row + 1
            sheet.write(row, 0, line.invoice_line_id.id or line.id, formats.get('center_format'))
            sheet.write(row, 1, line.product_id.name, formats.get('normal_format'))
            sheet.write(row, 2, line.uom_id.name, formats.get('normal_format'))
            sheet.write(row, 3, line.quantity, formats.get('int_number_format'))
            sheet.write(row, 4, line.exchange_quantity, formats.get('float_number_format'))
            sheet.write(row, 5, line.discount / 100, formats.get('percentage_format'))
            sheet.write(row, 6, line.vendor_price, formats.get('int_number_format'))
            sheet.write_formula(row, 7, "IF(E{0}>0,G{0}/E{0},G{0})".format(r), formats.get('int_number_format'))
            sheet.write_formula(row, 8, "H{0}*D{0}*(1-F{0})".format(r), formats.get('int_number_format'))
            sheet.write_formula(row, 9, "{0}*I{1}".format(sum(line.tax_ids.mapped('amount')) / 100, r), formats.get('int_number_format'))
            sheet.write_formula(row, 10, "I{0}".format(r), formats.get('int_number_format'))
            row += 1

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        if not self.line_ids:
            raise ValidationError('Dữ liệu Chi tiết hóa đơn trống.')
        self.ensure_one()
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút nhập !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        data_import = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        if not data_import:
            return self.return_error_log('Dữ liệu nhập trống.')
        error = []
        data_write = []
        key = 'invoice_line_id' if self.line_ids[0].invoice_line_id else 'id'
        self._cr.execute(f"""select json_object_agg({key}, array[vendor_price, id]) as data
                                    from wizard_increase_decrease_invoice_line
                                    where parent_id = {self.id}""")
        old_price_data = self._cr.fetchone()[0] or {}
        for index, data in enumerate(data_import, start=2):
            if not data[0] or not old_price_data.get(data[0]):
                error.append(f"Dòng {index}: ID '{data[0]}' không khớp với dữ liệu trong tab Chi tiết hóa đơn")
            elif not error:
                old_vendor_price, line_id = old_price_data.get(data[0])
                new_vendor_price = float(data[6])
                if old_vendor_price != new_vendor_price:
                    data_write.append((1, line_id, {
                        'vendor_price': new_vendor_price,
                        'is_selected': True,
                    }))
        if error:
            return self.return_error_log('\n'.join(error))
        elif data_write:
            self.write({'line_ids': data_write})
            self.line_ids.onchange_method()
        return self.return_error_log()

    def return_error_log(self, error=''):
        if error:
            self.write({
                'error_file': base64.encodebytes(error.encode()),
                'import_file': False,
            })
        action = self.env.ref('forlife_invoice.wizard_increase_decrease_invoice_action').read()[0]
        action['res_id'] = self.id
        return action


class WizardIncreaseDecreaseInvoiceLine(models.TransientModel):
    _name = 'wizard.increase.decrease.invoice.line'
    _description = 'Increase Decrease Invoice Line Wizard'

    product_id = fields.Many2one(comodel_name='product.product', string='Product', ondelete='restrict', )
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure', )
    parent_id = fields.Many2one('wizard.increase.decrease.invoice', string='Parent')
    price_unit = fields.Float(string='Unit Price')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", ondelete='restrict')
    invoice_line_id = fields.Many2one('account.move.line', string='Move Line')
    quantity = fields.Float(string='Quantity')
    price_subtotal = fields.Monetary(string='Subtotal')
    price_total = fields.Monetary(string='Total')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0,)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency')
    is_refund = fields.Boolean()
    tax_amount = fields.Float(string='Tax Amount')
    vendor_price = fields.Float(string="Vendor Price")
    exchange_quantity = fields.Float(string="Exchange Quantity", related='invoice_line_id.exchange_quantity')
    is_selected = fields.Boolean(string='Selected')

    @api.onchange('vendor_price')
    def onchange_method(self):
        for line in self:
            _price_subtotal = line.vendor_price * line.invoice_line_id.quantity_purchased * (1 - line.discount / 100)
            line.price_unit = line.vendor_price / line.exchange_quantity if line.exchange_quantity else line.vendor_price
            line.tax_amount = _price_subtotal * sum(line.tax_ids.mapped('amount')) / 100
            line.price_subtotal = _price_subtotal
            line.price_total = _price_subtotal
            line.is_selected = True

