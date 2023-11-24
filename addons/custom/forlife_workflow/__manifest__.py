{
    'name': 'Forlife WorkFlow',
    'version': '1.0',
    'description': '',
    'summary': '',
    'author': 'ForLife',
    'website': '',
    'license': 'LGPL-3',
    'category': 'Human Resources/Approvals',
    'depends': [
        'forlife_code',
    ],
    'installable': True,
    'auto_install': False,
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',

        'views/approval_level_workflow_view.xml',
        'views/business_group_workflow_view.xml',
        'views/document_detail_workflow_view.xml',
        'views/authorization_workflow_view.xml',
        'views/document_workflow_view.xml',
        'views/history_information_workflow_view.xml',
        'views/update_status_workflow_view.xml',
        'views/menu_item.xml',
    ],
}
