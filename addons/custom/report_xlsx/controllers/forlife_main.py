# -*- coding: utf-8 -*-

from odoo.http import Controller, request, route, content_disposition
from odoo.tools.safe_eval import safe_eval


class ReportController(Controller):
    @route(['/custom/download/xlsx/<report_name>/<model_name>/<int:record_id>/<allowed_company>'], type='http', auth="user")
    def report_download(self, report_name, model_name, record_id, allowed_company):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('%s.xlsx' % report_name))
            ]
        )
        response.stream.write(request.env[model_name].browse(record_id).get_xlsx(safe_eval(allowed_company)))
        return response
