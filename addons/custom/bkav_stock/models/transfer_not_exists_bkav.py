# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta, time


class TransferNotExistsBkav(models.Model):
    _name = 'transfer.not.exists.bkav'
    _description = 'General Transfer Not Exists Bkav'
    _rec_name = 'id'
    _order = 'id desc'

    #bkav
    exists_bkav = fields.Boolean(default=False, copy=False)
    is_post_bkav = fields.Boolean(default=False, string="Đã tạo HĐ trên BKAV", copy=False)
    is_check_cancel = fields.Boolean(default=False, copy=False)

    ###trạng thái và số hdđt từ bkav trả về
    invoice_state_e = fields.Char('Trạng thái HDDT', compute='_compute_data_compare_status', store=1,copy=False)
    invoice_guid = fields.Char('GUID HDDT', copy=False)
    invoice_no = fields.Char('Số HDDT', copy=False)
    invoice_form = fields.Char('Mẫu số HDDT', copy=False)
    invoice_serial = fields.Char('Ký hiệu HDDT', copy=False)
    invoice_e_date = fields.Datetime('Ngày HDDT', copy=False)
    data_compare_status = fields.Selection([('1', 'Mới tạo'),
                                            ('2', 'Đã phát hành'),
                                            ('3', 'Đã hủy'),
                                            ('4', 'Đã xóa'),
                                            ('5', 'Chờ thay thế'),
                                            ('6', 'Thay thế'),
                                            ('7', 'Chờ điều chỉnh'),
                                            ('8', 'Điều chỉnh'),
                                            ('9', 'Bị thay thế'),
                                            ('10', 'Bị điều chỉnh'),
                                            ('11', 'Trống (Đã cấp số, Chờ ký)'),
                                            ('12', 'Không sử dụng'),
                                            ('13', 'Chờ huỷ'),
                                            ('14', 'Chờ điều chỉnh chiết khấu'),
                                            ('15', 'Điều chỉnh chiết khấu')], copy=False)

    eivoice_file = fields.Many2one('ir.attachment', 'eInvoice PDF', readonly=1, copy=0)

    code = fields.Char(string="Mã", default="New", copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Công ty', related='location_id.company_id', store=True)
    date_transfer = fields.Date("Ngày xác nhận xuất", default=lambda x: fields.Date.today(), copy=False)
    location_id = fields.Many2one('stock.location', string="Kho xuất")
    location_dest_id = fields.Many2one('stock.location', string="Kho nhập")
    vendor_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng kinh tế số")
    delivery_contract_id = fields.Many2one('vendor.contract', string="Hợp đồng số")
    location_name = fields.Char('Tên kho xuất')
    location_dest_name = fields.Char('Tên kho nhập')
    transporter_id = fields.Many2one('res.partner', string="Người/Đơn vị vận chuyển")
    transfer_ids = fields.Many2many('stock.transfer', 'stock_transfer_bkav_not_exist', 'bkav_not_exist_id','transfer_id',copy=False, string='DS điều chuyển')
    line_ids = fields.One2many(
        comodel_name='transfer.not.exists.bkav.line',
        inverse_name='parent_id',
        string='DS sản phẩm'
    )
    state = fields.Selection([('new', 'Mới'),('post', 'Đã tích hợp')], copy=False)

    def genarate_code(self):
        location_code = self.location_id.code
        code = 'PTH' + (location_code if location_code else '') + datetime.now().strftime("%y")
        param_code = code+'%'
        query = """ 
            SELECT code
            FROM (
                (SELECT '000001' as code)
                UNION ALL
                (SELECT RIGHT(name,6) as code
                FROM stock_transfer
                WHERE name like %s
                ORDER BY name desc
                LIMIT 1)) as compu
            ORDER BY code desc LIMIT 1
        """
        self._cr.execute(query, (param_code))
        result = self._cr.fetchall()
        for list_code in result:
            if list_code[0] == '000001':
                code+='000001'
            else:
                code_int = int(list_code[0])
                code+='0'*len(6-len(code_int+1))+str(code_int+1)
        self.code = code

    def general_transfer_not_exists_bkav(self):
        date_now = datetime.utcnow().date()
        # tổng hợp điều chuyển chưa xuat hd
        query = """
            INSERT INTO transfer_not_exists_bkav(code,location_id, location_dest_id, 
                            location_name, location_dest_name, date_transfer, state)
            SELECT 'PTH'||kn.code||RIGHT(DATE_PART('Year', NOW())::VARCHAR,2),
                s.location_id, s.location_dest_id, 
                knc.name||'|'||kn.name, kdc.name||'/'||kd.name, 
                (s.date_transfer + interval '7 hours')::date, 'new'
            FROM stock_transfer s
            JOIN stock_location kn ON s.location_id = kn.id
            JOIN stock_location knc ON kn.location_id = knc.id
            JOIN stock_location kd ON s.location_id = kd.id
            JOIN stock_location kdc ON kd.location_id = kdc.id
            WHERE s.exists_bkav = 'f' 
            AND (s.date_transfer + interval '7 hours')::date < %s
            AND s.state in ('out_approve','in_approve','done')
            GROUP BY s.location_id, s.location_dest_id; 

            INSERT INTO transfer_not_exists_bkav_line(parent_id, product_id, uom_id, quantity)
            (SELECT a.id, b.product_id, b.uom_id, b.quantity
            FROM 
                (SELECT * 
                FROM transfer_not_exists_bkav 
                WHERE state = 'new') as a
            JOIN
                (SELECT s.location_id, s.location_dest_id, l.product_id, l.uom_id, sum(qty_out) as quantity
                FROM stock_transfer s, stock_transfer_line l
                WHERE l.stock_transfer_id = s.id
                AND s.exists_bkav = 'f' 
                AND (s.date_transfer + interval '7 hours')::date < %s
                AND s.state in ('out_approve','in_approve','done')
                GROUP BY s.location_id, s.location_dest_id, l.product_id, l.uom_id) as b 
            ON a.location_id = b.location_id AND a.location_dest_id = b.location_dest_id
            );

            INSERT INTO stock_transfer_bkav_not_exist(bkav_not_exist_id, transfer_id)
            (SELECT a.id, b.id
            FROM 
                (SELECT *
                FROM transfer_not_exists_bkav 
                WHERE state = 'new') as a
            JOIN
                (SELECT s.id, s.location_id, s.location_dest_id
                FROM stock_transfer s
                WHERE s.exists_bkav = 'f' 
                AND (s.date_transfer + interval '7 hours')::date < %s
                AND s.state in ('out_approve','in_approve','done')
                ) as b 
            ON a.location_id = b.location_id AND a.location_dest_id = b.location_dest_id
            );

            UPDATE transfer_not_exists_bkav t SET vendor_contract_id = p.vendor_contract_id
            FROM 
                (SELECT b.id, c.vendor_contract_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.vendor_contract_id is not null) p 
            WHERE t.id = b.id;

            UPDATE transfer_not_exists_bkav t SET delivery_contract_id = p.delivery_contract_id
            FROM 
                (SELECT b.id, c.delivery_contract_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.delivery_contract_id is not null) p 
            WHERE t.id = b.id;

            UPDATE transfer_not_exists_bkav t SET transporter_id = p.transporter_id
            FROM 
                (SELECT b.id, c.transporter_id
                FROM stock_transfer_bkav_not_exist a
                JOIN transfer_not_exists_bkav b ON a.bkav_not_exist_id = b.id
                JOIN stock_transfer c ON a.transfer_id = c.id
                WHERE b.state = 'new'
                AND c.transporter_id is not null) p 
            WHERE t.id = b.id;
        """
        self._cr.execute(query, (date_now,date_now,date_now))
        transfer_ids = self.env['transfer.not.exists.bkav'].search([('state','=','new')],order='id asc')
        for transfer_id in transfer_ids:
            transfer_id.genarate_code()
        

class TransferNotExistsBkavLine(models.Model):
    _name = 'transfer.not.exists.bkav.line'

    parent_id = fields.Many2one('transfer.not.exists.bkav', copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity')

