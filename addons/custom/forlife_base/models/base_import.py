# -*- coding: utf-8 -*-

from odoo import models


class Import(models.TransientModel):
    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        if dryrun:
            return super(Import, self.with_context(test_import=True)).execute_import(fields, columns, options, dryrun=dryrun)
        return super(Import, self).execute_import(fields, columns, options, dryrun=dryrun)
