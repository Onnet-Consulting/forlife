# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CardRank(models.Model):
    _name = 'card.rank'
    _description = 'Card Rank'
    _order = 'priority desc'

    name = fields.Char('Name', required=True)
    priority = fields.Integer('Priority', required=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Rank name must be unique"),
    ]

    @api.constrains("priority")
    def validate_time(self):
        for record in self:
            record.check_unique_priority()
            previous_rank, next_rank = self.get_ranking_around(record.priority)
            programs = self.env['member.card'].search([('card_rank_id', '=', record.id)])
            if programs:
                for p in programs:
                    if previous_rank:
                        self.check_program_in_progres('>', previous_rank, p, record.name)
                    if next_rank:
                        self.check_program_in_progres('<', next_rank, p, record.name)

    def check_program_in_progres(self, operator, ids, program, rank):
        domain = list(program.get_master_domain())
        domain.insert(3, ('min_turnover', operator, program.min_turnover))
        domain.insert(3, ('card_rank_id', 'in', ids))
        domain.insert(0, '&')
        domain.insert(0, '&')
        res = self.env['member.card'].search(domain)
        if res:
            raise ValidationError(_("It is not possible to change the priority of the Rank '%s' due to the ongoing programs") % rank)

    def check_unique_priority(self):
        res = self.search([('id', '!=', self.id), ('priority', '=', self.priority)])
        if res:
            raise ValidationError(_("Priority must be unique '%s'") % self.priority)

    def get_ranking_around(self, priority):
        next_rank = self.search([('priority', '>', priority)], order='priority asc').ids
        previous_rank = self.search([('priority', '<', priority)]).ids
        return previous_rank, next_rank
