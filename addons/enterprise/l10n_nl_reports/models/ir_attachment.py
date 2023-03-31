# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from lxml import etree

from odoo import api, models, tools

_logger = logging.getLogger(__name__)

XSD_NAME = 'XmlAuditfileFinancieel3.2.xsd'

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def _l10n_nl_reports_load_xsd_files(self, force_reload=False):
        url = 'https://www.softwarepakketten.nl/upload/auditfiles/xaf/20140402_AuditfileFinancieelVersie_3_2.zip'
        tools.load_xsd_files_from_url(self.env, url, 'xsd_nl_xaf_3.2.zip', force_reload=force_reload, xsd_names_filter=XSD_NAME)
        return

    @api.model
    def l10n_nl_reports_validate_xml_from_attachment(self, xml_content):
        return tools.validate_xml_from_attachment(self.env, xml_content, XSD_NAME, self._l10n_nl_reports_load_xsd_files)

    @api.model
    def l10n_nl_reports_load_iso_country_codes(self):
        if self.env.context.get('skip_xsd', False):
            return set()

        def load_xsd():
            attachment = self.search([('name', '=', XSD_NAME)])
            if attachment:
                return attachment
            self._l10n_nl_reports_load_xsd_files()
            return self.search([('name', '=', XSD_NAME)])

        attachment = load_xsd()
        if not attachment:
            return set()

        country_code_container = etree.fromstring(attachment.raw).find(
            './/{http://www.w3.org/2001/XMLSchema}simpleType[@name="CountrycodeIso3166"]')
        return set(
            e.attrib['value']
            for e in country_code_container.findall('.//{http://www.w3.org/2001/XMLSchema}enumeration')
        )
