from odoo import models, fields, api
import logging
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image
import io
import base64
import re
import face_recognition
import numpy as np

_logger = logging.getLogger(__name__)



class EmployeeImage(models.Model):
    _name = 'employee.image'
    _description = 'Employee Image Detection'

    name = fields.Char(string='Name', readonly=True)
    department = fields.Char(string='Department', readonly=True)
    manager_name = fields.Char(string='Manager Name', readonly=True)
    image = fields.Binary(string='Upload Image', required=True)
    result = fields.Text(string='Detection Result', readonly=True)

    def action_detect_employee(self):
        """Trigger employee detection manually from a button click."""
        if not self.image:
            return

        # First, try face recognition
        face_recognition_result = self.recognize_employee_face(self.image)
        if 'error' not in face_recognition_result:
            self.write(face_recognition_result)
        else:
            # Fallback to text detection
            detection_result = self.detect_employee_details(self.image)
            self.write(detection_result)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Image detection completed!",
                'type': 'rainbow_man',
            }
        }

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
    def recognize_employee_face(self, image_data):
        # Decode the base64 image
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        image = np.array(image)  # Convert to numpy array for face_recognition

        # Detect faces in the uploaded image
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            return {"error": "No faces detected in the image."}

        # Encode the detected face
        uploaded_face_encoding = face_recognition.face_encodings(image, face_locations)[0]

        # Fetch all employees with face images
        employees = self.env['hr.employee'].search([('face_image', '!=', False)])
        for employee in employees:
            # Decode the employee's face image
            employee_face_image = Image.open(io.BytesIO(base64.b64decode(employee.face_image)))
            employee_face_image = np.array(employee_face_image)

            # Encode the employee's face
            employee_face_encoding = face_recognition.face_encodings(employee_face_image)
            if not employee_face_encoding:
                continue

            # Compare faces
            match = face_recognition.compare_faces([employee_face_encoding[0]], uploaded_face_encoding)
            if match[0]:
                return {
                    'name': employee.name,
                    'department': employee.department_id.name if employee.department_id else "Unknown",
                    'manager_name': employee.parent_id.name if employee.parent_id else "Unknown",
                    'result': "Face recognized successfully.",
                }

        return {"error": "No matching employee found."}

    @api.model
    def create(self, vals):
        # Detect employee details when an image is uploaded
        if 'image' in vals:
            # Try face recognition first
            face_recognition_result = self.recognize_employee_face(vals['image'])
            if 'error' not in face_recognition_result:
                vals.update(face_recognition_result)
            else:
                # Fallback to text detection if face recognition fails
                detection_result = self.detect_employee_details(vals['image'])
                vals.update(detection_result)
        return super(EmployeeImage, self).create(vals)