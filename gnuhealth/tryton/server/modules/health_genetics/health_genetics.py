# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                       HEALTH GENETICS package                         #
#                  health_genetics.py: main module                      #
#########################################################################
from trytond import backend
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pyson import Eval
from trytond.pool import Pool
from uuid import uuid4
from trytond.modules.health.core import (get_institution,
                                         format_years_months_days)
from trytond.transaction import Transaction

__all__ = ['Gene', 'ProteinDisease', 'GeneVariant',
           'GeneVariantPhenotype',
           'PatientGeneticRisk', 'FamilyDiseases', 'GnuHealthPatient']


class Gene(ModelSQL, ModelView):
    'Genes'
    __name__ = 'gnuhealth.gene'

    name = fields.Char(
        'Symbol', help='Symbol', required=True, select=True)

    aliases = fields.Char(
        'Aliases', help='Symbol aliases')

    name_aliases = fields.Char(
        'Name Aliases', help='Name aliases')

    hgnc_id = fields.Char(
        'HGNC ID', help='HUGO Gene Nomenclature Committee identifier',
        required=True, select=True)

    gene_type = fields.Selection([
        (None, ''),
        ('protein_coding', 'protein-coding gene'),
        ('ncrna_long_non_coding_rna', 'ncRNA: long non-coding RNA'),
        ('ncrna_y_rna', 'ncRNA: Y RNA'),
        ('ncrna_cluster_rna', 'ncRNA: cluster RNA'),
        ('ncrna_micro_rna', 'ncRNA: micro RNA'),
        ('ncrna_misc_rna', 'ncRNA: misc RNA'),
        ('ncrna_ribosomal_rna', 'ncRNA: ribosomal RNA'),
        ('ncrna_small_nuclear_rna', 'ncRNA: small nuclear RNA'),
        ('ncrna_small_nucleolar_rna', 'ncRNA: small nucleolar RNA'),
        ('ncrna_transfer_rna', 'ncRNA: transfer RNA'),
        ('ncrna_vault_rna', 'ncRNA: vault RNA'),
        ('pseudogene_pseudogene', 'pseudogene: pseudogene'),
        ('pseudogene_tcell_receptor',
            'pseudogene: T cell receptor pseudogene'),
        ('pseudogene_immunoglobulin', 'pseudogene: immunoglobulin pseudogene'),
        ('other_tcell_receptor_gene', 'other: T cell receptor gene'),
        ('other_complex_locus_constituent',
            'other: complex locus constituent'),
        ('other_endogenous_retrovirus', 'other: endogenous retrovirus'),
        ('other_fragile_site', 'other: fragile site'),
        ('other_immunoglobulin_gene', 'other: immunoglobulin gene'),
        ('other_readthrough', 'other: readthrough'),
        ('other_region', 'other: biological region'),
        ('other_virus_integration_site', 'other: virus integration site'),
        ('other_unknown', 'other: unknown'),
        ], 'Gene type', help="Locus in the form of group:type",
        sort=False, select=True)

    protein_name = fields.Char('Protein Code',
                               help="Encoding Protein Code,"
                               " such as UniProt protein name",
                               select=True)
    # Do not translate the gene long name. Having the gene long name
    # description in English is OK in the scientific community, and it
    # will make the update process much faster, and don't overload the
    # translation server at Weblate. more details:
    # https://savannah.gnu.org/bugs/?64542
    long_name = fields.Char('Official Name', translate=False)
    gene_id = fields.Char('Entrez Gene ID',
                          help="Gene ID from NCBI Entrez database.",
                          select=True)
    chromosome = fields.Char('Chromosome',
                             help="Name of the affected chromosome",
                             select=True)
    location = fields.Char('Location', help="Locus of the chromosome")

    ensembl_id = fields.Char("Ensembl ID")
    refseq_accession = fields.Char("RefSeq", help="RefSeq Accession ID")
    omim_id = fields.Char("OMIM ID")

    info = fields.Text('Information', help="Extra Information")
    variants = fields.One2Many('gnuhealth.gene.variant', 'name',
                               'Variants')

    protein_uri = fields.Function(fields.Char("Protein URI"),
                                  'get_protein_uri')

    def get_protein_uri(self, name):
        ret_url = ''
        if (self.protein_name):
            ret_url = 'http://www.uniprot.org/uniprot/' + \
                str(self.protein_name)
        return ret_url

    @classmethod
    def __setup__(cls):
        super(Gene, cls).__setup__()

        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.hgnc_id),
                'The official identifier must be unique'),
            ]

    def get_rec_name(self, name):
        protein = ''
        if self.protein_name:
            protein = ' (' + self.protein_name + ') '
        return self.name + protein + ':' + self.long_name

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
                ('name',) + tuple(clause[1:]),
                ('long_name',) + tuple(clause[1:]),
                ]

    @classmethod
    def __register__(cls, module):
        # Migration from 4.2:
        # rename gnuhealth.disease.gene to gnuhealth.gene
        backend.TableHandler.table_rename('gnuhealth_disease_gene', cls._table)

        # Update the data field from gnuhealth.disease.gene to gnuhealth.gene
        cursor = Transaction().connection.cursor()
        cursor.execute("""
            UPDATE ir_model_data SET model = 'gnuhealth.gene'
            WHERE model = 'gnuhealth.disease.gene'
            """)
        super().__register__(module)


class ProteinDisease(ModelSQL, ModelView):
    'Protein related disorders'
    __name__ = 'gnuhealth.protein.disease'

    name = fields.Char('Disease', required=True, select=True,
                       help="Uniprot Disease Code")

    disease_name = fields.Char('Disease name', translate=True)
    acronym = fields.Char('Mnemonic', required=True, select=True,
                          help="Disease acronym / mnemonics")

    disease_uri = fields.Function(fields.Char("Disease URI"),
                                  'get_disease_uri')

    mim_reference = fields.Char('MIM', help="MIM -"
                                "Mendelian Inheritance in Man- DB reference")

    gene_variant = fields.One2Many('gnuhealth.gene.variant.phenotype',
                                   'phenotype',
                                   'Natural Variant',
                                   help="Natural variants "
                                        "involved in this condition")

    keywords = fields.Char('Keywords', select=True)

    xrefs = fields.Char('Xrefs', help="Cross references")

    inheritance_pattern = fields.Selection([
        (None, ''),
        ('ad', 'Autosomic dominant'),
        ('ar', 'Autosomic recessive'),
        ('x', 'X-Linked'),
        ('y', 'Y-Linked'),
        ('m', 'Mitochondrial'),
        ('c', 'codominance'),
        ], 'Inheritance Pattern', help="Inheritance pattern",
        sort=False, select=True)

    description = fields.Text('Description')

    active = fields.Boolean('Active', help="Whether this code is current."
                            "If you deactivate it, the code will "
                            "no longer show in the"
                            " protein-related diseases")

    @staticmethod
    def default_active():
        return True

    def get_disease_uri(self, name):
        ret_url = ''
        if (self.name):
            ret_url = 'http://www.uniprot.org/diseases/' + \
                str(self.name)
        return ret_url

    @classmethod
    def __setup__(cls):
        super(ProteinDisease, cls).__setup__()

        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.name),
                'The Disease Code  name must be unique'),
            ]

    @classmethod
    def __register__(cls, module):
        # Migration from 4.2:
        # rename dominance field to inheritance_pattern
        table_h = cls.__table_handler__(module)
        table_h.column_rename('dominance', 'inheritance_pattern')
        super().__register__(module)

    def get_rec_name(self, name):
        return self.name + ':' + self.disease_name

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
                ('name',) + tuple(clause[1:]),
                ('disease_name',) + tuple(clause[1:]),
                ]


class GeneVariant(ModelSQL, ModelView):
    'Natural Variant'
    __name__ = 'gnuhealth.gene.variant'

    name = fields.Many2One('gnuhealth.gene', 'Gene',
                           required=True,
                           help="Gene and protein product (in parenthesis)")
    variant = fields.Char(
        "FTId", help="Variant Feature Identifier (FTId)",
        required=True, select=True)
    protein = fields.Char('Protein ', help='Uniprot Protein ID')
    aa_change = fields.Char('AA Change', help="Amino acid change")

    dbsnp = fields.Char('dbSNP', help='dbSNP ID')

    dbsnp_url = fields.Function(
        fields.Char("Reference SNP",
                    help="Reference SNP (rs) link"), 'get_dbsnp_url')

    significance = fields.Selection([
        (None, ''),
        ('lbb', 'LB/B: Likely benign or benign'),
        ('lpp', 'LP/P: Likely pathogenic or pathogenic'),
        ('us', 'US: Unknown significance'),
        ], 'Significance',
        help="Category related to the clinical significance of the variant",
        sort=False, select=True)

    phenotypes = fields.One2Many('gnuhealth.gene.variant.phenotype', 'variant',
                                 'Phenotypes / Diseases')

    def get_dbsnp_url(self, name):
        url = ''
        if (self.dbsnp):
            url = f'https://www.ncbi.nlm.nih.gov/snp/{str(self.dbsnp)}'
        return url

    @classmethod
    def __setup__(cls):
        super(GeneVariant, cls).__setup__()

        t = cls.__table__()
        cls._sql_constraints = [
            ('variant_unique', Unique(t, t.variant),
                'The variant ID must be unique'),
            ('aa_unique', Unique(t, t.variant, t.aa_change),
                'The amino acid change for the variant already exists'),
            ]

    def get_rec_name(self, name):
        return ' : '.join([self.variant, self.aa_change])

    # Allow to search by gene and variant or amino acid change
    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
                ('name',) + tuple(clause[1:]),
                ('variant',) + tuple(clause[1:]),
                ('aa_change',) + tuple(clause[1:]),
                ('dbsnp',) + tuple(clause[1:]),
                ]


class GeneVariantPhenotype(ModelSQL, ModelView):
    'Variant Phenotypes'
    __name__ = 'gnuhealth.gene.variant.phenotype'

    name = fields.Char('Code', required=True)
    variant = fields.Many2One('gnuhealth.gene.variant', 'Variant',
                              required=True)

    gene = fields.Function(fields.Many2One(
        'gnuhealth.gene', 'Gene & Protein',
        depends=['variant'],
        help="Gene and expressing protein (in parenthesis)"),
        'get_gene',
        searcher='search_gene')

    phenotype = fields.Many2One('gnuhealth.protein.disease', 'Phenotype',
                                required=True)

    def get_gene(self, name):
        if (self.variant):
            return self.variant.name.id

    def get_rec_name(self, name):
        if self.phenotype:
            return self.phenotype.rec_name

    @classmethod
    def search_gene(cls, name, clause):
        res = []
        value = clause[2]
        res.append(('variant.name', clause[1], value))
        return res

    # Allow to search by gene, variant or phenotype
    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
                ('variant',) + tuple(clause[1:]),
                ('phenotype',) + tuple(clause[1:]),
                ('gene',) + tuple(clause[1:]),
                ]

    @classmethod
    def __setup__(cls):
        super(GeneVariantPhenotype, cls).__setup__()

        t = cls.__table__()
        cls._sql_constraints = [
            ('code', Unique(t, t.name),
                'This code already exists'),
                ]


class PatientGeneticRisk(ModelSQL, ModelView):
    'Patient Genetic Information'
    __name__ = 'gnuhealth.patient.genetic.risk'

    patient = fields.Many2One('gnuhealth.patient', 'Patient', select=True)
    disease_gene = fields.Many2One('gnuhealth.gene',
                                   'Gene', required=True)
    natural_variant = fields.Many2One('gnuhealth.gene.variant', 'Variant',
                                      domain=[('name', '=',
                                              Eval('disease_gene'))],
                                      depends=['disease_gene'])

    variant_phenotype = fields.Many2One('gnuhealth.gene.variant.phenotype',
                                        'Phenotype',
                                        domain=[('variant', '=',
                                                Eval('natural_variant'))],
                                        depends=['natural_variant'])

    onset = fields.Integer('Onset', help="Age in years")

    notes = fields.Char("Notes")

    healthprof = fields.Many2One(
        'gnuhealth.healthprofessional', 'Health prof',
        help="Health professional")

    institution = fields.Many2One('gnuhealth.institution', 'Institution')

    @staticmethod
    def default_institution():
        return get_institution()

    @classmethod
    def create_genetics_pol(cls, genetic_info):
        """ Adds an entry in the person Page of Life
            related to this genetic finding
        """
        Pol = Pool().get('gnuhealth.pol')
        pol = []

        vals = {
            'page': str(uuid4()),
            'person': genetic_info.patient.name.id,
            'age': format_years_months_days(
                years=genetic_info.onset, months=0, days=0),
            'federation_account': genetic_info.patient.name.federation_account,
            'page_type': 'medical',
            'medical_context': 'genetics',
            'relevance': 'important',
            'gene': genetic_info.disease_gene.rec_name,
            'natural_variant': genetic_info.natural_variant and
                               genetic_info.natural_variant.aa_change,
            'summary': genetic_info.notes,
            'author': genetic_info.healthprof and
            genetic_info.healthprof.name.rec_name,
            'node': genetic_info.institution and
            genetic_info.institution.name.rec_name
            }
        if (genetic_info.variant_phenotype):
            vals['health_condition_text'] = vals['health_condition_text'] = \
                genetic_info.variant_phenotype.phenotype.rec_name

        pol.append(vals)
        Pol.create(pol)

    @classmethod
    def create(cls, vlist):

        # Execute first the creation of PoL
        genetic_info = super(PatientGeneticRisk, cls).create(vlist)

        cls.create_genetics_pol(genetic_info[0])

        return genetic_info

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
                ('patient',) + tuple(clause[1:]),
                ('disease_gene',) + tuple(clause[1:]),
                ('variant_phenotype',) + tuple(clause[1:]),
                ]


class FamilyDiseases(ModelSQL, ModelView):
    'Family History'
    __name__ = 'gnuhealth.patient.family.diseases'

    patient = fields.Many2One('gnuhealth.patient', 'Patient', select=True)
    name = fields.Many2One('gnuhealth.pathology', 'Condition', required=True)
    xory = fields.Selection([
        (None, ''),
        ('m', 'Maternal'),
        ('f', 'Paternal'),
        ('s', 'Sibling'),
        ], 'Maternal or Paternal', select=True)

    xory_str = xory.translated('xory')

    relative = fields.Selection([
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('aunt', 'Aunt'),
        ('uncle', 'Uncle'),
        ('nephew', 'Nephew'),
        ('niece', 'Niece'),
        ('grandfather', 'Grandfather'),
        ('grandmother', 'Grandmother'),
        ('cousin', 'Cousin'),
        ], 'Relative',
        help='First degree = siblings, mother and father\n'
             'Second degree = Uncles, nephews and Nieces\n'
             'Third degree = Grandparents and cousins',
        required=True)


class GnuHealthPatient (ModelSQL, ModelView):
    """
    Add to the Medical patient_data class (gnuhealth.patient) the genetic
    and family risks"""
    __name__ = 'gnuhealth.patient'

    genetic_risks = fields.One2Many('gnuhealth.patient.genetic.risk',
                                    'patient', 'Genetic Information')
    family_history = fields.One2Many('gnuhealth.patient.family.diseases',
                                     'patient', 'Family History')
