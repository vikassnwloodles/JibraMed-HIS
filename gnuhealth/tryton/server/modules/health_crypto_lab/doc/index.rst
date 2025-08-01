.. SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
.. SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
..
.. SPDX-License-Identifier: CC-BY-SA-4.0

GNU Health Cryptography Module for Laboratory
#############################################

This module depends on the main health_crypto module.

This module intends to enhance the concepts of confidenciality, integrity and non-repudiation in GNU Health.

The health_crypto module will provide the following functionality :

    Document Serialization
    Document hashing (MD)
    Document signing
    Document verification
    Document encryption

The module will work on records from models that will need this functionality such as prescription, patient evaluations, surgeries or lab tests.

The Serialization process will include the information in a predefined format (JSON) and encoding (UTF8).

There will be a field that will contain the Message digest of the serialization process, and that will check for any changes.

The signing process will be upon that Message Digest field, whereas the encryption process will work on row or column level.

Public key / asymmetric cryptography will be used for signing the documents.

