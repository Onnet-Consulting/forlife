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
            'dia_diem': inv.mapped('location_ids.complete_name'),
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
    def create_inventory_session(self, inv_id, warehouse_code, data, note=None):
        if not isinstance(data, list):
            raise ValueError('Dữ liệu kiểm kê phải là 1 danh sách')
        res = self.env['inventory.session'].sudo().create({
            'inv_id': inv_id,
            'warehouse_code': warehouse_code,
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
            })
        return res

    @api.model
    def delete_inventory_session(self, inv_session_id):
        self.env['inventory.session'].sudo().browse(inv_session_id).write({'active': False})
        return 'Xóa thành công'

    @api.model
    def action_update_stock_inventory(self, inv_id):
        inv = self.env['stock.inventory'].sudo().search([('id', '=', inv_id), ('state', 'in', ('first_inv', 'second_inv'))])
        if not inv:
            raise ValueError('Không thể xác nhận kiểm đếm tại thời điểm này')
        inv = inv and inv[0]
        self.with_delay(description=f"Cập nhật dữ liệu kiểm đếm cho phiếu kiểm kê [{inv.id} - {inv.name}]").action_confirm_inventory_session(inv.id)
        return 'Cập nhật dữ liệu tổng kiểm đếm thành công'

    @api.model
    def action_confirm_inventory_session(self, inv_id):
        inventory = self.env['stock.inventory'].sudo().search([('id', '=', inv_id)])
        sessions = self.env['inventory.session'].sudo().search_read([('inv_id', '=', inv_id)], ['data'])
        if not inventory or not sessions:
            return False
        value = {}
        data = []
        for s in sessions:
            data.extend(json.loads(base64.b64decode(s['data']).decode()))
        for line in data:
            barcode = line.get('ItemId')
            qty = (line.get('Check') or 0) + (line.get('Loss') or 0) + (line.get('Err') or 0) + (line.get('Add') or 0) - (line.get('Sub') or 0)
            if barcode:
                value.update({
                    barcode: (value.get(barcode) or 0) + qty
                })
        if not value:
            return False
        if inventory.state == 'first_inv':
            for detail in inventory.line_ids:
                if detail.barcode in list(value.keys()):
                    detail.write({
                        'x_first_qty': value.get(detail.barcode) or 0,
                        'product_qty': value.get(detail.barcode) or 0,
                    })
        if inventory.state == 'second_inv':
            for detail in inventory.line_ids:
                if detail.barcode in list(value.keys()):
                    detail.write({
                        'product_qty': value.get(detail.barcode) or 0
                    })
