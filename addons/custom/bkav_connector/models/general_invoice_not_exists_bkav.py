# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta, time


class GeneralInvoiceNotExistsBkav(models.Model):
    _name = 'invoice.not.exists.bkav'
    _description = 'General Invoice Not Exists Bkav'
    _rec_name = 'id'
    _order = 'id desc'

    move_date = fields.Date('Move date', copy=False)
    # trạng thái và số hdđt từ bkav trả về
    invoice_guid = fields.Char('Invoice Guid', copy=False)
    invoice_no = fields.Char('Invoice no', copy=False)
    invoice_e_date = fields.Char('Invoice e date', copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    invoice_ids = fields.One2many('account.move', 'general_invoice_id', copy=False, string='Invoices')
    line_ids = fields.One2many(
        comodel_name='invoice.not.exists.bkav.line',
        inverse_name='parent_id',
        string='Lines'
    )
    negative_line_ids = fields.One2many(
        comodel_name='invoice.not.exists.bkav.negative.line',
        inverse_name='parent_id',
        string='Negative Lines'
    )
    partner_id = fields.Many2one('res.partner', 'Customer')
    is_post_bkav = fields.Boolean('Is post BKAV', default=True)

    def general_invoice_not_exists_bkav(self):
        move_date = datetime.utcnow().date()
        # tổng hợp hóa đơn nhanh
        query = """
            SELECT DISTINCT so.id 
            FROM sale_order so
            LEFT JOIN sale_order_line sol on sol.order_id = so.id
            LEFT JOIN sale_order_line_invoice_rel solir on solir.order_line_id = sol.id
            LEFT JOIN account_move_line aml on solir.invoice_line_id = aml.id
            LEFT JOIN account_move am on am.id = aml.move_id
            WHERE so.source_record IS TRUE 
            AND am.invoice_date = %s
            AND am.state = 'posted'
            AND am.exists_bkav IS NOT TRUE
            AND so.state IN ('sale', 'done')
            AND so.nhanh_id != 0
        """
        self._cr.execute(query, (move_date,))
        result = self._cr.fetchall()
        nhanh_order_ids = self.env['sale.order'].sudo().browse([idd[0] for idd in result])
        if nhanh_order_ids:
            self.create_general_nhanh_order(nhanh_order_ids, move_date)

        # tổng hợp hóa đơn pos
        all_store = self.env['store'].sudo().search([])
        for store in all_store:
            self.create_general_pos_order(store, move_date)
        # invoices = self.env['account.move'].sudo().search([
        #     ('exists_bkav', '=', False),
        #     ('move_type', 'in', ['out_invoice', 'out_refund']),
        #     ('state', '=', 'posted'),
        #     # ('date', '=', move_date),
        # ])

    def create_general_pos_order(self, store, move_date):
        pass

    def create_general_nhanh_order(self, order_ids, move_date):
        out_line_vals, negative_line_vals, partner_id = self.get_line_nhanh_order(order_ids)
        self.env['invoice.not.exists.bkav'].sudo().create({
            'company_id': order_ids[0].company_id.id,
            'move_date': move_date,
            'invoice_ids': [(6, 0, order_ids.mapped('invoice_ids').ids)],
            'line_ids': out_line_vals,
            'negative_line_ids': negative_line_vals,
            'partner_id': partner_id
        })

    def get_line_nhanh_order(self, order_ids):
        out_line_vals = []
        return_line_vals = []
        product_price_unit = []
        quantity = []
        # tax = []
        cancel_invoice = []
        for line_id in order_ids.order_line:
            # đơn bán
            if not line_id.order_id.nhanh_origin_id:
                if (line_id.product_id.id, line_id.price_unit) not in product_price_unit:
                    product_price_unit.append((line_id.product_id.id, line_id.price_unit))
                    quantity.append(line_id.qty_invoiced)
                else:
                    index = product_price_unit.index((line_id.product_id.id, line_id.price_unit))
                    quantity[index] += line_id.qty_invoiced
                # if line_id.tax_ids and line_id.tax_ids[0].id not in tax:
                #     tax.append(line_id.tax_ids[0].id)
            # đơn trả
            else:
                origin_order_id = self.env['sale.order'].sudo().search(
                    [('nhanh_id', '=', line_id.order_id.nhanh_origin_id)], limit=1)
                # đơn gốc phát hành tại thời điểm (không có hóa đơn tổng)
                if origin_order_id and origin_order_id.invoice_ids and not origin_order_id.invoice_ids[
                    0].general_invoice_id:
                    origin_invoice_id = origin_order_id.invoice_ids[0]
                    invoice_id = line_id.order_id.invoice_ids[0]
                    # trả toàn phần và trong cùng ngày đơn trả => Hủy
                    if origin_invoice_id.amount_total == invoice_id.amount_total and origin_invoice_id.invoice_date == invoice_id.invoice_date and origin_invoice_id.id not in cancel_invoice:
                        cancel_invoice.append(origin_invoice_id.id)
                        return_line_vals.append((0, 0, {
                            'product_id': line_id.product_id.id,
                            'uom_id': line_id.product_uom.id,
                            'quantity': line_id.qty_invoiced,
                            'price_unit': line_id.price_unit,
                            'price_subtotal': line_id.price_subtotal,
                            'origin_move_id': origin_invoice_id.id,
                            'invoice_action': 'cancel'
                        }))
                    # trường hợp còn lại => Điều chỉnh
                    else:
                        return_line_vals.append((0, 0, {
                            'product_id': line_id.product_id.id,
                            'uom_id': line_id.product_uom.id,
                            'quantity': line_id.qty_invoiced,
                            'price_unit': line_id.price_unit,
                            'price_subtotal': line_id.price_subtotal,
                            'origin_move_id': origin_invoice_id.id,
                            'invoice_action': 'adjust',
                        }))
                # đơn gốc phát hành theo đơn tổng
                else:
                    if (line_id.product_id.id, line_id.price_unit) not in product_price_unit:
                        product_price_unit.append((line_id.product_id.id, line_id.price_unit))
                        quantity.append(-line_id.qty_invoiced)
                    else:
                        index = product_price_unit.index((line_id.product_id.id, line_id.price_unit))
                        quantity[index] += -line_id.qty_invoiced
                # if line_id.tax_ids and line_id.tax_ids[0].id not in tax:
                #     tax.append(line_id.tax_ids[0].id)
        # tổng hợp thành chi tiết đơn tổng
        for index, value in enumerate(product_price_unit):
            if int(quantity[index]) == 0:
                continue
            product_id = self.env['product.product'].browse(value[0])
            if int(quantity[index]) > 0:
                out_line_vals.append((0, 0, {
                    'product_id': product_id.id,
                    'uom_id': product_id.uom_id,
                    'quantity': quantity[index],
                    'price_unit': value[1],
                    'price_subtotal': value[1] * quantity[index],
                    # 'taxes_id': tax[index][0] if tax[index] else
                }))
            elif int(quantity[index]) < 0:
                origin_invoice_ids = order_ids.filtered(lambda o: o.nhanh_origin_id and product_id.id in o.order_line.product_id.ids).invoice_ids.general_invoice_id.sorted(lambda gi: gi.move_date)
                left_quantity = quantity[index]
                for general_invoice_id in origin_invoice_ids:
                    if left_quantity < 0:
                        break
                    left_quantity = quantity[index] - general_invoice_id.line_ids.filtered(lambda l:l.product_id.id == product_id.id and l.price_unit == value[1]).quantity
                    return_line_vals.append((0, 0, {
                        'product_id': product_id.id,
                        'uom_id': product_id.uom_id,
                        'quantity': quantity[index],
                        'price_unit': value[1],
                        'price_subtotal': value[1] * quantity[index],
                        'origin_general_move_id': general_invoice_id.id,
                        'invoice_action': 'adjust',
                    }))

        return out_line_vals, return_line_vals, order_ids[0].partner_id.id

    # def create_general_nhanh_invoice(self, order_ids, move_date):
    #     invoices = order_ids.mapped('invoice_ids')
    #     out_invoices = invoices.filtered(lambda x: x.move_type == 'out_invoice')
    #     refund_invoices = invoices.filtered(lambda x: x.move_type == 'out_refund')
    #     if out_invoices or refund_invoices:
    #         out_line_vals = []
    #         negative_line_vals = []
    #         line_checked = []
    #         product_checked = []
    #         # Sản phẩm có cả bán và trả trong ngày
    #         for line in out_invoices.invoice_line_ids:
    #             if line.id not in line_checked:
    #                 product_checked.append(line.product_id.id)
    #                 product_line_ids = out_invoices.invoice_line_ids.filtered(
    #                     lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
    #                 refund_line_ids = refund_invoices.invoice_line_ids.filtered(
    #                     lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
    #                 line_checked += (product_line_ids + refund_line_ids).ids
    #                 diff_qty = sum(product_line_ids.mapped('quantity')) - sum(refund_line_ids.mapped('quantity'))
    #                 price_subtotal = sum(product_line_ids.mapped('price_subtotal')) - sum(
    #                     refund_line_ids.mapped('price_subtotal'))
    #                 if diff_qty > 0:
    #                     out_line_vals.append((0, 0, {
    #                         'product_id': line.product_id.id,
    #                         'uom_id': line.product_id.uom_id.id,
    #                         'quantity': diff_qty,
    #                         'price_unit': line.price_unit,
    #                         'price_subtotal': price_subtotal,
    #                         'taxes_id': line.tax_ids.id
    #                     }))
    #                 if diff_qty < 0:
    #                     negative_line_vals.append((0, 0, {
    #                         'product_id': line.product_id.id,
    #                         'uom_id': line.product_id.uom_id.id,
    #                         'quantity': abs(diff_qty),
    #                         'price_unit': line.price_unit,
    #                         'price_subtotal': price_subtotal,
    #                         'taxes_id': line.tax_ids.id
    #                     }))
    #         # Sản phẩm chỉ có trả trong ngày
    #         for line in refund_invoices.invoice_line_ids.filtered(lambda x: x.product_id.id not in product_checked):
    #             if line.id not in line_checked:
    #                 refund_line_ids = refund_invoices.invoice_line_ids.filtered(
    #                     lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
    #                 line_checked += refund_line_ids.ids
    #                 negative_line_vals.append((0, 0, {
    #                     'product_id': line.product_id.id,
    #                     'uom_id': line.product_id.uom_id.id,
    #                     'quantity': sum(refund_line_ids.mapped('quantity')),
    #                     'price_unit': line.price_unit,
    #                     'price_subtotal': sum(refund_line_ids.mapped('price_subtotal')),
    #                     'taxes_id': line.tax_ids.id
    #                 }))
    #
    #         self.env['invoice.not.exists.bkav'].sudo().create({
    #             'company_id': self.env.company.id,
    #             'move_date': move_date,
    #             'invoice_ids': [(6, 0, invoices.ids)],
    #             'line_ids': out_line_vals,
    #             'negative_line_ids': negative_line_vals
    #         })


class InvoiceNotExistsBkavLine(models.Model):
    _name = 'invoice.not.exists.bkav.line'

    parent_id = fields.Many2one('invoice.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Float(string='Subtotal')
    taxes_id = fields.Many2one('account.tax', string='Tax %', domain=[('active', '=', True)])
    account_id = fields.Many2one('account.account', 'Account')


class InvoiceNotExistsBkavNegativeLine(models.Model):
    _name = 'invoice.not.exists.bkav.negative.line'

    parent_id = fields.Many2one('invoice.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Float(string='Subtotal')
    taxes_id = fields.Many2one('account.tax', string='Tax %', domain=[('active', '=', True)])
    origin_move_id = fields.Many2one('account.move', 'Origin move')
    origin_general_move_id = fields.Many2one('invoice.not.exists.bkav', 'Origin move')
    invoice_action = fields.Selection([
        ('cancel', 'Hủy'),
        ('adjust', 'Điều chỉnh')
    ], 'Loại phát hành')
    account_id = fields.Many2one('account.account', 'Account')
