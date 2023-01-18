# -*- coding: utf-8 -*-
{
    'name': "forlife_pos_assign_employee",

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
        'pos_hr',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'wizard/assign_employee_order_line_wizard_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'forlife_pos_assign_employee/static/src/scss/pos.scss',
            'forlife_pos_assign_employee/static/src/js/**/*.js',
            'forlife_pos_assign_employee/static/src/xml/**/*.xml',
        ]
    }
}
