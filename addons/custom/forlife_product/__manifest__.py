# -*- coding: utf-8 -*-
{
    'name': "Product Forlife Customize",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Product/Forlife',

    'depends': [
        'base',
        'product',
        'account',
        'stock'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/product_inherit_view.xml',
        'views/product_category.xml',
        'views/product_attribute.xml',
        'views/product_template_views.xml'
    ]
}
