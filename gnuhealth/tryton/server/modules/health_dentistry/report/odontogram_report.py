# SPDX-FileCopyrightText: 2020-2021 National University of Entre Rios (UNER)
#                         School of Engineering
#                         <saludpublica@ingenieria.uner.edu.ar>
# SPDX-FileCopyrightText: 2020 Mario Puntin <mario@silix.com.ar>
# SPDX-FileCopyrightText: 2020-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2020-2024 GNU Solidario <health@gnusolidario.org>

# SPDX-License-Identifier: GPL-3.0-or-later
#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                         HEALTH DENTISTRY package                      #
#                odontogram_report.py: odontogram report                #
#########################################################################
import io
import os
import json
from PIL import Image, ImageDraw, ImageFont
from trytond.report import Report
from trytond.pool import Pool


__all__ = ['Odontogram']


class Odontogram(Report):
    __name__ = 'health_dentistry.odontogram.report'

    x_distance = 86
    y_distance = 110

    __pieces = {
        '18': ( 1, 1), '17': ( 2, 1), '16': ( 3, 1), '15': ( 4, 1),
        '14': ( 5, 1), '13': ( 6, 1), '12': ( 7, 1), '11': ( 8, 1),
        '21': (10, 1), '22': (11, 1), '23': (12, 1), '24': (13, 1),
        '25': (14, 1), '26': (15, 1), '27': (16, 1), '28': (17, 1),
        '48': ( 1, 4), '47': ( 2, 4), '46': ( 3, 4), '45': ( 4, 4),
        '44': ( 5, 4), '43': ( 6, 4), '42': ( 7, 4), '41': ( 8, 4),
        '31': (10, 4), '32': (11, 4), '33': (12, 4), '34': (13, 4),
        '35': (14, 4), '36': (15, 4), '37': (16, 4), '38': (17, 4),
        '55': ( 4, 2), '54': ( 5, 2), '53': ( 6, 2), '52': ( 7, 2), '51': ( 8, 2),
        '61': (10, 2), '62': (11, 2), '63': (12, 2), '64': (13, 2), '65': (14, 2),
        '85': ( 4, 3), '84': ( 5, 3), '83': ( 6, 3), '82': ( 7, 3), '81': ( 8, 3),
        '71': (10, 3), '72': (11, 3), '73': (12, 3), '74': (13, 3), '75': (14, 3),
    }

    pieces = {}
    for key, value in __pieces.items():
        pieces[key] = (x_distance/2 + x_distance*(value[0]-1),
                       x_distance/2 + y_distance*(value[1]-1))
    
    image_size = (x_distance * 17, y_distance * 4)

    @classmethod
    def plot_teeth(cls, image, dschema):
        draw = ImageDraw.Draw(image)
        
        for tooth, values in cls.pieces.items():
            width = 3
            color = (0, 0, 0)

            x = values[0]
            y = values[1]
            d1 = cls.x_distance/2 * 0.9
            d2 = d1/2
            d3 = d1/1.414
            d4 = d2/1.414

            draw.ellipse((x - d1, y - d1, x + d1, y + d1), outline=color, width = width)
            
            if tooth in dschema.keys():
                draw.ellipse((x - d2, y - d2, x + d2, y + d2), outline=color, width = width)
                draw.line((x - d3, y - d3, x - d4, y - d4), fill=color, width=width)
                draw.line((x + d3, y + d3, x + d4, y + d4), fill=color, width=width)
                draw.line((x - d3, y + d3, x - d4, y + d4), fill=color, width=width)
                draw.line((x + d3, y - d3, x + d4, y - d4), fill=color, width=width)

            fontsize = cls.x_distance//4
            # Note: load_default support size argument when pillow-10.1.0
            font = ImageFont.load_default(size=fontsize)
            draw.multiline_text((x - fontsize * 0.65, y + d1 * 1.1), tooth, fill=color, font=font)

    @classmethod
    def plot_extraction(cls, image, piece_center, status):
        missing_color = "#0000ff"  # blue
        for_extraction_color = "#ff0000"  # red
        if (status == 'M'):
            color = missing_color
        else:
            color = for_extraction_color

        xcenter, ycenter = piece_center
        num = cls.x_distance/(2*1.414)
        llc = {'x': xcenter - num, 'y': ycenter + num}
        urc = {'x': xcenter + num, 'y': ycenter - num}
        ulc = {'x': xcenter - num, 'y': ycenter - num}
        lrc = {'x': xcenter + num, 'y': ycenter + num}
        draw = ImageDraw.Draw(image)
        draw.line((llc['x'], llc['y'], urc['x'], urc['y']),
                  fill=color, width=10)

        draw.line((ulc['x'], ulc['y'], lrc['x'], lrc['y']),
                  fill=color, width=10)

        return (image)

    @classmethod
    def plot_decayed(cls, image, tooth, piece_center, status):
        x, y = piece_center
        filling = (0, 0, 255)  # blue
        decayed = (255, 0, 0)  # red

        # Pick the color for decay of filling
        if status['ts'] == 'D':
            color = decayed
        else:
            color = filling

        position = (x, y)  # Center of the tooth
        draw = ImageDraw.Draw(image)

        tregions = status.copy()
        tregions.pop('ts')  # Delete ts element and focus on the tooth areas

        # Set the section of the filling / decay
        # Maxillar / upper region
        num = cls.x_distance/(2*1.414)

        if (tooth in range(11, 28) or tooth in range(51, 65)):
            for key in tregions.keys():
                if (key in ['o', 'i']):  # Occlusal or Incisal
                    position = (x, y)  # Center of the tooth
                if (key == 'v'):  # Vestibular
                    position = (x, y - num)
                if (key == 'p'):  # Palatine
                    position = (x, y + num)
                if (key == 'd'):  # Distal
                    position = (x - num, y)
                if (key == 'm'):  # Mesial
                    position = (x + num, y)

                ImageDraw.floodfill(image, xy=position, value=color, thresh=200)

        # Mandibular / lower region
        if (tooth in range(31, 48) or tooth in range(71, 85)):
            for key in tregions.keys():
                if (key in ['o', 'i']):  # Occlusal or Incisal
                    position = (x, y)  # Center of the tooth
                if (key == 'l'):  # Lingual
                    position = (x, y - num)
                if (key == 'v'):  # Vestibular
                    position = (x, y + num)
                if (key == 'm'):  # Mesial
                    position = (x - num, y)
                if (key == 'd'):  # Distal
                    position = (x + num, y)

                ImageDraw.floodfill(image, xy=position, value=color, thresh=200)

        return (image)

    @classmethod
    def plot_odontogram(cls, patient):

        image = Image.new('RGB', cls.image_size, (255, 255, 255))

        dschema1 = json.loads(patient.dental_schema or "{}")

        if patient.use_primary_schema:
            dschema2 = json.loads(patient.dental_schema_primary or "{}")
        else:
            dschema2 = {}

        dschema = {**dschema1, **dschema2}

        cls.plot_teeth(image, dschema)

        for tooth, values in dschema.items():
            # Decayed or filled tooth
            # Plot it first to avoid wrong surface filling if overlapping with
            # other symbols
            if (values['ts'] in ('D', 'F')):
                status = dschema[tooth]  # Get all the keys (ts, o, m, d, ...)
                cls.plot_decayed(image, int(tooth), cls.pieces[tooth], status)

            # Missing or set for extraction tooth
            if (values['ts'] in ('M', 'E')):
                status = values['ts']
                cls.plot_extraction(image, cls.pieces[tooth], status)

        holder = io.BytesIO()
        image.save(holder, 'png')
        image_png = holder.getvalue()
        holder.close()
        return (image_png)

    @classmethod
    def get_context(cls, records, header, data):
        context = super(Odontogram, cls).get_context(
            records, header, data)

        context['get_patient_odontogram'] = cls.plot_odontogram

        return context
