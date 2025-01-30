from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    face_image = fields.Binary(string='Face Image', help="Upload an image of the employee's face for recognition.")