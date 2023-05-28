# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import re
from odoo import fields, Command
from odoo.exceptions import UserError
# from bs4 import BeautifulSoup

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    promotion_ids = fields.One2many('sale.order.promotion', 'order_id', string="Promotion")
    state = fields.Selection(
        selection_add=[('check_promotion', 'Check promotion'), ('done', "Done")]
    )

    def get_oder_line_barcode(self, barcode):
        for line in self.order_line:
            if line.product_id.barcode == barcode:
                return line
        return False

    def check_sale_promotion(self):
        for rec in self:
            if rec.order_line and rec.state in ["sale", "check_promotion"] and rec.x_sale_chanel == "online":
                rec.write({"state": "check_promotion"})
                text = re.compile('<.*?>')
                note = rec.note and re.sub(text, '', rec.note.replace("\n", "").replace("\t", "").strip()).replace('&nbsp;', '')
                # note = BeautifulSoup(rec.note, "lxml").text.replace('&nbsp;', '').strip()
                # đơn hàng có tôn tại Lấy 3 ký tự đầu tiên của note thỏa với '#mn'
                if rec.order_line and note and note[0:3].lower() == "#mn":
                    if len(rec.order_line) == 1:
                        if rec.order_line[0].product_uom_qty == 1:
                            rec.order_line.write({'x_free_good': True, 'price_unit': 0})
                        elif rec.order_line[0].product_uom_qty > 1:
                            for i in range(int(rec.order_line[0].product_uom_qty)):
                                new_line = rec.order_line[0].copy({'order_id': rec.order_line[0].order_id.id, 'product_uom_qty': 1})
                                if i == 0:
                                    new_line.write({'x_free_good': True, 'price_unit': 0})
                            rec.order_line[0].unlink()
                    else:
                        barcode = note[3:].strip()
                        line = self.get_oder_line_barcode(barcode)
                        if not line or len(line) == 0:
                            rec.write({"state": "check_promotion"})
                            raise UserError("Order note is invalid!")
                        elif line.product_uom_qty == 1:
                            line.write({'x_free_good': True, 'price_unit': 0})
                        elif line.product_uom_qty > 1:
                            for i in range(int(line.product_uom_qty)):
                                new_line = line.copy({'order_id': line.order_id.id, 'product_uom_qty': 1})
                                if i == 0:
                                    new_line.write({'x_free_good': True, 'price_unit': 0})
                            line.unlink()
                elif note and note[0:4].lower() == "#vip":
                    rec.promotion_ids = [Command.clear()]
                    # percent_arr = note[4:].replace('&nbsp;', '').lstrip().split(' ')
                    # percent = len(percent_arr) > 0 and int(percent_arr[0])
                    percent = re.sub("[^0-9]", "", note[4:6])
                    if percent and str(percent).isnumeric():
                        for ln in rec.order_line:
                            ghn_price_unit = ln.price_unit
                            price_percent = int(percent) / 100 * ghn_price_unit * ln.product_uom_qty
                            if not ln.x_free_good:
                                rec.promotion_ids = [(0, 0, {
                                    'product_id': ln.product_id.id,
                                    'value': price_percent,
                                    'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                    'description': "Giảm giá từ CT làm giá"
                                })]
                    else:
                        return

                else:
                    rec.promotion_ids = [Command.clear()]
                    for ln in rec.order_line:
                        odoo_price_unit = ln.odoo_price_unit
                        diff_price_unit = odoo_price_unit - ln.price_unit  # thay 0 thanhf don gia Nhanh khi co truong
                        diff_price = diff_price_unit * ln.product_uom_qty
                        if ln.x_cart_discount_fixed_price > 0:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': ln.x_cart_discount_fixed_price,
                                'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                'description': "Chiết khấu khuyến mãi"
                            })]
                        if diff_price > 0:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': diff_price_unit,
                                'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                'description': "Chiết khấu khuyến mãi"
                            })]
                        # elif ln.prm_price_discount > 0:
                        #     rec.promotion_ids = [(0, 0, {
                        #         'product_id': ln.product_id.id,
                        #         'value': ln.prm_price_discount,
                        #         'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                        #         'description': "Giảm giá từ CT làm giá"
                        #     })]
                rec.write({"state": "done"})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    prm_price_discount = fields.Float(string="Price discount")
    prm_price_total_discount = fields.Float(string="Price total discount", compute="_compute_amount_discount")
    # ghn_price_unit_discount = fields.Float(string="Price unit discount (GHN)")
    # product_gift = fields.Boolean(string="Gift")

    @api.depends("discount_price_unit", "price_unit", "product_uom_qty", "order_id.x_sale_chanel", "prm_price_discount")
    def _compute_amount_discount(self):
        for rec in self:
            # rec.prm_price_discount = False
            rec.prm_price_total_discount = False
            if rec.order_id.x_sale_chanel == "online":
                # rec.prm_price_discount = rec.discount_price_unit * rec.product_uom_qty
                rec.prm_price_total_discount = rec.price_subtotal - rec.prm_price_discount
