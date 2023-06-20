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
    invoice_ids = fields.Many2many(comodel_name='account.move', copy=False, string='Invoices')
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

    def general_invoice_not_exists_bkav(self):
        move_date = datetime.utcnow().date()
        invoices = self.env['account.move'].sudo().search([
            ('exists_bkav', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            # ('date', '=', move_date),
        ])

        out_invoices = invoices.filtered(lambda x: x.move_type == 'out_invoice')
        refund_invoices = invoices.filtered(lambda x: x.move_type == 'out_refund')
        if out_invoices or refund_invoices:
            out_line_vals = []
            negative_line_vals = []
            line_checked = []
            product_checked = []
            # Sản phẩm có cả bán và trả trong ngày
            for line in out_invoices.invoice_line_ids:
                if line.id not in line_checked:
                    product_checked.append(line.product_id.id)
                    product_line_ids = out_invoices.invoice_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    refund_line_ids = refund_invoices.invoice_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    line_checked += (product_line_ids + refund_line_ids).ids
                    diff_qty = sum(product_line_ids.mapped('quantity')) - sum(refund_line_ids.mapped('quantity'))
                    price_subtotal = sum(product_line_ids.mapped('price_subtotal')) - sum(
                        refund_line_ids.mapped('price_subtotal'))
                    if diff_qty > 0:
                        out_line_vals.append((0, 0, {
                            'product_id': line.product_id.id,
                            'uom_id': line.product_id.uom_id.id,
                            'quantity': diff_qty,
                            'price_unit': line.price_unit,
                            'price_subtotal': price_subtotal,
                            # 'taxes_id': line.taxes_id.id,
                        }))
                    if diff_qty < 0:
                        negative_line_vals.append((0, 0, {
                            'product_id': line.product_id.id,
                            'uom_id': line.product_id.uom_id.id,
                            'quantity': abs(diff_qty),
                            'price_unit': line.price_unit,
                            'price_subtotal': price_subtotal,
                            # 'taxes_id': line.taxes_id.id
                        }))
            # Sản phẩm chỉ có trả trong ngày
            for line in refund_invoices.invoice_line_ids.filtered(lambda x: x.product_id.id not in product_checked):
                if line.id not in line_checked:
                    refund_line_ids = refund_invoices.invoice_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id and r.price_unit == line.price_unit)
                    line_checked += (refund_line_ids).ids
                    negative_line_vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'uom_id': line.product_id.uom_id.id,
                        'quantity': sum(refund_line_ids.mapped('quantity')),
                        'price_unit': line.price_unit,
                        'price_subtotal': sum(refund_line_ids.mapped('price_subtotal')),
                        # 'taxes_id': line.taxes_id.id
                    }))

            general_invoice_id = self.env['invoice.not.exists.bkav'].sudo().create({
                'company_id': self.env.company.id,
                'move_date': move_date,
                'invoice_ids': [(6, 0, invoices.ids)],
                'line_ids': out_line_vals,
                'negative_line_ids': negative_line_vals
            })


class InvoiceNotExistsBkavLine(models.Model):
    _name = 'invoice.not.exists.bkav.line'

    parent_id = fields.Many2one('invoice.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Float(string='Subtotal')
    taxes_id = fields.Many2one('account.tax', string='Tax %', domain=[('active', '=', True)])


class InvoiceNotExistsBkavNegativeLine(models.Model):
    _name = 'invoice.not.exists.bkav.negative.line'

    parent_id = fields.Many2one('invoice.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    price_subtotal = fields.Float(string='Subtotal')
    taxes_id = fields.Many2one('account.tax', string='Tax %', domain=[('active', '=', True)])
