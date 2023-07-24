from odoo import fields, api, models
import json
import logging

_logger = logging.getLogger(__name__)


class StockTransferInherit(models.Model):
    _name = 'stock.transfer'
    _inherit = ['stock.transfer', 'redis.action']

    def action_approve(self):
        super().action_approve()
        for rec in self:
            if rec.state == 'approved':
                rec.with_delay(max_retries=10, channel='root.Redis').send_transfer_to_redis()

    @api.model
    def send_transfer_to_redis(self):
        for rec in self.filtered(lambda x: x.state == 'approved'):
            brand_id = rec.location_id.warehouse_id.brand_id
            if brand_id:
                hash_key = 'INT-TKL' if brand_id.code == 'TKL' else 'INT-FM'
                data = {
                    "bill_code": rec.name or '',
                    "num_of_packs": rec.total_package,
                    "export_date": rec.create_date.strftime('%d-%m-%Y'),
                    "description": rec.note or '',
                    "weight": rec.total_weight,
                    "branch_from": rec.location_id.code or '',
                    "branch_to": rec.location_dest_id.code or '',
                    "partner_id": rec.transporter_id.code or '',
                }

                self.hset('internal_transfer', hash_key, rec.name, json.dumps(data))
                _logger.info("Send transfer to redis success with transfer_name (%s)", rec.name)
            _logger.info("Send transfer to redis failure: error -> brand_id not found")
