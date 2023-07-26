# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import json


class RequestConfirmationPickingWizard(models.TransientModel):
    _name = 'request.confirmation.picking.wizard'
    _description = 'Yêu cầu xác nhận phiếu kho'

    name = fields.Text('Name', readonly=True)
    inventory_id = fields.Many2one('stock.inventory', 'Inventory')

    def btn_continue(self):
        self.inventory_id.sudo()._action_start()
        self.inventory_id.sudo()._check_company()
