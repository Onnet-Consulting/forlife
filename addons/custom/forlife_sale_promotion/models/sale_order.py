# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import re
from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError
# from bs4 import BeautifulSoup

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    promotion_ids = fields.One2many('sale.order.promotion', 'order_id', string="Promotion")
    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('sent', "Quotation Sent"),
            ('check_promotion', 'Check promotion'), #new item
            ('done_sale', "Done sale"),#new item
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')

    def get_oder_line_barcode(self, barcode):
        line_product = []
        for line in self.order_line:
            if line.product_id.barcode == barcode and not line.is_reward_line:
                line_product.append(line)
        return line_product

    def find_mn_index(self, note):
        if note:
            index_list = []
            for m in re.finditer('#mn', note.lower()):
                index_list.append(m.start())
            return index_list
        return []

    def get_customer_promotion_nhanh(self, rec, ln):
        if rec.source_record:
            res_id = f'product.category,{ln.product_id.categ_id.id}'
            ir_property = self.env['ir.property'].search([
                ('name', 'in', ['property_account_expense_categ_id','product_gift_account_id','discount_account_id','promotion_account_id']),
                ('res_id', '=', res_id),
                ('company_id', '=', rec.company_id.id)
            ])
            property_account_expense_categ_id = None
            property_promotion_account_id = None
            property_discount_account_id = None
            property_product_gift_account_id = None
            for ir in ir_property:
                if ir.name == 'property_account_expense_categ_id':
                    property_account_expense_categ_id = str(ir.value_reference).replace("account.account,", "")

                if ir.name == 'product_gift_account_id':
                    property_product_gift_account_id = str(ir.value_reference).replace("account.account,", "")

                if ir.name == 'discount_account_id':
                    property_discount_account_id = str(ir.value_reference).replace("account.account,", "")

                if ir.name == 'promotion_account_id':
                    property_promotion_account_id = str(ir.value_reference).replace("account.account,", "")

            gift_account_id = property_product_gift_account_id or property_account_expense_categ_id
            discount_account_id = property_discount_account_id or property_account_expense_categ_id
            promotion_account_id = property_promotion_account_id or property_account_expense_categ_id
        else:
            gift_account_id = ln.product_id.categ_id.product_gift_account_id.id or ln.product_id.categ_id.property_account_expense_categ_id.id
            discount_account_id = ln.product_id.categ_id.discount_account_id.id or ln.product_id.categ_id.property_account_expense_categ_id.id
            promotion_account_id = ln.product_id.categ_id.promotion_account_id.id or ln.product_id.categ_id.property_account_expense_categ_id.id

        return gift_account_id, discount_account_id, promotion_account_id

    def check_sale_promotion(self):
        for rec in self:
            if rec.order_line and rec.state in ["draft", 'sent', "check_promotion"]:
                rec.promotion_ids = [Command.clear()]
                if rec.x_sale_chanel == "online":
                    rec.write({"state": "check_promotion"})
                    text = re.compile('<.*?>')
                    note = rec.note and re.sub(text, '', rec.note.replace("\n", "").replace("\t", "").strip()).replace('&nbsp;', '')
                    # note = BeautifulSoup(rec.note, "lxml").text.replace('&nbsp;', '').strip()
                    # đơn hàng có tôn tại Lấy 3 ký tự đầu tiên của note thỏa với '#mn'

                    # Check mã đơn gốc và mã đơn đổi trả trong trường note
                    if rec.source_record and rec.x_is_change:
                        pattern_re = re.compile('#X\d+([\r\n]|.)*?#N\d+')
                        matched_str = pattern_re.search(rec.note)
                        if matched_str:
                            nhanh_origin_id = re.search(r'#X\d+', rec.note).group().split('#X', 1)[-1]
                            nhanh_return_id = re.search(r'#N\d+', rec.note).group().split('#N', 1)[-1]
                            orig_order = rec.search([('nhanh_id', '=', nhanh_origin_id)], limit=1)
                            return_order = rec.search([('nhanh_id', '=', nhanh_return_id)], limit=1)
                            if not orig_order or not return_order:
                                action = self.env['ir.actions.actions']._for_xml_id(
                                    'forlife_sale_promotion.action_check_promotion_wizard')
                                action['context'] = {
                                    'default_message': _("Not found the Sale Order with #X[%s] and #N[%s]!") % (nhanh_origin_id, nhanh_return_id)}
                                return action
                        else:
                            action = self.env['ir.actions.actions']._for_xml_id('forlife_sale_promotion.action_check_promotion_wizard')
                            action['context'] = {'default_message': _("Order note '#X[Nhanh Origin ID] #N[Nhanh Return ID]' invalid!")}
                            return action

                    has_vip = False
                    if len(self.find_mn_index(note)) >= 0:
                        for mn in self.find_mn_index(note):
                            barcode_str = note[mn + 3:].strip()
                            barcode = re.split(' |,', barcode_str)[0]

                            if len(rec.order_line) == 1 and rec.order_line[0].product_uom_qty == 1 and not rec.order_line[0].is_reward_line:
                                rec.order_line.write({'x_free_good': True, 'price_unit': 0, 'odoo_price_unit': 0, 'x_cart_discount_fixed_price': 0})

                            else:
                                line = self.get_oder_line_barcode(barcode)
                                if not line or len(line) == 0:
                                    rec.write({"state": "check_promotion"})
                                    action = self.env['ir.actions.actions']._for_xml_id(
                                        'forlife_sale_promotion.action_check_promotion_wizard')
                                    action['context'] = {'default_message': _("Order note '#MN' invalid!")}
                                    return action
                                elif len(line) >= 1:
                                    if line[0].product_uom_qty == 1:
                                        line[0].write({'x_free_good': True, 'price_unit': 0, 'odoo_price_unit': 0, 'x_cart_discount_fixed_price': 0})
                                    elif line[0].product_uom_qty > 1:
                                        line[0].write({
                                            'product_uom_qty': line[0].product_uom_qty - 1,
                                            'price_unit': line[0].price_unit
                                        })
                                        line[0].copy(
                                            {'x_free_good': True, 'order_id': line[0].order_id.id,
                                             'product_uom_qty': 1, 'price_unit': 0, 'odoo_price_unit': 0,
                                             'x_cart_discount_fixed_price': 0}
                                        )
                    if note and note.lower().find('#vip') >= 0:
                        vip_text = note[note.lower().find('#vip') + 4:]
                        vip_number_text = vip_text.strip()[:2]
                        vip_number = vip_number_text and str(vip_number_text[0]).isnumeric() and re.sub("[^0-9]", "", vip_number_text)
                        if vip_number and str(vip_number).isnumeric() and int(vip_number) != 0:
                            for ln in rec.order_line:
                                warehouse_code = ln.x_location_id.warehouse_id.code
                                analytic_account_id = warehouse_code and self.env['account.analytic.account'].search(
                                    [('code', 'like', '%' + warehouse_code)], limit=1)
                                ghn_price_unit = ln.price_unit
                                price_percent = int(vip_number) / 100 * ghn_price_unit * ln.product_uom_qty
                                # gift_account_id = ln.product_id.categ_id.product_gift_account_id or ln.product_id.categ_id.property_account_expense_categ_id
                                # discount_account_id = ln.product_id.categ_id.discount_account_id or ln.product_id.categ_id.property_account_expense_categ_id
                                # promotion_account_id = ln.product_id.categ_id.promotion_account_id or ln.product_id.categ_id.property_account_expense_categ_id
                                gift_account_id, discount_account_id, promotion_account_id = self.get_customer_promotion_nhanh(rec, ln)
                                has_vip = True
                                # Ưu tiên 3
                                if not ln.x_free_good and not ln.is_reward_line and price_percent > 0:
                                    rec.promotion_ids = [(0, 0, {
                                        'product_id': ln.product_id.id,
                                        'value': price_percent,
                                        'promotion_type': 'vip_amount',
                                        'account_id': promotion_account_id,
                                        'analytic_account_id': analytic_account_id and analytic_account_id.id,
                                        'product_uom_qty': ln.product_uom_qty,
                                        'description': "Chiết khấu theo chính sách vip"
                                    })]
                                    ln.x_account_analytic_id = analytic_account_id and analytic_account_id.id
                                # Ưu tiên 4

                                if ln.x_cart_discount_fixed_price - price_percent > 0:
                                    rec.promotion_ids = [(0, 0, {
                                        'product_id': ln.product_id.id,
                                        'value': ln.x_cart_discount_fixed_price - price_percent,
                                        'account_id': discount_account_id,
                                        'analytic_account_id': analytic_account_id and analytic_account_id.id,
                                        'product_uom_qty': ln.product_uom_qty,
                                        'promotion_type': 'vip_amount_remain',
                                        'description': "Chiết khấu giảm giá trực tiếp"
                                    })]
                                    ln.x_account_analytic_id = analytic_account_id and analytic_account_id.id
                        else:
                            self.env.cr.rollback()
                            rec.write({"state": "check_promotion"})
                            action = self.env['ir.actions.actions']._for_xml_id('forlife_sale_promotion.action_check_promotion_wizard')
                            action['context'] = {'default_message': _("Order note '#VIP' invalid!")}
                            return action
                            # raise ValidationError(_("Order note '#VIP' invalid!"))
                    for ln in rec.order_line:
                        warehouse_code = ln.x_location_id.warehouse_id.code
                        analytic_account_id = warehouse_code and self.env['account.analytic.account'].search([('code', 'like', '%' + warehouse_code)], limit=1)
                        odoo_price_unit = ln.odoo_price_unit
                        diff_price_unit = odoo_price_unit - ln.price_unit  # thay 0 thanhf don gia Nhanh khi co truong
                        diff_price = diff_price_unit * ln.product_uom_qty
                        # gift_account_id = ln.product_id.categ_id.product_gift_account_id or ln.product_id.categ_id.property_account_expense_categ_id
                        # discount_account_id = ln.product_id.categ_id.discount_account_id or ln.product_id.categ_id.property_account_expense_categ_id

                        # promotion_account_id = ln.product_id.categ_id.promotion_account_id or ln.product_id.categ_id.property_account_expense_categ_id
                        gift_account_id, discount_account_id, promotion_account_id = self.get_customer_promotion_nhanh(rec, ln)
                        # Ưu tiên 4
                        if not has_vip and ln.x_cart_discount_fixed_price > 0 and not ln.x_free_good and not ln.is_reward_line:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': ln.x_cart_discount_fixed_price,
                                'promotion_type': 'discount',
                                'account_id': discount_account_id,
                                'analytic_account_id': analytic_account_id and analytic_account_id.id,
                                'description': "Chiết khấu giảm giá trực tiếp"
                            })]
                            ln.x_account_analytic_id = analytic_account_id and analytic_account_id.id
                        # Ưu tiên 2
                        if diff_price > 0 and not ln.x_free_good and not ln.is_reward_line:
                            rec.promotion_ids = [(0, 0, {
                                'product_id': ln.product_id.id,
                                'value': diff_price,
                                'promotion_type': 'diff_price',
                                'account_id': promotion_account_id,
                                'analytic_account_id': analytic_account_id and analytic_account_id.id,
                                'description': "Chiết khấu khuyến mãi theo CT giá"
                            })]
                            ln.x_account_analytic_id = analytic_account_id and analytic_account_id.id

                    # Nhanh shipping fee
                    if rec.nhanh_shipping_fee and rec.nhanh_shipping_fee > 0:
                        product_id = self.env.ref('forlife_sale_promotion.product_product_promotion_shipping_fee')
                        try:
                            if rec.source_record:
                                res_id = f'product.template,{product_id.product_tmpl_id.id}'
                                ir_property = self.env['ir.property'].search([
                                    ('name', '=', 'property_account_income_id'),
                                    ('res_id', '=', res_id),
                                    ('company_id', '=', rec.company_id.id)
                                ], limit=1)
                                if ir_property:
                                    account_id = str(ir_property.value_reference).replace("account.account,", "")
                                else:
                                    account_id = None
                            else:
                                account_id = product_id.property_account_income_id.id
                        except Exception as e:
                            account_id = None
                        
                        if not account_id:
                            raise UserError("Chưa cấu hình Tài khoản doanh thu cho sản phầm %s!" % product_id.name)
                            
                        rec.promotion_ids = [(0, 0, {
                            'product_id': product_id and product_id.id,
                            'value': - rec.nhanh_shipping_fee,
                            'promotion_type': 'nhanh_shipping_fee',
                            'account_id': account_id,
                            # 'analytic_account_id': analytic_account_id and analytic_account_id.id,
                            'description': "Phí vận chuyển"
                        })]

                    # Customer shipping fee
                    if rec.nhanh_customer_shipping_fee and rec.nhanh_customer_shipping_fee > 0:
                        product_id = self.env.ref('forlife_sale_promotion.product_product_promotion_customer_shipping_fee')
                        try:
                            if rec.source_record:
                                res_id = f'product.template,{product_id.product_tmpl_id.id}'
                                ir_property = self.env['ir.property'].search([
                                    ('name', '=', 'property_account_expense_id'),
                                    ('res_id', '=', res_id),
                                    ('company_id', '=', rec.company_id.id)
                                ], limit=1)
                                if ir_property:
                                    account_id = str(ir_property.value_reference).replace("account.account,", "")
                                else:
                                    account_id = None
                            else:
                                account_id = product_id.property_account_expense_id
                        except Exception as e:
                            account_id = None


                        if not account_id:
                            raise UserError("Chưa cấu hình Tài khoản chi phí cho sản phầm %s!" % product_id.name)

                        rec.promotion_ids = [(0, 0, {
                            'product_id': product_id and product_id.id,
                            'value': rec.nhanh_customer_shipping_fee,
                            'promotion_type': 'customer_shipping_fee',
                            'account_id': account_id,
                            # 'analytic_account_id': analytic_account_id and analytic_account_id.id,
                            'description': "Phí ship báo khách hàng"
                        })]
                # đơn bán buôn
                elif rec.x_sale_chanel == "wholesale":
                    for line in rec.order_line:
                        # check khuyên mãi để tạo promotion
                        if line.reward_id.reward_type == "discount":
                            product_domain = line.reward_id._get_discount_product_domain()
                            for line_promotion in rec.order_line:
                                warehouse_code = line_promotion.x_location_id.warehouse_id.code
                                analytic_account_id = warehouse_code and self.env['account.analytic.account'].search([('code', 'like', '%' + warehouse_code)], limit=1)

                                if line_promotion.product_id.filtered_domain(
                                        product_domain) and not line_promotion.x_free_good and not line_promotion.is_reward_line:
                                    discount_amount = line_promotion.price_unit * \
                                                      line_promotion.product_uom_qty * \
                                                      (line.reward_id.discount or 100) / 100
                                    discount_account_id = line_promotion.product_id.categ_id.discount_account_id or line_promotion.product_id.categ_id.property_account_expense_categ_id
                                    rec.promotion_ids = [(0, 0, {
                                        'product_id': line_promotion.product_id.id,
                                        'value': discount_amount,
                                        'promotion_type': 'reward',
                                        'account_id': discount_account_id and discount_account_id.id,
                                        'analytic_account_id': analytic_account_id and analytic_account_id.id,
                                        'description': "Chiết khấu khuyến mãi"
                                    })]
                                    line_promotion.x_account_analytic_id = discount_account_id and discount_account_id.id
                            line.write({'state': 'draft'})
                            line.unlink()
                rec.write({"state": "done_sale"})

    def action_open_reward_wizard(self):
        for rec in self:
            res = super(SaleOrder, self).action_open_reward_wizard()
            for line in rec.order_line:
                if line.is_reward_line:
                    if line.reward_id.reward_type == "product":
                        line.write({'x_free_good': True, 'price_unit': 0, 'odoo_price_unit': 0, 'x_cart_discount_fixed_price': 0})
            return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    prm_price_discount = fields.Float(string="Price discount")
    # prm_price_total_discount = fields.Float(string="Price total discount", compute="_compute_amount_discount")
    # ghn_price_unit_discount = fields.Float(string="Price unit discount (GHN)")
    # product_gift = fields.Boolean(string="Gift")

    # @api.depends("price_subtotal", "price_unit", "product_uom_qty", "order_id.x_sale_chanel", "x_cart_discount_fixed_price")
    # def _compute_amount_discount(self):
    #     for rec in self:
    #         # rec.prm_price_discount = False
    #         rec.prm_price_total_discount = False
    #         if rec.order_id.x_sale_chanel == "online":
    #             # rec.prm_price_discount = rec.discount_price_unit * rec.product_uom_qty
    #             rec.prm_price_total_discount = rec.price_subtotal - rec.x_cart_discount_fixed_price
