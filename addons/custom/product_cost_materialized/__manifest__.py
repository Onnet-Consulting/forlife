# -*- coding: utf-8 -*-
{
    'name': "Product Materialized",
    'summary': """ - Create materialized for Account stock period value""",
    #TienNQ
    'website': "",
    'category': 'account',
    'version': '16.0.0.1',
    'license': 'LGPL-3',
    'depends': ['base','product_cost_config'],
    'data': [
        'security/ir.model.access.csv',
        'data/manage_materialized_cron.xml',
        'views/manage_materialized.xml'
    ]
}
