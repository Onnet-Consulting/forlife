from odoo import fields, api, models
from datetime import datetime


class ApiStockTransfer(models.AbstractModel):
    _inherit = 'res.utility'

    @api.model
    def get_list_stock_transfer(self, **kwargs):
        page = kwargs.get('page', 1)
        limit = kwargs.get('limit', 100)
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')
        offset = limit * (page - 1)

        if (datetime.strptime(date_from, '%Y-%m-%d') - datetime.strptime(date_to, '%Y-%m-%d')).days > 30:
            return {
                "status": 400,
                "message": 'Khoảng thời gian lấy dữ liệu không được lớn hơn 30 ngày.',
            }

        domain = [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
            ('state', '=', 'approved'),
        ]
        stock_transfer = self.env['stock.transfer'].search(domain, limit=limit, offset=offset)
        total = self.env['stock.transfer'].search_count(domain)

        response = {
            "status": 200,
            "message": '',
            "pagination": {
                "page": page,
                "limit": limit,
                "total_page": total
            },
        }
        data = []
        for rec in stock_transfer:
            data.append({
                "bill_code": rec.name or '',
                "export_date": rec.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "description": rec.note or '',
                "weight": rec.total_weight,
                "num_of_packs": rec.total_package,
                "branch_from": rec.location_id.code or '',
                "branch_to": rec.location_dest_id.code or '',
                "partner_id": rec.transporter_id.code or '',
            })
        response.update({'data': data})
        return response

    @api.model
    def get_detail_stock_transfer(self, **kwargs):
        transfer_code = kwargs.get('transfer_code')
        stock_transfer = self.env['stock.transfer'].search([('name', '=', transfer_code)])
        if not stock_transfer:
            return {
                "status": 404,
                "message": 'Không tôn tài phiếu xuất điều chỉnh nội bộ với mã %s' % transfer_code
            }
        data = {}
        for rec in stock_transfer:
            data = {
                "bill_code": rec.name or '',
                "export_date": rec.create_date.strftime('%Y-%m-%dT%H:%M:%S'),
                "description": rec.note or '',
                "weight": rec.total_weight,
                "num_of_packs": rec.total_package,
                "branch_from": rec.location_id.code or '',
                "branch_to": rec.location_dest_id.code or '',
                "partner_id": rec.transporter_id.code or '',
            }
        response = {
            "status": 200,
            "message": '',
            "data": data,
        }
        return response
