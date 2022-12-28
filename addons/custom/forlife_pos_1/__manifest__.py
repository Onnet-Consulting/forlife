# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_1",

    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",

    'category': 'Point of Sale',
    'version': '1.0',

    'depends': [
        'point_of_sale',
        'contacts',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_group.xml',
        'data/res_partner.xml',
        'data/ir_fields.xml',
        'views/res_partner_group_views.xml',
        'views/res_partner_job_views.xml',
        'views/res_partner_views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
    'post_init_hook': '_update_required_attribute_for_fields',
}
