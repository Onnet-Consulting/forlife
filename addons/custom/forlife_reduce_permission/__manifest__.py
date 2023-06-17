# -*- coding: utf-8 -*-
{
    'name': "forlife_reduce_permission",

    'summary': """
        Reduce Permission of base""",

    'description': """
        Reduce Permission of base"
    """,

    'author': "thang.dao@onnet",
    'website': "Onnet",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'stock',
                'point_of_sale',
                'purchase',
                'sales_team',
                'account'
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/groups.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
    ]
}
