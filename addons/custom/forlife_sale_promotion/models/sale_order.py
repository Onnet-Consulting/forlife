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
        selection_add=[('check_promotion', 'Check promotion'), ('done_sale', "Done sale")]
    )

    def get_oder_line_barcode(self, barcode):
        for line in self.order_line:
            if line.product_id.barcode == barcode:
                return line
        return False

    def check_sale_promotion(self):
        for rec in self:
            if rec.order_line and rec.state in ["sale", "check_promotion"]:
                rec.promotion_ids = [Command.clear()]
                if rec.x_sale_chanel == "online":
                    rec.write({"state": "check_promotion"})
                    text = re.compile('<.*?>')
                    note = rec.note and re.sub(text, '', rec.note.replace("\n", "").replace("\t", "").strip()).replace('&nbsp;', '')
                    # note = BeautifulSoup(rec.note, "lxml").text.replace('&nbsp;', '').strip()
                    # đơn hàng có tôn tại Lấy 3 ký tự đầu tiên của note thỏa với '#mn'

                    line_gift_mn = []
                    if note and note.lower().find('#mn') >= 0:
                        barcode = note[note.lower().find('#mn') + 3:].strip().split(' ')[0]
                        if len(rec.order_line) == 1:
                            if rec.order_line[0].product_uom_qty == 1:
                                rec.order_line.write({'x_free_good': True, 'price_unit': 0, 'x_cart_discount_fixed_price': 0})
                            elif rec.order_line[0].product_uom_qty > 1:
                                for i in range(int(rec.order_line[0].product_uom_qty)):
                                    new_line = rec.order_line[0].copy({'order_id': rec.order_line[0].order_id.id, 'product_uom_qty': 1})
                                    if i == 0:
                                        new_line.write({'x_free_good': True, 'price_unit': 0, 'x_cart_discount_fixed_price': 0})
                                rec.order_line[0].unlink()
                        else:
                            line = self.get_oder_line_barcode(barcode)
                            if not line or len(line) == 0:
                                rec.write({"state": "check_promotion"})
                                raise UserError(_("Order note invalid!"))
                            elif line.product_uom_qty == 1:
                                line.write({'x_free_good': True, 'price_unit': 0})
                            elif line.product_uom_qty > 1:
                                for i in range(int(line.product_uom_qty)):
                                    new_line = line.copy({'order_id': line.order_id.id, 'product_uom_qty': 1})
                                    if i == 0:
                                        new_line.write({'x_free_good': True, 'price_unit': 0, 'x_cart_discount_fixed_price': 0})
                                line.unlink()
                    if note and note.lower().find('#vip') >= 0:
                        vip_text = note[note.lower().find('#vip') + 4:]
                        vip_number_text = vip_text.strip()[:2]
                        vip_number = re.sub("[^0-9]", "", vip_number_text)
                        if vip_number and str(vip_number).isnumeric():
                            for ln in rec.order_line:
                                warehouse_code = ln.x_location_id.warehouse_id.whs_code
                                analytic_account_id = warehouse_code and self.env['account.analytic.account'].search(
                                    [('code', 'like', '%' + warehouse_code + '%')], limit=1)
                                ghn_price_unit = ln.price_unit
                                price_percent = int(vip_number) / 100 * ghn_price_unit * ln.product_uom_qty
                                if not ln.x_free_good:
                                    rec.promotion_ids = [(0, 0, {
                                        'product_id': ln.product_id.id,
                                        'value': price_percent,
                                        'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                        'analytic_account_id': analytic_account_id.id,
                                        'description': "Giảm giá từ CT làm giá"
                                    })]

                    for ln in rec.order_line:
                        warehouse_code = ln.x_location_id.warehouse_id.whs_code
                        analytic_account_id = warehouse_code and self.env['account.analytic.account'].search([('code', 'like', '%'+warehouse_code+'%')], limit=1)
                        odoo_price_unit = ln.odoo_price_unit
                        diff_price_unit = odoo_price_unit - ln.price_unit  # thay 0 thanhf don gia Nhanh khi co truong
                        diff_price = diff_price_unit * ln.product_uom_qty
                        if ln.x_cart_discount_fixed_price > 0 and not ln.x_free_good:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': ln.x_cart_discount_fixed_price,
                                'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                'analytic_account_id': analytic_account_id.id,
                                'description': "Chiết khấu khuyến mãi"
                            })]
                        if diff_price > 0 and not ln.x_free_good:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': diff_price_unit,
                                'account_id': ln.product_id.categ_id and ln.product_id.categ_id.discount_account_id.id,
                                'analytic_account_id': analytic_account_id.id,
                                'description': "Chiết khấu khuyến mãi"
                            })]

                elif rec.x_sale_chanel == "wholesale":
                    for line in rec.order_line:
                        if line.reward_id.reward_type == "discount":
                            product_domain = line.reward_id._get_discount_product_domain()
                            for line_promotion in rec.order_line:
                                warehouse_code = line_promotion.x_location_id.warehouse_id.whs_code
                                analytic_account_id = warehouse_code and self.env['account.analytic.account'].search(
                                    [('code', 'like', '%' + warehouse_code + '%')], limit=1)

                                if line_promotion.product_id.filtered_domain(
                                        product_domain) and not line_promotion.x_free_good and not line_promotion.is_reward_line:
                                    discount_amount = line_promotion.price_unit * (
                                            1 - (line_promotion.discount or 0.0) / 100.0) * (
                                                              line.reward_id.discount / 100)
                                    rec.promotion_ids = [(0, 0, {
                                        'product_id': line_promotion.product_id.id,
                                        'value': discount_amount,
                                        'account_id': line_promotion.product_id.categ_id and line_promotion.product_id.categ_id.discount_account_id.id,
                                        'analytic_account_id': analytic_account_id.id,
                                        'description': "Chiết khấu khuyến mãi"
                                    })]
                            line.write({'state': 'draft'})
                            line.unlink()
                rec.write({"state": "done_sale"})

    def action_open_reward_wizard(self):
        for rec in self:
            res = super(SaleOrder, self).action_open_reward_wizard()
            for line in rec.order_line:
                if line.is_reward_line:
                    if line.reward_id.reward_type == "product":
                        line.write({'x_free_good': True, 'price_unit': 0, 'x_cart_discount_fixed_price': 0})
            return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    prm_price_discount = fields.Float(string="Price discount")
    prm_price_total_discount = fields.Float(string="Price total discount", compute="_compute_amount_discount")
    # ghn_price_unit_discount = fields.Float(string="Price unit discount (GHN)")
    # product_gift = fields.Boolean(string="Gift")

    @api.depends("price_subtotal", "price_unit", "product_uom_qty", "order_id.x_sale_chanel", "x_cart_discount_fixed_price")
    def _compute_amount_discount(self):
        for rec in self:
            # rec.prm_price_discount = False
            rec.prm_price_total_discount = False
            if rec.order_id.x_sale_chanel == "online":
                # rec.prm_price_discount = rec.discount_price_unit * rec.product_uom_qty
                rec.prm_price_total_discount = rec.price_subtotal - rec.x_cart_discount_fixed_price
