# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero
from odoo import api, fields, models, _, tools
import json


def read_sql_file(file_path):
    fd = tools.file_open(file_path, 'r')
    sqlFile = fd.read()
    fd.close()
    return sqlFile


class Inventory(models.Model):
    _name = "stock.inventory"
    _description = "Kiểm kê kho"
    _order = "date desc, id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Mã phiếu', default="Phiếu kiểm kê", readonly=True, required=True,
                       states={'draft': [('readonly', False)]})
    date = fields.Datetime('Ngày kiểm kho', required=True, default=fields.Datetime.now)
    accounting_date = fields.Date('Ngày kế toán')
    line_ids = fields.One2many('stock.inventory.line', 'inventory_id', string='Chi tiết tồn kho',
                               copy=False, readonly=False, states={'done': [('readonly', True)]})
    move_ids = fields.One2many('stock.move', 'inventory_id', string='Created Moves',
                               states={'done': [('readonly', True)]})
    state = fields.Selection(string='Trạng thái', selection=[
        ('draft', 'Nháp'),
        ('waiting', 'Chờ chốt tồn'),
        ('cancel', 'Hủy'),
        ('first_inv', 'Chờ xác nhận lần 1'),
        ('second_inv', 'Chờ xác nhận lần 2'),
        ('confirm', 'Xác nhận'),
        ('done', 'Hoàn thành'),
    ],
                             copy=False, index=True, readonly=True, tracking=True, default='draft')
    company_id = fields.Many2one('res.company', 'Công ty', readonly=True, index=True, required=True,
                                 states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', string='Kho hàng', readonly=True, check_company=True,
                                   states={'draft': [('readonly', False)]}, required=True)
    view_location_id = fields.Many2one(related='warehouse_id.view_location_id')

    location_id = fields.Many2one('stock.location', string='Địa điểm', readonly=True, check_company=True,
                                  states={'draft': [('readonly', False)]},
                                  domain="[('usage', 'in', ['internal']), ('id', 'child_of', view_location_id)]")

    #
    # filter_by = fields.Selection(string='Filtrer par', selection=[
    #     ('1', 'Product'),
    #     ('2', 'Category')],
    #     default='1', readonly=True, states={'draft': [('readonly', False)]})

    product_ids = fields.Many2many(
        'product.product', string='Sản phẩm', check_company=True,
        domain="[('type', '=', 'product')]", readonly=True,
        states={'draft': [('readonly', False)]})
    # categ_ids = fields.Many2many('product.category', string='Catégories', readonly=True, states={'draft': [('readonly', False)]})

    start_empty = fields.Boolean('Kho trống')

    prefill_counted_quantity = fields.Selection(string='Số lượng đã đếm',
                                                selection=[('counted', 'Mặc định bằng số lượng tồn kho'), ('zero', 'Mặc định bằng 0')], default='counted')
    exhausted = fields.Boolean('Gồm cả sản phẩm đã hết', readonly=True,
                               states={'draft': [('readonly', False)]})

    move_out_count = fields.Integer(string="Dịch chuyển đi", compute='_compute_stock_move_count')
    move_in_count = fields.Integer(string="Dịch chuyển đến", compute='_compute_stock_move_count')
    move_out_count1 = fields.Integer(string="Dịch chuyển đi 1", compute='_compute_stock_move_count')
    move_in_count1 = fields.Integer(string="Dịch chuyển đến 1", compute='_compute_stock_move_count')

    detail_ids = fields.One2many('inventory.detail', 'inventory_id', string='Chi tiết đếm kiểm', copy=False, readonly=True)
    x_status = fields.Integer('Trạng thái chi tiết', default=0,
                              help='1: Đã đồng bộ từ chi tiết kiểm kê\n2: Cửa hàng đã xác nhận lần 1\n3: Cửa hàng đã xác nhận lần 2')

    # total_valorisation = fields.Float(string='Tổng kiểm kê', compute='_compute_total_valorisation')
    #
    #
    #
    # @api.depends('line_ids')
    # def _compute_total_valorisation(self):
    #     self.total_valorisation = 0
    #     for line in self.line_ids:
    #         self.total_valorisation += line.total

    @api.onchange('company_id')
    def _onchange_company_id(self):
        # If the multilocation group is not active, default the location to the one of the main
        # warehouse.
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            if warehouse:
                self.location_id = warehouse.lot_stock_id

    def _compute_stock_move_count(self):
        for r in self:
            r.move_out_count = len(r.move_ids.filtered(lambda x: x.state == 'done' and x.location_id.id == r.location_id.id and x.inv_state == 'second_inv'))
            r.move_in_count = len(r.move_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.id == r.location_id.id and x.inv_state == 'second_inv'))
            r.move_out_count1 = len(r.move_ids.filtered(lambda x: x.state == 'done' and x.location_id.id == r.location_id.id and x.inv_state == 'first_inv'))
            r.move_in_count1 = len(r.move_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.id == r.location_id.id and x.inv_state == 'first_inv'))

    def action_view_move_out(self):
        """ Display moves raw for subcontracted product self. """
        self.ensure_one()
        move_out_ids = self.move_ids.filtered(lambda x: x.state == 'done' and x.location_id.id == self.location_id.id and x.inv_state == self._context.get('state'))
        return {
            'name': _('Xuất hàng'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(self.env.ref('stock.view_move_tree').id, 'list'), (self.env.ref('stock.view_move_form').id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', move_out_ids.ids)],
            'context': self.env.context
        }

    def action_view_move_in(self):
        """ Display moves raw for subcontracted product self. """
        self.ensure_one()
        move_in_ids = self.move_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.id == self.location_id.id and x.inv_state == self._context.get('state'))
        return {
            'name': _('Nhập hàng'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'views': [(self.env.ref('stock.view_move_tree').id, 'list'), (self.env.ref('stock.view_move_form').id, 'form')],
            'target': 'current',
            'domain': [('id', 'in', move_in_ids.ids)],
            'context': self.env.context
        }

    def copy_data(self, default=None):
        name = _("%s (copy)") % (self.name)
        default = dict(default or {}, name=name)
        return super(Inventory, self).copy_data(default)

    def unlink(self):
        for inventory in self:
            if (inventory.state not in ('draft', 'cancel')
                    and not self.env.context.get(MODULE_UNINSTALL_FLAG, False)):
                raise UserError(_('Bạn chỉ có thể xóa bản ghi kiểm kê ở trạng thái nháp. Nếu việc kiểm kê không được thực hiện, bạn có thể hủy bỏ nó.'))
        return super(Inventory, self).unlink()

    def action_approved_first(self):
        if self.state == 'first_inv' and self.x_status == 2:
            self.action_validate('second_inv')
        elif self.state == 'second_inv' and self.x_status == 3:
            self.action_validate('done')
        else:
            return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_validate(self, state):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('stock.group_stock_manager'):
            raise UserError(_("Only a stock manager can validate an inventory adjustment."))
        if self.state not in ('second_inv', 'first_inv') or state not in ('second_inv', 'done'):
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory "
                "has been already validated or isn't ready.", self.name))
        if state == 'second_inv':
            inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.x_first_qty)
            lines = self.line_ids.filtered(lambda l: float_compare(l.x_first_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        elif state == 'done':
            inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.x_first_qty != l.product_qty)
            lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        else:
            return False
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done(state)
        self.line_ids._check_company()
        self._check_company()
        return True

    def _action_done(self, state):
        if state == 'second_inv':
            current_state = 'first_inv'
            negative = next((line for line in self.mapped('line_ids') if line.x_first_qty < 0 and line.x_first_qty != line.theoretical_qty), False)
            if negative:
                raise UserError(_(
                    'You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s',
                    negative.product_id.display_name,
                    negative.x_first_qty
                ))
        else:
            current_state = 'second_inv'
            negative = next((line for line in self.mapped('line_ids') if line.product_qty < 0 and line.product_qty != line.x_first_qty), False)
            if negative:
                raise UserError(_(
                    'You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s',
                    negative.product_id.display_name,
                    negative.product_qty
                ))
        self.action_check(current_state)
        self.write({'state': state})
        self.post_inventory(current_state)
        return True

    def get_ir_sequence_inventory(self, warehouse_code=None):
        code = 'PKK_WAREHOUSE_' + warehouse_code
        ir_sequence = self.env['ir.sequence'].search([('code', '=', code)], limit=1)
        if ir_sequence:
            return ir_sequence
        vals = {
            'name': 'Kiểm kê kho: ' + code,
            'code': code,
            'company_id': None,
            'prefix': '%(y)s',
            'padding': 6,
            'number_increment': 1,
            'number_next_actual': 1
        }
        ir_sequence = self.env['ir.sequence'].create(vals)
        return ir_sequence

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'warehouse_id' in val and val.get('warehouse_id'):
                warehouse_code = self.env['stock.warehouse'].browse(val.get('warehouse_id')).code
                ir = self.get_ir_sequence_inventory(warehouse_code)
                val['name'] = 'PKK' + warehouse_code + ir.next_by_id()
        res = super(Inventory, self).create(vals_list)
        return res

    def post_inventory(self, state):
        # The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
        # as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
        # as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
        stock_move_ids = self.mapped('move_ids').filtered(lambda move: move.state != 'done' and move.inv_state == state)._action_done()
        stock_move_ids.move_line_ids.write({'date': self.date})
        stock_move_ids.write({'date': self.date})
        return True

    def action_check(self, state):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self.filtered(lambda x: x.state == state):
            # first remove the existing stock moves linked to this inventory
            inventory.with_context(prefetch_fields=False).mapped('move_ids').filtered(lambda s: s.inv_state == state).unlink()
            inventory.line_ids._generate_moves(state)

    def action_cancel_draft(self):
        self.sudo().mapped('move_ids')._action_cancel()
        self.sudo().line_ids.unlink()
        self.sudo().detail_ids.unlink()
        self.sudo().write({'state': 'draft', 'x_status': 0})
        inv_sessions = self.env['inventory.session'].search([('inv_id', 'in', self.ids)])
        if inv_sessions:
            inv_sessions.with_context(not_update_inv=True).sudo().action_inactive_session()

    def action_start(self):
        self.ensure_one()
        self._cr.execute(f"""
        select array_agg(distinct name) as picking
        from (select distinct sp.name as name
              from stock_picking sp
                       join stock_location sl on (sp.location_id = sl.id or sp.location_dest_id = sl.id)
              where state = 'assigned'
                and sl.code = '{self.location_id.code}'
              union all
              select distinct st.name as name
              from stock_transfer st
                       join stock_location sl on st.location_dest_id = sl.id
              where state = 'out_approve'
                and sl.code = '{self.location_id.code}') as datas
        """)
        result = self._cr.dictfetchone().get('picking') or []
        if result:
            action = self.env.ref('stock_inventory.request_confirmation_picking_wizard_action').read()[0]
            action['context'] = dict(self._context, default_inventory_id=self.id, default_name=json.dumps(result))
            return action
        else:
            self._action_start()
            self._check_company()
        # return self.action_open_inventory_lines()

    def _action_start(self):
        """ Confirms the Inventory Adjustment and generates its inventory lines
        if its state is draft and don't have already inventory lines (can happen
        with demo data or tests).
        """
        for inventory in self:
            if inventory.state != 'draft':
                continue
            vals = {
                'state': 'waiting',
                # 'date': fields.Datetime.now()
            }
            if not inventory.line_ids and not inventory.start_empty:
                self.env['stock.inventory.line'].create(inventory._get_inventory_lines_values())
            inventory.write(vals)

    '''
    def action_open_inventory_lines(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Inventory Lines'),
            'res_model': 'stock.inventory.line',
        }
        context = {
            'default_is_editable': True,
            'default_inventory_id': self.id,
            'default_company_id': self.company_id.id,
        }
        # Define domains and context
        domain = [
            ('inventory_id', '=', self.id),
            ('location_id.usage', 'in', ['internal', 'transit'])
        ]
        if self.location_ids:
            context['default_location_id'] = self.location_ids[0].id
            if len(self.location_ids) == 1:
                if not self.location_ids[0].child_ids:
                    context['readonly_location_id'] = True

        if self.product_ids:
            # no_create on product_id field
            action['view_id'] = self.env.ref('stock_inventory.stock_inventory_line_tree').id
                #self.env.ref('stock.stock_inventory_line_tree_no_product_create').id
            if len(self.product_ids) == 1:
                context['default_product_id'] = self.product_ids[0].id
        else:
            # no product_ids => we're allowed to create new products in tree
            action['view_id'] = self.env.ref('stock_inventory.stock_inventory_line_tree').id

        action['context'] = context
        action['domain'] = domain
        return action

    def action_view_related_move_lines(self):
        self.ensure_one()
        domain = [('move_id', 'in', self.move_ids.ids)]
        action = {
            'name': _('Product Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_type': 'list',
            'view_mode': 'list,form',
            'domain': domain,
        }
        return action
        '''

    def init(self):
        get_quantity_inventory = read_sql_file('./stock_inventory/sql_functions/get_quantity_inventory.sql')
        self.env.cr.execute(get_quantity_inventory)

    def action_print(self):
        return self.env.ref('stock_inventory.action_report_inventory').report_action(self)

    def action_print_valorisation(self):
        return self.env.ref('stock_inventory.action_report_inventory_valorisation').report_action(self)

    def _get_quantities(self):
        """Return quantities group by product_id, location_id, lot_id, package_id and owner_id

        :return: a dict with keys as tuple of group by and quantity as value
        :rtype: dict
        """
        self.ensure_one()
        if self.location_id:
            domain_loc = [('id', 'child_of', self.location_id.ids)]
        else:
            domain_loc = [('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])]
        locations_ids = [l['id'] for l in self.env['stock.location'].search_read(domain_loc, ['id'])]

        sql = f"""select * from get_quantity_inventory('{str(self.date)}', array{locations_ids}::integer[] ,array{self.product_ids.ids}::integer[])"""
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        return data
        # domain = [('company_id', '=', self.company_id.id),
        #           ('quantity', '!=', '0'),
        #           ('location_id', 'in', locations_ids)]
        # if self.prefill_counted_quantity == 'zero':
        #     domain.append(('product_id.active', '=', True))

        # if self.product_ids and self.filter_by == "1":
        #     domain = expression.AND([domain, [('product_id', 'in', self.product_ids.ids)]])
        #
        # if self.categ_ids and self.filter_by == "2":
        #     domain = expression.AND([domain, [('product_id.categ_id', 'in', self.categ_ids.ids)]])
        #
        # if self.marque_ids and self.filter_by == "3":
        #     domain = expression.AND([domain, [('product_id.product_brand_id', 'in', self.marque_ids.ids)]])

        # fields = ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id', 'quantity:sum']
        # group_by = ['product_id', 'location_id', 'lot_id', 'package_id', 'owner_id']

        # quants = self.env['stock.quant'].read_group(domain, fields, group_by, lazy=False)
        # return {(
        #     quant['product_id'] and quant['product_id'][0] or False,
        #     quant['location_id'] and quant['location_id'][0] or False,
        #     quant['lot_id'] and quant['lot_id'][0] or False,
        #     quant['package_id'] and quant['package_id'][0] or False,
        #     quant['owner_id'] and quant['owner_id'][0] or False):
        #     quant['quantity'] for quant in quants
        # }

    def _get_exhausted_inventory_lines_vals(self, non_exhausted_set):
        """Return the values of the inventory lines to create if the user
        wants to include exhausted products. Exhausted products are products
        without quantities or quantity equal to 0.

        :param non_exhausted_set: set of tuple (product_id, location_id) of non exhausted product-location
        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        if self.product_ids:
            product_ids = self.product_ids.ids
        else:
            product_ids = self.env['product.product'].search_read([
                '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
                ('type', '=', 'product'),
                ('active', '=', True)], ['id'])
            product_ids = [p['id'] for p in product_ids]

        if self.location_id:
            location_ids = self.location_id.ids
        else:
            location_ids = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)]).lot_stock_id.ids

        vals = []
        for product_id in product_ids:
            for location_id in location_ids:
                if ((product_id, location_id) not in non_exhausted_set):
                    vals.append({
                        'inventory_id': self.id,
                        'product_id': product_id,
                        'location_id': location_id,
                        'theoretical_qty': 0
                    })
        return vals

    def _get_inventory_lines_values(self):
        """Return the values of the inventory lines to create for this inventory.

        :return: a list containing the `stock.inventory.line` values to create
        :rtype: list
        """
        self.ensure_one()
        quants_groups = self._get_quantities()
        vals = []
        '''
        product_ids = tuple([p['product_id'] for p in quants_groups])
        query = f"""
            SELECT pp.id product_id, pt.uom_id 
            FROM product_product pp JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            WHERE pp.id in {product_ids}
        """
        self._cr.execute(query)
        product_uom_data = self._cr.dictfetchall()
        uom_data = {x['product_id']:x['uom_id']  for x in product_uom_data} if product_uom_data else {}
        '''
        for data in quants_groups:
            line = {
                'inventory_id': self.id,
                'product_qty': 0, # 0 if self.prefill_counted_quantity == "zero" else data.get('quanty'),
                'theoretical_qty': data.get('quanty'),
                'x_first_qty': 0, # data.get('quanty'),
                'product_id': data.get('product_id'),
                'location_id': data.get('location_id'),
                'product_uom_id': data.get('uom_id')
            }
            vals.append(line)
        if self.exhausted:
            vals += self._get_exhausted_inventory_lines_vals({(l['product_id'], l['location_id']) for l in vals})
        return vals

    def clone_detail_data(self):
        self.ensure_one()
        # if self.detail_ids or not self.line_ids:
        #     return False
        # val = []
        # attr_codes = self.env['res.utility'].get_attribute_code_config()
        # attr_values = self.env['res.utility'].get_attribute_value_by_product_id(product_ids=self.line_ids.product_id.ids)
        # for line in self.line_ids:
        #     product_attr_value = attr_values.get(str(line.product_id.id)) or {}
        #     mau = product_attr_value.get(attr_codes.get('mau_sac')) or []
        #     size = product_attr_value.get(attr_codes.get('size')) or []
        #     val.append({
        #         'inventory_id': self.id,
        #         'product_id': line.product_id.id,
        #         'ma_hang': line.product_id.barcode,
        #         'ten_hang': line.product_id.name,
        #         'mau': ','.join(mau),
        #         'size': ','.join(size),
        #         'nhom_san_pham': line.product_id.categ_id.complete_name,
        #         'don_vi': line.product_id.uom_id.name,
        #         'gia': line.product_id.lst_price,
        #         'ton_phan_mam': line.theoretical_qty,
        #     })
        # if val:
        #     self.env['inventory.detail'].create(val)
        self.write({'state': 'first_inv', 'x_status': 1})
            # self.message_post(body='Đã đồng bộ danh sách sản phẩm Chi tiết kiểm kê sang Chi tiết kiểm đếm')

    def btn_import_excel(self):
        self.ensure_one()
        action = self.env.ref('stock_inventory.import_inventory_session_action').read()[0]
        action['context'] = dict(self._context, default_inv_id=self.id)
        return action

    def btn_action_confirm1(self):
        self.write({'x_status': 2})
        self.message_post(body='Xác nhận dữ liệu đếm kiểm lần 1')
        self.action_update_qty_inventory_line(state='lan1')

    def btn_action_confirm2(self):
        self.write({'x_status': 3})
        self.message_post(body='Xác nhận dữ liệu đếm kiểm lần 2')
        self.action_update_qty_inventory_line(state='lan2')

    def action_update_qty_inventory_line(self, state):
        _new_vals = []
        for line in self:
            for detail in line.detail_ids:
                record = line.line_ids.filtered(lambda s: s.product_id.id == detail.product_id.id)
                if record:
                    record.sudo().write(self.env[self._name].get_value(state, detail))
                else:
                    val = dict(self.env[self._name].get_value(state, detail))
                    val.update({
                        'inventory_id': line.id,
                        'product_id': detail.product_id.id,
                        'product_uom_id': detail.product_id.uom_id.id,
                        'location_id': line.location_id.id
                    })
                    _new_vals.append(val)
        if _new_vals:
            self.env['stock.inventory.line'].sudo().create(_new_vals)

    @api.model
    def get_value(self, state, detail):
        val = {}
        if state == 'lan1':
            val = {
                'x_first_qty': detail.tong_kiem_ke_thuc_te_1 or 0,
            }
        if state == 'lan2':
            val = {
                'product_qty': detail.tong_kiem_dem_thuc_te or 0,
            }
        return val

    def btn_show_all_inv_session(self):
        action = self.env.ref('stock_inventory.inventory_session_action_active_id').read()[0]
        action['context'] = dict(self._context)
        return action

    def open_all_inv_session_detail(self):
        self.ensure_one()
        return self.env.ref('stock_inventory.session_detail_by_product_action').read()[0]

    def btn_export_inventory_detail(self):
        self.ensure_one()
        return self.env['import.inventory.session.wizard'].create({'inv_id': self.id}).print_xlsx()

    def update_inventory_detail(self):
        self.ensure_one()
        if self.state not in ('first_inv', 'second_inv'):
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        self.detail_ids.sudo().unlink()
        new_sessions = self.env['inventory.session'].search([('inv_id', '=', self.id), ('updated', '=', False)])
        if not new_sessions:
            raise ValidationError('Không thành công, không tìm thấy phiên kiêm kê mới, vui lòng kiểm tra lại')
        new_sessions.sudo().write({'updated': True})
        session_lines = self.env['inventory.session'].search([('inv_id', '=', self.id)]).line_ids
        if session_lines:
            sql = f"""
with concat_name as (select product_id, array_agg(concat(inv_id, '-', session_id)) as phien_dem
                     from (select distinct isl.product_id as product_id,
                                           ise.inv_id     as inv_id,
                                           ise.id         as session_id
                           from inventory_session_line isl
                                    join inventory_session ise on ise.id = isl.inv_session_id and ise.active is true
                           where ise.inv_id = {self.id}
                           order by isl.product_id, ise.inv_id, ise.id) as data1
                     group by product_id),
     get_note as (select distinct product_id, ghi_chu
                  from (select isl.product_id,
                               isl.ghi_chu,
                               row_number() over (partition by isl.product_id order by isl.id desc) as num
                        from inventory_session_line isl
                                 join inventory_session ise on ise.id = isl.inv_session_id and ise.active is true
                        where ise.inv_id = {self.id} and ise.type = 'other') as data2
                  where num = 1)
select json_object_agg(product_id, data.*) as inv_data
from (select isl.product_id                       as product_id,
             sum(isl.kiem_ke_thuc_te)             as kiem_ke_thuc_te,
             sum(isl.phien_dem_bo_sung)           as phien_dem_bo_sung,
             sum(isl.hang_khong_kiem_dem)         as hang_khong_kiem_dem,
             sum(isl.tui_ban_hang)                as tui_ban_hang,
             sum(isl.hang_khong_tem)              as hang_khong_tem,
             sum(isl.hang_khong_cheat_duoc)       as hang_khong_cheat_duoc,
             sum(isl.hang_loi_chua_duyet)         as hang_loi_chua_duyet,
             sum(isl.hang_loi_da_duyet)           as hang_loi_da_duyet,
             sum(isl.them1)                       as them1,
             sum(isl.bot1)                        as bot1,
             sum(isl.cong_hang_ban_ntl_chua_kiem) as cong_hang_ban_ntl_chua_kiem,
             sum(isl.tru_hang_ban_da_kiem)        as tru_hang_ban_da_kiem,
             sum(isl.bo_sung_hang_chua_cheat)     as bo_sung_hang_chua_cheat,
             sum(isl.tru_hang_kiem_dup)           as tru_hang_kiem_dup,
             sum(isl.them2)                       as them2,
             sum(isl.bot2)                        as bot2,
             cn.phien_dem                         as phien_dem,
             coalesce(gn.ghi_chu, '')             as ghi_chu
      from inventory_session_line isl
               join inventory_session ise on ise.id = isl.inv_session_id and ise.active is true
               left join concat_name cn on cn.product_id = isl.product_id
               left join get_note gn on gn.product_id = isl.product_id
      where ise.inv_id = {self.id}
      group by isl.product_id, cn.phien_dem, gn.ghi_chu) as data
                """
            self._cr.execute(sql)
            inv_data = self._cr.dictfetchone().get('inv_data') or {}
            attr_codes = self.env['res.utility'].get_attribute_code_config()
            attr_values = self.env['res.utility'].get_attribute_value_by_product_id(product_ids=session_lines.product_id.ids)
            detail_vals = []
            for product in session_lines.product_id:
                product_attr_value = attr_values.get(str(product.id)) or {}
                mau = product_attr_value.get(attr_codes.get('mau_sac')) or []
                size = product_attr_value.get(attr_codes.get('size')) or []
                field_add = {
                    'inventory_id': self.id,
                    'product_id': product.id,
                    'ma_hang': product.barcode,
                    'ten_hang': product.name,
                    'mau': ','.join(mau),
                    'size': ','.join(size),
                    'nhom_san_pham': product.categ_id.complete_name,
                    'don_vi': product.uom_id.name,
                    'gia': product.lst_price,
                    'ton_phan_mam': 0,
                }
                detail_vals.append(self._get_update_value(vals=inv_data.get(str(product.id)), field_add=field_add))
            if detail_vals:
                self.env['inventory.detail'].sudo().create(detail_vals)
        if self.x_status in (2, 3):
            self.write({'x_status': 0})
            self.message_post(body='Phiên kiểm đếm đã được cập nhật thêm. Bộ phận cửa hàng cần xác nhận lại để cập nhật Chi tiết kiểm kê')

    @api.model
    def _get_update_value(self, vals, **kwargs):
        field_list = {
            'kiem_ke_thuc_te': 0, 'phien_dem_bo_sung': 0, 'hang_khong_kiem_dem': 0, 'tui_ban_hang': 0,
            'hang_khong_tem': 0, 'hang_khong_cheat_duoc': 0, 'hang_loi_chua_duyet': 0, 'hang_loi_da_duyet': 0,
            'them1': 0, 'bot1': 0, 'cong_hang_ban_ntl_chua_kiem': 0, 'tru_hang_ban_da_kiem': 0, 'phien_dem': [],
            'bo_sung_hang_chua_cheat': 0, 'tru_hang_kiem_dup': 0, 'them2': 0, 'bot2': 0, 'ghi_chu': False,
        }
        field_list.update(kwargs.get('field_add') or {})
        values = {}
        for field, v in field_list.items():
            if field == 'phien_dem':
                values.update({
                    field: '|'.join(vals.get(field) or v)
                })
            else:
                values.update({
                    field: vals.get(field) or v
                })
        return values

    def action_filter_product(self):
        action = self.env.ref('stock_inventory.filter_product_wizard_action').read()[0]
        action['res_id'] = self.env['filter.product.wizard'].search([('inventory_id', '=', self.id)], limit=1).id
        return action


class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    @api.model
    def _domain_location_id(self):
        if self.env.context.get('active_model') == 'stock.inventory':
            inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
            if inventory.exists() and inventory.location_id:
                return "[('usage', 'in', ['internal', 'transit']), ('id', 'child_of', %s)]" % inventory.location_id.ids
        return "[('usage', 'in', ['internal'])]"

    @api.model
    def _domain_product_id(self):
        if self.env.context.get('active_model') == 'stock.inventory':
            inventory = self.env['stock.inventory'].browse(self.env.context.get('active_id'))
            if inventory.exists() and len(inventory.product_ids) > 1:
                return "[('type', '=', 'product'), ('id', 'in', %s)]" % inventory.product_ids.ids
        return "[('type', '=', 'product')]"

    is_editable = fields.Boolean()
    inventory_id = fields.Many2one('stock.inventory', 'Phiếu kiểm kê', check_company=True,
                                   index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Owner', check_company=True)
    product_id = fields.Many2one('product.product', 'Sản phẩm', check_company=True,
                                 domain=lambda self: self._domain_product_id(), index=True, required=True)
    barcode = fields.Char('Mã vạch', related='product_id.barcode')
    product_uom_id = fields.Many2one('uom.uom', 'Đơn vị tính', required=True, readonly=True)
    product_qty = fields.Float('Đếm được', default=0)
    categ_id = fields.Many2one(related='product_id.categ_id', store=True)
    location_id = fields.Many2one('stock.location', 'Địa điểm', check_company=True,
                                  domain=lambda self: self._domain_location_id(), index=True, required=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True, check_company=True,
        domain="[('location_id', '=', location_id)]",
    )
    prod_lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number', check_company=True,
        domain="[('product_id','=',product_id)]")
    company_id = fields.Many2one(
        'res.company', 'Công ty', related='inventory_id.company_id',
        index=True, readonly=True, store=True)
    state = fields.Selection(string='Status', related='inventory_id.state')
    theoretical_qty = fields.Float(
        'Tồn hiện có', default=0)
    x_first_qty = fields.Float(
        'Đã đếm', default=0,
        digits='Product Unit of Measure')
    difference_qty = fields.Float('Chênh lệch lần 2', compute='_compute_difference',
                                  readonly=True, digits='Product Unit of Measure', search="_search_difference_qty")
    difference_qty1 = fields.Float('Chênh lệch lần 1', compute='_compute_difference', digits='Product Unit of Measure')
    inventory_date = fields.Datetime('Ngày kiểm kho', readonly=True, default=fields.Datetime.now)
    outdated = fields.Boolean(string='Quantity outdated',
                              compute='_compute_outdated', search='_search_outdated')

    product_tracking = fields.Selection(string='Tracking', related='product_id.tracking', readonly=True)

    # unit_price = fields.Float(string='Unit Price', related='product_id.standard_price', readonly=True)
    #
    # total = fields.Float(string='Total',
    #                           compute='_compute_total')
    #
    # total_difference = fields.Float(string='Difference',
    #                           compute='_compute_total_difference')

    # @api.depends('product_qty', 'unit_price', 'theoretical_qty')
    # def _compute_total(self):
    #     for rec in self:
    #         rec.total = rec.unit_price * rec.product_qty
    #
    # @api.depends('product_qty', 'unit_price', 'theoretical_qty')
    # def _compute_total_difference(self):
    #     for rec in self:
    #         rec.total_difference = (rec.unit_price * rec.product_qty) -  (rec.unit_price * rec.theoretical_qty)

    @api.onchange('product_id')
    def get_line_default(self):
        if self.inventory_id.location_id:
            self.location_id = self.inventory_id.location_id
        if self.inventory_id.location_id:
            return {'domain': {'location_id': [('id', 'in', self.inventory_id.location_id.ids)]}}
        elif self.inventory_id.warehouse_id:
            return {'domain': {'location_id': [('warehourse_id', '=', self.inventory_id.warehouse_id.id)]}}
        else:
            return False

    # @api.onchange('theoretical_qty')
    # def set_x_first_qty(self):
    #     if self.theoretical_qty != self.x_first_qty:
    #         self.x_first_qty = self.theoretical_qty

    # @api.onchange('x_first_qty')
    # def set_product_qty(self):
    #     if self.x_first_qty != self.product_qty:
    #         self.product_qty = self.x_first_qty

    # @api.depends('product_qty', 'theoretical_qty')
    def _compute_difference(self):
        for line in self:
            line.difference_qty1 = line.x_first_qty - line.theoretical_qty
            line.difference_qty = line.product_qty - line.x_first_qty

    @api.depends('inventory_date', 'product_id.stock_move_ids', 'theoretical_qty', 'product_uom_id.rounding')
    def _compute_outdated(self):
        quants_by_inventory = {inventory: inventory._get_quantities() for inventory in self.inventory_id}
        for line in self:
            quants = quants_by_inventory[line.inventory_id] or {}
            if line.state == 'done' or not line.id:
                line.outdated = False
                continue
            qty = quants.get((
                line.product_id.id,
                line.location_id.id,
                line.prod_lot_id.id,
                line.package_id.id,
                line.partner_id.id), 0
            )
            if float_compare(qty, line.theoretical_qty, precision_rounding=line.product_uom_id.rounding) != 0:
                line.outdated = True
            else:
                line.outdated = False

    @api.onchange('product_id', 'location_id', 'product_uom_id', 'prod_lot_id', 'partner_id', 'package_id')
    def _onchange_quantity_context(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
        if self.product_id and self.location_id and self.product_id.uom_id.category_id == self.product_uom_id.category_id:  # TDE FIXME: last part added because crash
            # theoretical_qty = self.product_id.get_theoretical_quantity(
            #     self.product_id.id,
            #     self.location_id.id,
            #     lot_id=self.prod_lot_id.id,
            #     package_id=self.package_id.id,
            #     owner_id=self.partner_id.id,
            #     to_uom=self.product_uom_id.id,
            # )
            check_quant = self.env['stock.quant'].search(
                [('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id)])
            theoretical_qty = check_quant.quantity if check_quant else 0
        else:
            theoretical_qty = 0
        # Sanity check on the lot.
        if self.prod_lot_id:
            if self.product_id.tracking == 'none' or self.product_id != self.prod_lot_id.product_id:
                self.prod_lot_id = False

        if self.prod_lot_id and self.product_id.tracking == 'serial':
            # We force `product_qty` to 1 for SN tracked product because it's
            # the only relevant value aside 0 for this kind of product.
            self.product_qty = 1
        elif self.product_id and float_compare(self.product_qty, self.theoretical_qty, precision_rounding=self.product_uom_id.rounding) == 0:
            # We update `product_qty` only if it equals to `theoretical_qty` to
            # avoid to reset quantity when user manually set it.
            self.product_qty = theoretical_qty
        self.theoretical_qty = theoretical_qty

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to handle the case we create inventory line without
        `theoretical_qty` because this field is usually computed, but in some
        case (typicaly in tests), we create inventory line without trigger the
        onchange, so in this case, we set `theoretical_qty` depending of the
        product's theoretical quantity.
        Handles the same problem with `product_uom_id` as this field is normally
        set in an onchange of `product_id`.
        Finally, this override checks we don't try to create a duplicated line.
        """
        for values in vals_list:
            if 'theoretical_qty' not in values:
                check_quant = self.env['stock.quant'].search(
                    [('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id)])
                theoretical_qty = check_quant.quantity if check_quant else 0
                values['theoretical_qty'] = theoretical_qty
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        res = super(InventoryLine, self).create(vals_list)
        # res._check_no_duplicate_line()
        return res

    def write(self, vals):
        res = super(InventoryLine, self).write(vals)
        # self._check_no_duplicate_line()
        return res

    def _check_no_duplicate_line(self):
        for line in self:
            domain = [
                ('id', '!=', line.id),
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('partner_id', '=', line.partner_id.id),
                ('package_id', '=', line.package_id.id),
                ('prod_lot_id', '=', line.prod_lot_id.id),
                ('inventory_id', '=', line.inventory_id.id)]
            existings = self.search_count(domain)
            if existings:
                raise UserError(_("There is already one inventory adjustment line for this product,"
                                  " you should rather modify this one instead of creating a new one."))

    @api.constrains('product_id')
    def _check_product_id(self):
        """ As no quants are created for consumable products, it should not be possible do adjust
        their quantity.
        """
        if self.product_id.ids:
            query = """
                SELECT pp.id
                FROM product_product pp
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE pt.type != 'product'
                    AND pp.id in {product_ids}
            """.format(product_ids=tuple(self.product_id.ids + [0]))
            self._cr.execute(query)
            data = self._cr.dictfetchall()
            if data:
                for product in data:
                    product_id = self.env['product.product'].browse(product['id'])
                    raise ValidationError(_("You can only adjust storable products.") + '\n\n%s -> %s' % (product_id.display_name, product_id.type))

    def _get_move_values(self, qty, location_id, location_dest_id, out, inv_state):
        self.ensure_one()
        return {
            'name': _('INV:') + (self.inventory_id.name or ''),
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': qty,
            'date': self.inventory_id.date,
            'company_id': self.inventory_id.company_id.id,
            'inventory_id': self.inventory_id.id,
            'state': 'confirmed',
            'inv_state': inv_state,
            'restrict_partner_id': self.partner_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'lot_id': self.prod_lot_id.id,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': qty,
                'package_id': out and self.package_id.id or False,
                'result_package_id': (not out) and self.package_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'owner_id': self.partner_id.id,
            })]
        }

    def _get_virtual_location(self):
        return self.product_id.with_company(self.company_id).property_stock_inventory

    def _generate_moves(self, state):
        vals_list = []
        for line in self:
            if state == 'first_inv':
                difference_qty = line.difference_qty1
            elif state == 'second_inv':
                difference_qty = line.difference_qty
            else:
                continue
            virtual_location = line._get_virtual_location()
            rounding = line.product_id.uom_id.rounding
            if float_is_zero(difference_qty, precision_rounding=rounding):
                continue
            if difference_qty > 0:  # found more than expected
                vals = line._get_move_values(difference_qty, virtual_location.id, line.location_id.id, False, state)
                line.create_import_export_other(vals, type_picking='import')
            else:
                vals = line._get_move_values(abs(difference_qty), line.location_id.id, virtual_location.id, True, state)
                line.create_import_export_other(vals, type_picking='export')
            vals_list.append(vals)
        return self.env['stock.move'].create(vals_list)

    def action_refresh_quantity(self):
        filtered_lines = self.filtered(lambda l: l.state != 'done')
        for line in filtered_lines:
            if line.outdated:
                quants = self.env['stock.quant']._gather(line.product_id, line.location_id, lot_id=line.prod_lot_id, package_id=line.package_id, owner_id=line.partner_id, strict=True)
                if quants.exists():
                    quantity = sum(quants.mapped('quantity'))
                    if line.theoretical_qty != quantity:
                        line.theoretical_qty = quantity
                else:
                    line.theoretical_qty = 0
                line.inventory_date = fields.Datetime.now()

    def action_reset_product_qty(self):
        """ Write `product_qty` to zero on the selected records. """
        impacted_lines = self.env['stock.inventory.line']
        for line in self:
            if line.state == 'done':
                continue
            impacted_lines |= line
        impacted_lines.write({'product_qty': 0})

    def _search_difference_qty(self, operator, value):
        if operator == '=':
            result = True
        elif operator == '!=':
            result = False
        else:
            raise NotImplementedError()
        if not self.env.context.get('default_inventory_id'):
            raise NotImplementedError(_('Unsupported search on %s outside of an Inventory Adjustment', 'difference_qty'))
        lines = self.search([('inventory_id', '=', self.env.context.get('default_inventory_id'))])
        line_ids = lines.filtered(lambda line: float_is_zero(line.difference_qty, line.product_id.uom_id.rounding) == result).ids
        return [('id', 'in', line_ids)]

    def _search_outdated(self, operator, value):
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()
        if not self.env.context.get('default_inventory_id'):
            raise NotImplementedError(_('Unsupported search on %s outside of an Inventory Adjustment', 'outdated'))
        lines = self.search([('inventory_id', '=', self.env.context.get('default_inventory_id'))])
        line_ids = lines.filtered(lambda line: line.outdated == value).ids
        return [('id', 'in', line_ids)]
