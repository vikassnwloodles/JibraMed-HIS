# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                         HEALTH QR_CODES PACKAGE                       #
#                      health_qrcodes.py: Main module                   #
#########################################################################
import qrcode
import barcode
import io
from trytond.model import fields
from trytond.pool import PoolMeta


__all__ = ['Party', 'Patient', 'Appointment', 'Newborn', 'LabTest']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    # Add the CODE39 Code to the Person for ID purposes
    barcode = fields.Function(fields.Binary('Code39'), 'make_code39')

    def make_code39(self, name):
        # Create the Code39 bar code to encode the Person ID
        party_puid = self.ref or ''
        puid = f'{party_puid}'

        CODE39 = barcode.get_barcode_class('code39')

        code39 = CODE39(puid, add_checksum=False)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        code39.write(holder)
        code39_png = holder.getvalue()
        holder.close()

        return bytearray(code39_png)


# Add the QR field and QR image in the patient model
class Patient(metaclass=PoolMeta):
    __name__ = 'gnuhealth.patient'

    # Add the QR Code to the Patient
    qr = fields.Function(fields.Binary('QR Code'), 'make_qrcode')
    barcode = fields.Function(fields.Binary('Code39'), 'make_code39')

    def make_qrcode(self, name):
        # Create the QR code

        patient_puid = self.puid or ''
        patient_blood_type = self.blood_type or ''
        patient_rh = self.rh or ''
        patient_gender = self.name.gender_str or ''
        patient_dob = ''

        if (self.dob):
            patient_dob = str(self.dob)

        qr_string = f'{patient_puid}\n' \
            f'Name: {self.name.rec_name}\n' \
            f'Gender: {patient_gender}\n' \
            f'DoB: {patient_dob}\n' \
            f'Blood Type: {patient_blood_type} {patient_rh}'

        qr_image = qrcode.make(qr_string)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        qr_image.save(holder)
        qr_png = holder.getvalue()
        holder.close()

        return bytearray(qr_png)

    def make_code39(self, name):
        # Create the Code39 bar code to encode the Patient ID

        patient_puid = self.puid or ''
        puid = f'{patient_puid}'

        CODE39 = barcode.get_barcode_class('code39')

        code39 = CODE39(puid, add_checksum=False)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        code39.write(holder)
        code39_png = holder.getvalue()
        holder.close()

        return bytearray(code39_png)


class Appointment(metaclass=PoolMeta):
    __name__ = 'gnuhealth.appointment'

    # Add the QR Code to the Appointment
    qr = fields.Function(fields.Binary('QR Code'), 'make_qrcode')

    def make_qrcode(self, name):
        # Create the QR code

        appointment_healthprof = ''
        appointment_patient = ''
        patient_puid = ''
        appointment_specialty = ''
        appointment_date = ''
        appointment = ''

        if (self.name):
            appointment = self.name

        if (self.healthprof):
            appointment_healthprof = str(self.healthprof.rec_name) or ''

        if (self.patient):
            appointment_patient = self.patient.rec_name or ''
            patient_puid = self.patient and self.patient.puid

        if (self.appointment_date):
            appointment_date = str(self.appointment_date)

        if (self.speciality):
            appointment_specialty = str(self.speciality.rec_name) or ''

        qr_string = f'{appointment}\n' \
            f'Name: {appointment_patient}\n' \
            f'PUID: {patient_puid}\n' \
            f'Specialty: {appointment_specialty}\n' \
            f'Health Prof: {appointment_healthprof}\n' \
            f'Date: {appointment_date}'

        qr_image = qrcode.make(qr_string)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        qr_image.save(holder)
        qr_png = holder.getvalue()
        holder.close()

        return bytearray(qr_png)


class Newborn(metaclass=PoolMeta):
    'NewBorn'
    __name__ = 'gnuhealth.newborn'

    # Add the QR Code to the Newborn
    qr = fields.Function(fields.Binary('QR Code'), 'make_qrcode')

    def make_qrcode(self, name):
        # Create the QR code

        newborn_mother_name = self.mother and self.mother.rec_name or ''
        newborn_mother_id = self.mother and self.mother.puid or ''

        newborn_name = self.newborn_name or self.patient.rec_name or ''
        newborn_id = self.patient.puid or ''
        newborn_sex = self.sex_str or ''
        newborn_birth_date = self.birth_date or ''

        qr_string = f'{newborn_id}\n' \
            f'Name: {newborn_name}\n' \
            f'Mother: {newborn_mother_name}\n' \
            f'Mother\'s PUID: {newborn_mother_id}\n' \
            f'Sex: {newborn_sex}\n' \
            f'DoB: {str(newborn_birth_date)}'

        qr_image = qrcode.make(qr_string)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        qr_image.save(holder)
        qr_png = holder.getvalue()
        holder.close()

        return bytearray(qr_png)


class LabTest(metaclass=PoolMeta):
    __name__ = 'gnuhealth.lab'

    # Add the QR Code to the Lab Test
    qr = fields.Function(fields.Binary('QR Code'), 'make_qrcode')
    bar = fields.Function(fields.Binary('Bar Code39'), 'make_barcode')

    def make_qrcode(self, name):
        # Create the QR code

        labtest_id = self.name or ''
        labtest_type = self.test or ''

        patient_puid = self.patient and self.patient.puid or ''
        patient_name = self.patient and self.patient.rec_name or ''
        source = self.other_source

        requestor_name = self.requestor and self.requestor.rec_name or ''

        if self.is_patient():
            qr_string = f'{labtest_id}\n' \
                f'Test: {labtest_type.rec_name}\n' \
                f'Patient ID: {patient_puid}\n' \
                f'Patient: {patient_name}\n' \
                f'Requestor: {requestor_name}'
        else:
            qr_string = f'{labtest_id}\n' \
                f'Test: {labtest_type.rec_name}\n' \
                f'Source: {source}\n' \
                f'Requestor: {requestor_name}'

        qr_image = qrcode.make(qr_string)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        qr_image.save(holder)
        qr_png = holder.getvalue()
        holder.close()

        return bytearray(qr_png)

    def make_barcode(self, name):
        # Create the Code39 bar code to encode the TEST ID

        labtest_id = self.name or ''

        CODE39 = barcode.get_barcode_class('code39')

        code39 = CODE39(labtest_id, add_checksum=False)

        # Make a PNG image from PIL without the need to create a temp file

        holder = io.BytesIO()
        code39.write(holder)
        code39_png = holder.getvalue()
        holder.close()

        return bytearray(code39_png)
