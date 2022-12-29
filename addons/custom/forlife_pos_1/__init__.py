# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID


def _update_required_attribute_for_fields(cr, registry):
    # update missing required field values for already exist partner
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False})
    partners = env['res.partner'].search([('group_id', '=', False)])
    partners.write({'group_id': env.ref('forlife_pos_1.partner_group_3').id})

    cr.execute("""
        UPDATE ir_model_fields
        SET required=TRUE
        WHERE name IN ('group_id', 'phone')
          AND model='res.partner';
    """)
    cr.commit()
