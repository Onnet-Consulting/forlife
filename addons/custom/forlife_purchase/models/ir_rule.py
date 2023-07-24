from odoo import models


class InheritIrRule(models.Model):
    _inherit = 'ir.rule'

    def _get_rules(self, model_name, mode='read'):
        results = super(InheritIrRule, self)._get_rules(model_name, mode)
        if not self._context.get('company_purchase') or not results or mode != 'read' or model_name != 'stock.location':
            return results
        stock_location_comp_rule = self.env.ref('stock.stock_location_comp_rule')
        stock_location_comp_rule_id = stock_location_comp_rule.id if stock_location_comp_rule.perm_read else 0
        return results.with_context(company_purchase=False).filtered(lambda r: r.id != stock_location_comp_rule_id)
