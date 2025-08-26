import math
from odoo import models, fields, api


class ProjectTask(models.Model):

    _inherit = 'project.task'

    distance = fields.Float(string="Distance (km)", readonly=True,
                            compute="_compute_distance")

    def _calculate_distance_with_haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate the distance between two geographical points using the
        Haversine formula.
        More info here:https://en.wikipedia.org/wiki/Haversine_formula
        """
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(
            math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = round(R * c, 2)
        return distance

    @api.depends('partner_id', 'company_id')
    def _compute_distance(self):
        for task in self:

            lat1 = task.partner_id.partner_latitude
            lon1 = task.partner_id.partner_longitude

            lat2 = task.company_id.partner_id.partner_latitude
            lon2 = task.company_id.partner_id.partner_longitude
            if (
                lat1 is not None and
                lon1 is not None and
                lat2 is not None and
                lon2 is not None
            ):
                task.distance = task._calculate_distance_with_haversine(
                    lat1, lon1, lat2, lon2)
            else:
                task.distance = 0.0
