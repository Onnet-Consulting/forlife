# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID


def _update_required_attribute_for_fields(cr, registry):
    # update missing required field values for already exist partner
    env = api.Environment(cr, SUPERUSER_ID, {'active_test': False, 'initial_write_action': True})
    partner_obj = env['res.partner']
    partners = partner_obj.search([('group_id', '=', False)])
    partners.write({'group_id': env.ref('forlife_pos_1.partner_group_3').id})
    for partner in partners:
        partner_id = partner.id
        partner.write({
            'phone': partner_id,
            'ref': partner_id
        })
    cr.commit()

    cr.execute("""
        UPDATE ir_model_fields
        SET required=TRUE
        WHERE name IN ('group_id', 'phone', 'ref')
          AND model='res.partner';
    """)

    cr.execute("""
        ALTER TABLE res_partner
        ALTER COLUMN group_id
        SET NOT NULL,
        ALTER COLUMN ref
        SET NOT NULL,
        ALTER COLUMN phone
        SET NOT NULL
    """)

    cr.commit()
