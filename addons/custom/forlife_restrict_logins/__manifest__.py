# -*- coding: utf-8 -*-
{
    'name': "forlife_restrict_logins",

    'summary': """
        This module restricts the concurrent sessions for users.The user will get restricted from login if they already login in to another device.Also it provides an option to force logout for users""",

    'description': """
        This module restricts the concurrent sessions for users.The user will get restricted from login if they already login in to another device.Also it provides an option to force logout for users
    """,

    'author': "thang.dao@on.net.vn",
    'website': "https://on.net.vn/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_users_view.xml',
        'views/templates.xml',
        'data/data.xml'
    ]

}
