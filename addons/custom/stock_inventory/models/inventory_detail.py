# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class InventoryDetail(models.Model):
    _name = 'inventory.detail'
    _description = 'Inventory Detail'
    _rec_name = 'inventory_id'

    inventory_id = fields.Many2one('stock.inventory', 'Phiếu kiểm kê', ondelete='restrict')
    product_id = fields.Many2one('product.product', 'Sản phẩm', ondelete='restrict')
    ma_hang = fields.Char('Mã hàng')
    ten_hang = fields.Char('Tên hàng')
    mau = fields.Char('Màu')
    size = fields.Char('Size')
    nhom_san_pham = fields.Char('Nhóm sản phẩm')
    don_vi = fields.Char('Đơn vị')
    gia = fields.Float('Giá')
    ton_phan_mam = fields.Integer('Tồn phần mềm', default=0)
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
    tong_kiem_ke_thuc_te_1 = fields.Integer('Tổng kiểm kê thực tế lần 1', compute="_compute_value")
    them2 = fields.Integer('Thêm lần 2', default=0)
    bot2 = fields.Integer('Bớt lần 2', default=0)
    tong_kiem_dem_thuc_te = fields.Integer('Tổng kiểm đếm thực tế', compute="_compute_value")
    chenh_lech_kiem_ke = fields.Integer('Chênh lệch kiểm kê', compute="_compute_value")
    ghi_chu = fields.Char('Ghi chú')
    phien_dem = fields.Char('Phiên đếm')

    def _compute_value(self):
        for line in self:
            tong_kiem_ke_thuc_te_1 = line.kiem_ke_thuc_te + line.phien_dem_bo_sung + line.hang_khong_kiem_dem + line.tui_ban_hang + line.hang_khong_tem + \
                                     line.hang_khong_cheat_duoc + line.hang_loi_chua_duyet + line.hang_loi_da_duyet + line.them1 - line.bot1 + \
                                     line.cong_hang_ban_ntl_chua_kiem - line.tru_hang_ban_da_kiem + line.bo_sung_hang_chua_cheat - line.tru_hang_kiem_dup
            line.tong_kiem_ke_thuc_te_1 = tong_kiem_ke_thuc_te_1
            line.tong_kiem_dem_thuc_te = tong_kiem_ke_thuc_te_1 + line.them2 - line.bot2
            line.chenh_lech_kiem_ke = line.ton_phan_mam - (tong_kiem_ke_thuc_te_1 + line.them2 - line.bot2)

    def open_detail(self):
        self.ensure_one()
        action = self.env.ref('stock_inventory.session_detail_by_product_action').read()[0]
        action['domain'] = [('product_id', '=', self.product_id.id), ('inv_session_id.inv_id', '=', self.inventory_id.id), ('updated', '=', True)]
        action['context'] = '{}'
        action.update({'target': 'new'})
        return action
