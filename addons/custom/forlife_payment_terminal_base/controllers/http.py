# -*- coding:utf-8 -*-

from odoo.http import JsonRPCDispatcher


class RawJsonRPCDispatcher(JsonRPCDispatcher):
    routing_type = 'raw_json'

    def _response(self, result=None, error=None):
        response = {}
        if error is not None:
            response = error
        if result is not None:
            response = result
        return self.request.make_json_response(response)
