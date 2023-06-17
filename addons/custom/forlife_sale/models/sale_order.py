# -*- coding: utf-8 -*-


from odoo import api, fields,models,_
from odoo.osv import expression
from datetime import date, datetime
from odoo.exceptions import UserError
import pyodbc
from datetime import date, datetime
from odoo.tests import Form

list_state = {
    'draft': 'Dự thảo',
    'waiting': 'Đang chờ hoạt động khác',
    'confirmed': 'Chờ',
    'assigned': 'Sẵn sàng',
    'done': 'Hoàn thành',
    'cancel': 'Đã hủy'
}
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_sale_type = fields.Selection(
        [('product', 'Hàng hóa'),
         ('service', 'Dịch vụ'),
         ('asset', 'Tài sản')],
        string='Loại bán hàng', default='product')
    x_sale_chanel = fields.Selection(
        [('pos', 'Đơn bán hàng POS'),
         ('wholesale', 'Đơn bán buôn'),
         ('intercompany', 'Đơn bán hàng liên công ty'),
         ('online', 'Đơn bán hàng online')],
        string='Kênh bán', default='wholesale')
    x_account_analytic_ids = fields.Many2many('account.analytic.account', string='Trung tâm chi phí')
    x_occasion_code_ids = fields.Many2many('occasion.code', string='Mã vụ việc')
    x_punish = fields.Boolean(string='Đơn phạt', copy=False)
    # x_shipping_punish = fields.Boolean(string='Đơn phạt đơn vị vận chuyển', copy=False)
    x_is_exchange = fields.Boolean(string='Đơn đổi', copy=False)
    x_manufacture_order_code_id = fields.Many2one('forlife.production', string='Mã lệnh sản xuất')
    x_is_return = fields.Boolean('Đơn trả hàng', copy=False)
    x_origin = fields.Many2one('sale.order', 'Tài liệu gốc', copy=False)
    x_order_punish_count = fields.Integer('Số đơn phạt', compute='_compute_order_punish_count')
    x_order_return_count = fields.Integer('Số đơn trả lại', compute='_compute_order_return_count')
    x_is_exchange_count = fields.Integer('Số đơn đổi', compute='_compute_exchange_count')
    x_domain_pricelist = fields.Many2many('product.pricelist', compute='_compute_domain_pricelist', store=False)

    @api.onchange('x_punish', 'partner_id')
    def _compute_domain_pricelist(self):
        for r in self:
            if not r.partner_id:
                r.x_domain_pricelist = None
                continue
            if not r.x_punish:
                pricelist = self.env['product.pricelist'].search(
                    ['|', ('x_partner_id', '=', r.partner_id.id), ('x_partner_id', '=', False), '|',
                     ('company_id', '=', False), ('company_id', '=', r.company_id.id)]).ids
            else:
                pricelist = r.get_pricelist()
            r.x_domain_pricelist = [(6, 0, pricelist)]

    def get_pricelist(self):
        sql = f"""            
                select pp.id from product_pricelist pp 
                left join product_pricelist_item ppi on ppi.pricelist_id = pp.id
                where 1=1
                and pp.x_punish is True
                and pp.x_partner_id = {self.partner_id.id}
                and '{str(self.date_order)}' between ppi.date_start and ppi.date_end
                and (pp.company_id = {self.company_id.id} or pp.company_id is Null)
                order by pp.id desc
            """
        self._cr.execute(sql)
        result = self._cr.fetchall()
        if result:
            return [rec[0] for rec in result]
        else:
            return []
    # @api.onchange('x_process_punish')
    # def onchange_x_process_punish(self):
    #     for line in self.order_line:
    #         line._compute_price_unit()

    def copy(self, default=None):
        default = dict(default or {})
        res = super().copy(default)
        for line in res.order_line:
            line._compute_price_unit()
        return res

    def confirm_return_so(self):
        so_id = self.x_origin
        picking_ids = so_id.picking_ids.filtered(lambda p: p.state == 'done')
        if picking_ids and len(picking_ids) == 1:
            stock_return_picking_form = Form(
                self.env['stock.return.picking'].with_context(active_ids=picking_ids.ids,
                                                              active_id=picking_ids[0].id,
                                                              active_model='stock.picking'))
            ctx = {
                'so_return': self.id,
                'x_return': True,
                'picking_id': picking_ids.id
            }
            return_wiz = stock_return_picking_form.save()
            return {
                'name': _('Trả hàng phiếu %s' % (picking_ids[0].name)),
                'view_mode': 'form',
                'res_model': 'stock.return.picking',
                'type': 'ir.actions.act_window',
                'views': [(False, 'form')],
                'res_id': return_wiz.id,
                'context': ctx,
                'target': 'new'
            }

        line = []
        for picking in picking_ids:
            line.append((0, 0, {'picking_name': picking.name,
                                'state': list_state.get(picking.state),
                                'picking_id': picking.id,
                                }))

        comfirm = self.env['confirm.return.so'].create({
            'origin': self.id,
            'line_ids': line})
        return {
            'view_mode': 'form',
            'res_model': 'confirm.return.so',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'res_id': comfirm.id,
            'target': 'current'
        }
    def _compute_order_punish_count(self):
        for r in self:
            count = self.env['sale.order'].search(
                [('x_origin', '=', r.id), ('x_punish', '=', True)])
            r.x_order_punish_count = len(count)

    def _compute_exchange_count(self):
        for r in self:
            count = self.env['sale.order'].search(
                [('x_origin', '=', r.id), ('x_is_exchange', '=', True)])
            r.x_is_exchange_count = len(count)

    def _compute_order_return_count(self):
        for r in self:
            count = self.env['sale.order'].search(
                [('x_origin', '=', r.id), ('x_is_return', '=', True)])
            r.x_order_return_count = len(count)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.check_debtBalance()
        return res
    def write(self, vals_list):
        res = super().write(vals_list)
        self.check_debtBalance()
        return res

    def check_debtBalance(self):
        if not self.partner_id.use_partner_credit_limit:
            return True
        debtBalance_bravo = self.get_DebtBalance()
        sale_so_ids = self.env['sale.order'].search([('partner_id', '=', self.partner_id.id), ('state', '=', 'sale')])
        debtBalance_forlife = sum(so.amount_untaxed for so in sale_so_ids)
        if debtBalance_bravo + debtBalance_forlife + self.amount_untaxed > self.partner_id.credit_limit:
            raise UserError(_('Đơn hàng vượt quá hạn mức tín dụng của khách hàng'))

    def action_view_so_punish(self):
        count = self.env['sale.order'].search(
            [('x_origin', '=', self.id), ('x_punish', '=', True)])
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        if len(count) > 1:
            action['domain'] = [('id', 'in', count.ids)]
        elif len(count) == 1:
            form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = count.id
        return action
    def action_view_so_return(self):
        count = self.env['sale.order'].search(
            [('x_origin', '=', self.id), ('x_is_return', '=', True)])
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        if len(count) > 1:
            action['domain'] = [('id', 'in', count.ids)]
        elif len(count) == 1:
            form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = count.id
        return action

    def action_view_so_exchange(self):
        count = self.env['sale.order'].search(
            [('x_origin', '=', self.id), ('x_is_exchange', '=', True)])
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        if len(count) > 1:
            action['domain'] = [('id', 'in', count.ids)]
        elif len(count) == 1:
            form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = count.id
        return action
    def get_rule_domain(self):
        domain = ['&', ('location_dest_id', '=', self.partner_shipping_id.property_stock_customer.id),
                  ('action', '!=', 'push')]
        if self.env.su and self.company_id:
            domain_company = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.company_id.ids)]
            domain = expression.AND([domain, domain_company])
        return domain

    def get_rule(self):
        if self.warehouse_id:
            domain = expression.AND(
                [['|', ('warehouse_id', '=', self.warehouse_id.id), ('warehouse_id', '=', False)],
                 self.get_rule_domain()])
            warehouse_routes = self.warehouse_id.route_ids
            if warehouse_routes:
                res = self.env['stock.rule'].search(
                    expression.AND([[('route_id', 'in', warehouse_routes.ids)], domain]),
                    order='route_sequence, sequence', limit=1)
            return res

    def action_create_picking(self):
        rule = self.get_rule()
        master = {
            'origin': self.name,
            'company_id': self.company_id.id,
            'move_type': self.picking_policy,
            'partner_id': self.partner_id.id,
            'picking_type_id': rule.picking_type_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.partner_shipping_id.property_stock_customer.id,
            'sale_id': self.id,
            'state': 'confirmed'
        }
        list_location = []
        stock_move_ids = {}
        line_x_scheduled_date = []
        for line in self.order_line:
            date = datetime.combine(line.x_scheduled_date,
                                    datetime.min.time()) if line.x_scheduled_date else datetime.now()
            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            detail_data = {
                'name': line.name,
                'company_id': line.company_id.id,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': line.product_uom_qty,
                'partner_id': line.order_id.partner_id.id,
                'location_id': line.x_location_id.id,
                'location_dest_id': line.order_id.partner_shipping_id.property_stock_customer.id,
                'rule_id': rule.id,
                'procure_method': 'make_to_stock',
                'origin': line.order_id.name,
                'picking_type_id': rule.picking_type_id.id,
                'date_deadline': datetime.now(),
                'description_picking': line.name,
                'sale_line_id': line.id,
                'occasion_code_id': line.x_occasion_code_id,
                'work_production': line.x_manufacture_order_code_id,
                'account_analytic_id': line.x_account_analytic_id,
                'group_id': group_id.id
            }
            line_x_scheduled_date.append((line.id, str(date)))
            if line.x_location_id:
                if line.x_location_id.id not in list_location:
                    stock_move_ids[line.x_location_id.id] = [(0, 0, detail_data)]
                    list_location.append(line.x_location_id.id)
                else:
                    stock_move_ids[line.x_location_id.id].append((0, 0, detail_data))
        if self.x_punish:
            condition = True
        else:
            condition = False
        for move in stock_move_ids:
            master_data = master
            master_data['name'] = rule.picking_type_id.sequence_id.next_by_id()
            master_data['location_id'] = stock_move_ids[move][0][2].get('location_id')
            picking_id = self.env['stock.picking'].create(master_data)
            picking_id.move_ids_without_package = stock_move_ids[move]
            picking_id.confirm_from_so(condition)
            sql = f""" 
                with A as (
                    SELECT *
                    FROM ( VALUES {str(line_x_scheduled_date).replace('[', '').replace(']', '')})as A(sale_line_id,date)
                    )
                update stock_move
                    set date = A.date::timestamp
                from A
                where stock_move.sale_line_id = A.sale_line_id
                """
            self._cr.execute(sql)
        self.state = 'sale'
        if condition:
            advance_payment = self.env['sale.advance.payment.inv'].create({
                'sale_order_ids': [(6, 0, self.ids)],
                'advance_payment_method': 'delivered',
                'deduct_down_payments': True
            })
            invoice_id = advance_payment._create_invoices(advance_payment.sale_order_ids)
            invoice_id.action_post()

    def _conn(self, autocommit=True, encrypt="no"):
        ir_config = self.env['ir.config_parameter'].sudo()
        driver = ir_config.get_param("mssql.driver")
        host = ir_config.get_param("mssql.host")
        database = ir_config.get_param("mssql.database")
        username = ir_config.get_param("mssql.username")
        password = ir_config.get_param("mssql.password")
        return pyodbc.connect(
            f'DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password};'
            f'ENCRYPT={encrypt};CHARSET=UTF8;', autocommit=autocommit)

    def get_DebtBalance(self):
        cnxn = self._conn(True, "no")
        cursor = cnxn.cursor()
        doc_date = int(date.today().strftime('%Y%m%d'))
        ref_partner = self.partner_id.code
        branch_code = self.company_id.code
        sql = f"""
            SET NOCOUNT ON
              Exec usp_sys_CheckDebtBalance
              @_CustomerCode  = '{ref_partner}',
              @_DocDate =  '{doc_date}',
              @_BranchCode = '{branch_code}'
            """
        cursor.execute(sql)
        result = cursor.fetchone()
        debtBalance = float(result[0]) if result else 0
        cursor.close()
        return debtBalance


    def action_cancel(self):
        for line in self.order_line:
            if line.qty_delivered > 0:
                raise UserError(_('Đơn hàng đã được giao'))
        res = super(SaleOrder, self).action_cancel()
        return res

    def action_return(self):
        so_return = self.copy()
        picking_location_list = {}
        for picking in self.picking_ids:
            picking_location_list[picking.location_id.id] = picking.name
        so_return.update({
            'x_is_return': True,
            'x_origin': self.id,
            'state': 'sale'
        })
        for line in so_return.order_line:
            if picking_location_list.get(line.x_location_id.id):
                line.x_origin = picking_location_list.get(line.x_location_id.id)

    def action_punish(self):
        return {
            'name': _('Tạo hóa đơn phạt'),
            'view_mode': 'form',
            'res_model': 'create.sale.order.punish',
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'target': 'new'
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_cart_discount_fixed_price = fields.Float('Giảm giá cố định', digits=(16, 2))
    x_location_id = fields.Many2one('stock.location', 'Địa điểm kho')
    x_scheduled_date = fields.Date(string='Ngày giao hàng dự kiến')
    x_manufacture_order_code_id = fields.Many2one('forlife.production', string='Mã lệnh sản xuất')
    x_product_code_id = fields.Many2one('assets.assets', string='Mã tài sản')
    x_account_analytic_id = fields.Many2one('account.analytic.account', string='Trung tâm chi phí')
    x_occasion_code_id = fields.Many2one('occasion.code', string='Mã vụ việc')
    x_free_good = fields.Boolean(string='Hàng tặng')
    x_origin = fields.Char(string='Tài liệu gốc')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if self._context.get('import_file'):
            for line in lines:
                line._set_price_unit()
                line.compute_cart_discount_fixed_price()
        return lines

    @api.onchange('product_id')
    def _onchange_product_get_domain(self):
        self.x_account_analytic_id = self.order_id.x_account_analytic_ids[0]._origin if self.order_id.x_account_analytic_ids else None
        self.x_occasion_code_id = self.order_id.x_occasion_code_ids[0]._origin if self.order_id.x_occasion_code_ids else None
        self.x_manufacture_order_code_id = self.order_id.x_manufacture_order_code_id
        if self.order_id.x_sale_type:
            domain = [('detailed_type', '=', self.order_id.x_sale_type)]
            return {'domain': {'product_id': [('sale_ok', '=', True), '|', ('company_id', '=', False),
                                              ('company_id', '=', self.order_id.company_id)] + domain}}

    @api.onchange('x_product_code_id')
    def x_product_code_id_get_domain(self):
        if self.x_product_code_id:
            account = self.x_product_code_id.asset_account.id
            product_categ_id = self.env['product.category'].search(
                [('property_stock_valuation_account_id', '=', account)])
            if product_categ_id:
                product_id = self.env['product.product'].search([('categ_id', 'in', product_categ_id.ids)])
                domain = [('id', 'in', product_id.ids)]
                return {'domain': {'product_id': [('sale_ok', '=', True), '|', ('company_id', '=', False),
                                                  ('company_id', '=', self.order_id.company_id)] + domain,
                                   'x_product_code_id': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                         ('company_id', '=', self.order_id.company_id.id)]
                                   }}
            else:
                return {'domain': {'product_id': [('id', '=', 0)],
                                   'x_product_code_id': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                         ('company_id', '=', self.order_id.company_id.id)]
                                   }}
        else:
            return {'domain': {'x_product_code_id': [('state', '=', 'using'), '|', ('company_id', '=', False),
                                                     ('company_id', '=', self.order_id.company_id.id)]}}

    @api.onchange('price_unit', 'discount', 'product_uom_qty')
    def compute_cart_discount_fixed_price(self):
        self.x_cart_discount_fixed_price = self.price_unit * self.discount * self.product_uom_qty / 100

    @api.onchange('x_free_good')
    def _onchange_x_free_good(self):
        self._compute_price_unit()

    @api.onchange('price_unit')
    def _set_price_unit(self):
        if self.x_free_good:
            self.price_unit = 0
            return
        if self.product_id and self.price_unit:
            if self.product_id.product_tmpl_id.x_negative_value:
                self.price_unit = - abs(self.price_unit)
            else:
                self.price_unit = abs(self.price_unit)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        res = super()._compute_amount()
        for line in self:
            line.price_subtotal = line.price_unit * line.product_uom_qty - line.x_cart_discount_fixed_price
        return res

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        res = super(SaleOrderLine, self)._compute_price_unit()
        for line in self:
            # line._set_price_unit()
            if line.x_product_code_id:
                line.price_unit = 0
            # if line.order_id.partner_id and self.product_id and line.order_id.x_process_punish:
            #     line.set_price_unit()
        return res
    '''
    def set_price_unit(self):
        tmpl_id = self.product_id.product_tmpl_id.id
        sql = f"""
            select ppi.product_tmpl_id  , ppi.fixed_price from product_pricelist pp 
            left join product_pricelist_item ppi on ppi.pricelist_id = pp.id
            where 1=1
            and pp.x_punish is True
            and pp.x_partner_id = {self.order_id.partner_id.id}
            and (ppi.product_tmpl_id = {tmpl_id} or ppi.product_tmpl_id is null)
            and '{str(self.order_id.date_order)}' between ppi.date_start and ppi.date_end
            order by pp.id desc
            limit 2 
        """
        self._cr.execute(sql)
        result = self._cr.dictfetchall()
        if not result:
            raise UserError(_('Khách hàng chưa được cấu hình bảng giá cho đơn phạt'))
        if len(result) > 1:
            self.price_unit = [r.get('fixed_price') for r in result if r.get('product_tmpl_id') == tmpl_id][0]
        else:
            self.price_unit = [r.get('fixed_price') for r in result][0]
            
            '''
