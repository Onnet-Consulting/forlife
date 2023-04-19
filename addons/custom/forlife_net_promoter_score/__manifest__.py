# -*- coding: utf-8 -*-
{
    'name': "Forlife Net Promoter Score",

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
        'point_of_sale',
        'forlife_point_of_sale',
        'forlife_telegram_integration',
        'report_xlsx',
    ],

    'data': [
        'security/nps_security.xml',
        'security/ir.model.access.csv',
        'data/cron_job_data.xml',
        'data/forlife_app_api_link_data.xml',

        'views/forlife_question_views.xml',
        'views/forlife_comment_views.xml',
        'views/forlife_app_api_link_views.xml',
        'wizard/net_promoter_score_report_views.xml',
        'report/net_promoter_score_xlsx_report.xml',
    ]
}
