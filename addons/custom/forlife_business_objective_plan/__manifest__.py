# -*- coding: utf-8 -*-
{
    'name': "Forlife Business Objective Plan",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Sales/Point of Sale',

    'depends': [
        'forlife_base',
        'forlife_point_of_sale',
    ],

    'data': [
        'security/business_objective_plan_security.xml',
        'security/ir.model.access.csv',

        'data/ir_attachment_data.xml',

        'views/business_objective_employee_views.xml',
        'views/business_objective_plan_views.xml',
        'views/business_objective_store_views.xml',
        'views/employee_transfer_views.xml',
        'views/coefficient_revenue_views.xml',

        'wizard/bo_import_excel_wizard_views.xml',
        
        'views/menuitem.xml',
    ],
}
