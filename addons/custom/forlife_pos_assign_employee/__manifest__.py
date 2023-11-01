# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_assign_employee",
    "license": "LGPL-3",
    'summary': """""",

    'description': """
    """,

    'author': "ForLife",
    'website': "",

    'category': 'Sales/Point Of Sale',
    'version': '1.0',

    'depends': [
        'contacts',
        'forlife_point_of_sale',
        'forlife_pos_layout',
        'pos_hr',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'views/pos_order_views.xml',
        'wizard/assign_employee_order_line_wizard_views.xml',
        'wizard/print_employee_code_wizard_view.xml',
        'views/pos_order_templates.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_assign_employee/static/src/scss/pos.scss',
            'forlife_pos_assign_employee/static/src/js/**/*.js',
            'forlife_pos_assign_employee/static/src/xml/**/*.xml',
        ]
    }
}
