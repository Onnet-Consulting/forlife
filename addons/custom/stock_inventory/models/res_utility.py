# -*- coding: utf-8 -*-

from odoo import fields, api, models
import json
import base64


class ResUtility(models.AbstractModel):
    _inherit = 'res.utility'

    @api.model
    def get_stock_inventory_by_wh_id(self, wh_id):
        data = self.env['stock.inventory'].sudo().search([('company_id', '=', self.env.user.company_id.id),
                                                          ('warehouse_id', '=', wh_id),
                                                          ('state', 'in', ('first_inv', 'second_inv'))])
        return [{
            'id_phieu_kk': inv.id,
            'so_phieu_kk': inv.name,
            'dia_diem': inv.location_id.complete_name or '',
            'trang_thai': 'kk_b1' if inv.state == 'first_inv' else 'kk_b2',
            'tong_ton': sum(inv.mapped('line_ids.theoretical_qty'))
        } for inv in data]

    @api.model
    def get_stock_inventory_detail(self, inv_id):
        data = self.env['stock.inventory'].sudo().search([('id', '=', inv_id)])
        return {
            'total_qty': sum(data.mapped('line_ids.theoretical_qty')),
            'details': [{
                'barcode': line.product_id.barcode,
                'quantity': line.theoretical_qty
            } for line in data.mapped('line_ids')],
        }

    @api.model
    def create_inventory_session(self, inv_id, data, note=None):
        if not isinstance(data, list):
            raise ValueError('Dữ liệu kiểm kê phải là 1 danh sách')
        res = self.env['inventory.session'].sudo().create({
            'inv_id': inv_id,
            'data': base64.b64encode((json.dumps(data)).encode('utf-8')),
            'note': note,
        })
        return {
            'message': 'Cập nhật phiên đếm kiểm thành công',
            'id': res.id
        }

    @api.model
    def get_data_inventory_session(self, inv_id):
        recs = self.env['inventory.session'].sudo().search_read([('inv_id', '=', inv_id)], ['id', 'create_uid', 'data'])
        res = []
        for session in recs:
            check = 0
            loss = 0
            err = 0
            add = 0
            sub = 0
            for line in json.loads(base64.b64decode(session['data']).decode()):
                check += line.get('Check') or 0
                loss += line.get('Loss') or 0
                err += line.get('Err') or 0
                add += line.get('Add') or 0
                sub += line.get('Sub') or 0
            res.append({
                'session_id': session.get('id'),
                'create_user': session.get('create_uid')[1],
                'Check': check,
                'Loss': loss,
                'Err': err,
                'Add': add,
                'Sub': sub,
                'total': check + loss + err + add + sub,
            })
        return res

    @api.model
    def delete_inventory_session(self, inv_session_id):
        self.env['inventory.session'].sudo().browse(inv_session_id).write({'active': False})
        return 'Xóa thành công'

    @api.model
    def action_update_stock_inventory(self, inv_id):
        inv = self.env['stock.inventory'].sudo().search([('id', '=', inv_id), ('state', 'in', ('first_inv', 'second_inv'))], limit=1)
        if not inv:
            raise ValueError('Không thể xác nhận kiểm đếm tại thời điểm này')
        self.with_delay(description=f"Cập nhật dữ liệu kiểm đếm cho phiếu kiểm kê [{inv.id} - {inv.name}]").action_confirm_inventory_session(inv.id)
        return 'Cập nhật dữ liệu tổng kiểm đếm thành công'

    @api.model
    def action_confirm_inventory_session(self, inv_id):
        def get_value(type, qty):
            if type == 'first_inv':
                return {
                    'x_first_qty': qty or 0,
                    'product_qty': qty or 0,
                }
            if type == 'second_inv':
                return {
                    'product_qty': qty or 0,
                }

        inventory = self.env['stock.inventory'].sudo().search([('id', '=', inv_id)], limit=1)
        sessions = self.env['inventory.session'].sudo().search_read([('inv_id', '=', inv_id)], ['data'])
        if not inventory or not sessions:
            return False
        self._cr.execute(f"""
        with inventorys as (select distinct pp.barcode, 1 as x
                            from stock_inventory_line sil
                                     join product_product pp on pp.id = sil.product_id and pp.barcode notnull
                            where sil.inventory_id = {inv_id})
        select json_object_agg(barcode, x) as product_exists from inventorys
        """)
        result = self._cr.dictfetchone()
        product_exists = result.get('product_exists') or {}
        value_exits = {}
        value_not_exits = {}
        data = []
        for s in sessions:
            data.extend(json.loads(base64.b64decode(s['data']).decode()))
        for line in data:
            barcode = line.get('ItemID')
            qty = (line.get('Check') or 0) + (line.get('Loss') or 0) + (line.get('Err') or 0) + (line.get('Add') or 0) - (line.get('Sub') or 0)
            if barcode:
                if product_exists.get(barcode):
                    value_exits.update({
                        barcode: (value_exits.get(barcode) or 0) + qty
                    })
                else:
                    value_not_exits.update({
                        barcode: (value_not_exits.get(barcode) or 0) + qty
                    })
        if value_exits:
            for k, v in value_exits.items():
                inv = inventory.line_ids.filtered(lambda f: f.barcode == k)
                if inv:
                    inv.sudo().write(get_value(inventory.state, v))
            inventory.line_ids.filtered(lambda f: f.barcode not in list(value_exits.keys())).write({'x_first_qty': 0, 'product_qty': 0})
        else:
            inventory.line_ids.write({'x_first_qty': 0, 'product_qty': 0})
        if value_not_exits:
            products = self.env['product.product'].search([('barcode', 'in', list(value_not_exits.keys()))])
            values = []
            for k, v in value_not_exits.items():
                product = products.filtered(lambda f: f.barcode == k)
                if product:
                    product = product[0]
                    val = dict(get_value(inventory.state, v))
                    val.update({
                        'inventory_id': inventory.id,
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'location_id': inventory.location_id.id
                    })
                    values.extend([val])
            if values:
                self.env['stock.inventory.line'].sudo().create(values)
