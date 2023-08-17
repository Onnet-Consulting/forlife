# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class InventorySession(models.Model):
    _name = 'inventory.session'
    _description = 'Inventory Session'
    _rec_name = 'id'
    _order = 'inv_id, id'

    inv_id = fields.Many2one('stock.inventory', 'Phiếu kiểm kê', ondelete='restrict')
    note = fields.Char('Ghi chú')
    active = fields.Boolean('Hiệu lực', default=True)
    data = fields.Binary('Data')
    line_ids = fields.One2many('inventory.session.line', 'inv_session_id', string='Chi tiết')
    type = fields.Selection([('app', 'Từ app kiểm kê'), ('web', 'Nhập bổ sung từ web'), ('other', 'Nhập dữ liệu khác'), ('add', 'Nhập bổ sung lần 2')], 'Loại', default='app')
    updated = fields.Boolean('Đã đồng bộ', default=False)
    qty_total = fields.Integer('Tổng số lượng', compute='_compute_qty_total', store=True)

    @api.model
    def action_inactive_session(self):
        self.sudo().write({'active': False})

    @api.depends('line_ids')
    def _compute_qty_total(self):
        for line in self:
            line.qty_total = sum([i.kiem_ke_thuc_te + i.phien_dem_bo_sung + i.hang_khong_kiem_dem + i.tui_ban_hang + i.hang_khong_tem
                                  + i.hang_khong_cheat_duoc + i.hang_loi_chua_duyet + i.hang_loi_da_duyet + i.them1 - i.bot1 + i.cong_hang_ban_ntl_chua_kiem
                                  - i.tru_hang_ban_da_kiem + i.bo_sung_hang_chua_cheat - i.tru_hang_kiem_dup + i.them2 - i.bot2
                                  for i in line.line_ids])


class InventorySessionLine(models.Model):
    _name = 'inventory.session.line'
    _description = 'Inventory Session Line'
    _order = 'inv_session_id, id'

    inv_session_id = fields.Many2one('inventory.session', 'Phiên đếm kiểm', ondelete='restrict')
    product_id = fields.Many2one('product.product', 'Sản phẩm', ondelete='restrict')
    kiem_ke_thuc_te = fields.Integer('Kiểm kê thực tế', default=0)
    phien_dem_bo_sung = fields.Integer('Phiên đếm bổ sung', default=0)
    hang_khong_kiem_dem = fields.Integer('Hàng không kiểm đếm', default=0)
    tui_ban_hang = fields.Integer('Túi bán hàng', default=0)
    hang_khong_tem = fields.Integer('Hàng không tem', default=0)
    hang_khong_cheat_duoc = fields.Integer('Hàng không cheat được mã vạch', default=0)
    hang_loi_chua_duyet = fields.Integer('Hàng lỗi chưa được duyệt', default=0)
    hang_loi_da_duyet = fields.Integer('Hàng lỗi đã được duyệt', default=0)
    them1 = fields.Integer('Thêm lần 1', default=0)
    bot1 = fields.Integer('Bớt lần 1', default=0)
    cong_hang_ban_ntl_chua_kiem = fields.Integer('Công hàng bán / ntl chưa kiểm', default=0)
    tru_hang_ban_da_kiem = fields.Integer('Trừ hàng bán đã kiểm', default=0)
    bo_sung_hang_chua_cheat = fields.Integer('Bổ sung hàng chưa được cheat', default=0)
    tru_hang_kiem_dup = fields.Integer('Từ hàng kiểm đúp', default=0)
    them2 = fields.Integer('Thêm lần 2', default=0)
    bot2 = fields.Integer('Bớt lần 2', default=0)
    ghi_chu = fields.Char('Ghi chú')
    active = fields.Boolean('Hiệu lực', related='inv_session_id.active')
    updated = fields.Boolean('Đã đồng bộ', related='inv_session_id.updated')
