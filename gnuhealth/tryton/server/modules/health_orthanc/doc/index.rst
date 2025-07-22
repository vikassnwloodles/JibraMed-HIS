.. SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
..
.. SPDX-License-Identifier: CC-BY-SA-4.0

GNU Health Orthanc Package 
##########################

This package provides GNU Health integration to the
Orthanc PACS server.

Worklists
#########

Setup worklist template
@@@@@@@@@@@@@@@@@@@@@@@@

1. Open: Health > Configuration > Orthanc > Worklist template
2. Set encoding field.

   At the moment, it is used to generate dump2dcm dumpfile-in text
   file by script/orthanc/update_worklists_database.py

   this field should work well with (0008,0005) dicom tag of worklist
   template, for example: if (0008,0005) = [ISO_IR 192], encoding
   should be "utf-8", if (0008,0005) = [GBK], encoding should be
   "gbk".

3. Create worklist templates.

   In most situation, a type of modality should to create a template,
   template use python genshi syntax and used to generate dump2dcm
   dumpfile-in text file (dump2dcm is a command of dcmtk package).

   At the moment, template support the following variables and most of
   them use dicom tag nicknames.
   
   1. AccessionNumber
   2. RequestedProcedureID
   3. StudyInstanceUID
   4. PatientName
   5. PatientID
   6. PatientAge
   7. PatientBirthDate
   8. PatientSex
   9. RequestingPhysician
   10. RequestingService
   11. ReferringPhysicianName
   12. InstitutionName
   13. RequestedProcedureDescription
   14. ScheduledProcedureStepStartDate
   15. ScheduledProcedureStepStartTime
   16. TimezoneOffsetFromUTC
   17. ScheduledStationAETitle
   18. Modality

   Two special variables are supported:

   1. my: this variable refer to 'gnuhealth.imaging.test.request'
      model.
   2. MergeID: Merge Id is used to merge orthanc studies to health
      imaging result, in most situation, we do not use this variable
      for we use StudyInstanceUID as merge id, if modality workstation
      has bug and can not handle StudyInstanceUID properly, user can
      use other dicom tags to tranfer merge id, more details can be
      found in *get_merge_id* method in gnuhealth.orthanc.study
      model. but, this is a hack way, do not use unless absolutely
      necessary.

   if user would like to support new worklist template variables,
   extend *get_worklist_template_data* method in
   gnuhealth.imaging.test.request model is a good way.

   Note: Creating a template for a modality may need more work, user
   should know which tags should be set up properly with the help of
   Dicom Conformance Statement of this modality, user can use wlmscpfs
   of dcmtk to create a test worklist server to know which tags will
   be sent to worklist server from modality. user can try
   script/orthanc/worklists_service_demo.sh too.

4. Setup fields of Medical Imaging Studies. 

   (Health > Configuration > Medical Imaging > Medical Imaging Studies)

   1. Type: the code of this field is used as Modality (0008,0060) tag
      of worklist, so make sure its code use the value of Dicom
      Modality (0008,0060) tag, more details can be found at:
      https://www.dicomlibrary.com/dicom/modality/
   2. AETitle: this field is used as ScheduledStationAETitle
      (0040,0001) tag of worklist.
   3. Worklist Template.

View worklist text of a imaging request
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

1. Open form: Medical Imaging > Medical Imaging Requests
2. Click worklist field of a request

Generate worklists wl files
@@@@@@@@@@@@@@@@@@@@@@@@@@@

1. Let orthanc enable worklists plugin, please read:
   https://book.orthanc-server.com/plugins/worklists-plugin.html

2. Install dcmtk package in orthanc machine.

3. Run the below command in orthanc machine, it will get worklist text
   from gnuhealth and generate a wl file (dicom file used by orthanc
   worklist server) with the help of dump2dcm command in dcmtk
   package, -w argument should set to the Database config of worklists
   plugin.

       script/orthanc/update_worklists_database.py -d <gnuhealth-db> -u <gnuhealth-user> -P <password> -w <orthanc-worklist-db-dir>

   More arguments can be found by run:

       script/orthanc/update_worklists_database.py -h


Sync orthanc studies to gnuhealth imaging results.
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

Just run script/orthanc/sync_orthanc_server.py
   

