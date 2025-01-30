from odoo import models, fields, api
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image
import io
import base64
import re


class EmployeeImage(models.Model):
    _name = 'employee.image'
    _description = 'Employee Image Detection'

    name = fields.Char(string='Name', readonly=True)
    department = fields.Char(string='Department', readonly=True)
    manager_name = fields.Char(string='Manager Name', readonly=True)
    image = fields.Binary(string='Upload Image', required=True)
    result = fields.Text(string='Detection Result', readonly=True)

    @api.model
    def detect_employee_details(self, image_data):
        # Decode the base64 image
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))

        # Use pytesseract to extract text from the image
        extracted_text = pytesseract.image_to_string(image)

        # Extract employee ID or name from the image text
        employee_identifier = self._extract_employee_identifier(extracted_text)

        # Fetch employee details from the HR module
        employee = self.env['hr.employee'].search([('name', 'ilike', employee_identifier)], limit=1)

        if employee:
            return {
                'name': employee.name,
                'department': employee.department_id.name if employee.department_id else "Unknown",
                'manager_name': employee.parent_id.name if employee.parent_id else "Unknown",
                'result': extracted_text,
            }
        else:
            return {
                'name': "Unknown",
                'department': "Unknown",
                'manager_name': "Unknown",
                'result': extracted_text,
            }

    def _extract_employee_identifier(self, text):
        # Look for an employee ID or name in the extracted text
        # Example: "Employee ID: 123" or "Name: John Doe"
        id_pattern = re.compile(r'Employee ID:\s*(\d+)')
        name_pattern = re.compile(r'Name:\s*([A-Za-z\s]+)')

        id_match = id_pattern.search(text)
        name_match = name_pattern.search(text)

        if id_match:
            return id_match.group(1).strip()  # Return employee ID
        elif name_match:
            return name_match.group(1).strip()  # Return employee name
        else:
            return "Unknown"

    @api.model
    def create(self, vals):
        # Detect employee details when an image is uploaded
        if 'image' in vals:
            detection_result = self.detect_employee_details(vals['image'])
            vals.update(detection_result)
        return super(EmployeeImage, self).create(vals)