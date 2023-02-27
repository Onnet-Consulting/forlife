# -*- coding: utf-8 -*-
{
    'name': "HR Payroll",

    'summary': """
        """,

    'description': """
    """,

    'author': "ForLife",
    'website': "",
    "license": "LGPL-3",
    'version': '16.0.1.0,0',

    'category': 'Human Resources/Payroll',

    'depends': [
        'account',
        'hr',
        'queue_job',
        'report_xlsx',
        'l10n_vn',
        'forlife_sap_integration',
    ],

    'data': [
        'data/res_company_data.xml',
        'data/res_groups_data.xml',
        'data/queue_job_data.xml',
        'security/ir.model.access.csv',
        'data/ir_attachment_data.xml',
        'data/salary_record_type_data.xml',
        'data/salary_record_purpose_data.xml',
        'security/ir_rule.xml',

        # report
        'report/salary_record_report.xml',

        # views
        'views/res_partner_views.xml',
        'views/salary_record_type_views.xml',
        'views/salary_record_purpose_views.xml',
        'views/salary_entry_views.xml',
        'views/salary_accounting_config_views.xml',
        'views/salary_record_main_views.xml',
        'views/salary_total_income_views.xml',
        'views/salary_supplementary_views.xml',
        'views/salary_arrears_views.xml',
        'views/salary_accounting_views.xml',
        'views/salary_backlog_views.xml',
        'views/salary_record_views.xml',
        'views/save_change_log_views.xml',
        'views/account_move_views.xml',
        'views/hr_department_views.xml',

        # wizard
        'wizard/import_salary_record_view.xml',
        'wizard/error_log_wizard_view.xml',

        'views/menuitem.xml',
    ]
}
