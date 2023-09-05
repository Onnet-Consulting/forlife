# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _, Command
import logging

_logger = logging.getLogger(__name__)


class IrActionsInherit(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model
    def get_bindings(self, model_name):
        result = super(IrActionsInherit, self).get_bindings(model_name)
        if model_name == 'purchase.order':
            actions = result.get('action')
            for action in actions:
                if action.get('id') == self.env.ref(f'purchase.action_purchase_batch_bills').id:
                    actions.remove(action)
                    result.update({'action': actions})
        return result
