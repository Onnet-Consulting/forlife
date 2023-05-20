# Copyright 2016-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


{'name': 'Attachments on S3 storage',
 'summary': 'Store assets and attachments on a S3 compatible object storage',
 'version': '16.0.1.0.0',
 'author': 'onnet',
 'license': 'AGPL-3',
 'category': 'Knowledge Management',
 'depends': ['base', 'base_attachment_object_storage'],
 'external_dependencies': {
     'python': ['boto3'],
 },
 'website': 'https://on.net.vn/',
 'data': [
   'security/ir.model.access.csv',
   'views/aws_config_views.xml',
 ],
 'installable': True,
 }
