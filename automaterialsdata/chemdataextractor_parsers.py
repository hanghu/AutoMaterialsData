import chemdataextractor as cde
from chemdataextractor import Document
from chemdataextractor.reader import acs,base,cssp,HtmlReader,NlmXmlReader,PdfReader,RscHtmlReader,XmlReader
from chemdataextractor.model import Compound, UvvisSpectrum, UvvisPeak, BaseModel, StringType, ListType, ModelType
from chemdataextractor.parse.common import hyphen, lbrct, dt, rbrct, colon, delim, quote
from chemdataextractor.parse.base import BaseParser
from chemdataextractor.utils import first

from chemdataextractor.parse.actions import strip_stop, merge, join
from chemdataextractor.parse.elements import W, I, T, R, Optional, ZeroOrMore, OneOrMore, Or, And, Not, Any
from chemdataextractor.parse.cem import chemical_name, cem, chemical_label, lenient_chemical_label, solvent_name
from chemdataextractor.doc import Paragraph, Sentence, Caption, Figure,Table, Heading
from chemdataextractor.doc.table import Table, Cell

from functools import reduce
import re

"""
Notes from ChemDataExtractor:

W ... match text exactly
I ... match case-incensitive text
T ... match tags
R ... match regex

lbrct ... left bracket
rbrct ... right bracket
"""

# Pattern Helpers
COMMON_TEXT = R('^\w+$').hide()
NUMERICAL_VALUE = (R(u'^\d+(\.\d*)?$'))(u'value')
LOGIC_PATTERN = 'was|is|be(ing)?|result(s|ed)?|reach(es|ed)?|increase(s|d)?|decrease(s|d)?|yeild(s|ed)?'
LOGIC_WORDS = R('(' + LOGIC_PATTERN + ')').hide()
NONLOGIC_WORDS  =  R('^(?!'+ LOGIC_PATTERN + ')([\w\d\(\),:\-]+)$').hide()
NONLOGIC_WORDS_AND_NOT_NUMBER  =  R('^(?!'+ LOGIC_PATTERN + '|\d+)(\w+)$').hide()
DEGREE_WORDS = R('^(to|about|around|approximately|roughly|~)$').hide()
LOGIC_INDICATORS = R('^(\)|\(|=|:|of|as)$').hide()

#JOINED_RANGE = R('^[\+\-–−]?\d+(\.\d+)?[\-–−~∼˜]\d+(\.\d+)?$')('value').add_action(merge)
#SPACED_RANGE = (R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(units).hide() + 
#                (R('^[\-–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?$') 
#                 | R('^[\+\-–−]\d+(\.\d+)?$')))('value').add_action(merge)
#TO_RANGE = (R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(units).hide() + 
#            (I('to') + R('^[\+\-–−]?\d+(\.\d+)?$') 
#             | R('^[\+\-–−]\d+(\.\d+)?$')))('value').add_action(join)

def generate_grammars_to_parse_numerical_properties(names, abbrvs, units, notation=None):
    
    if notation is None: notation = u'numerical_property'
    
    lambda_or = lambda a, b: a | b
    
    names  = reduce(lambda_or, names)
    abbrvs = reduce(lambda_or, abbrvs)
    property_names = ((names + Optional(lbrct + abbrvs + rbrct)) | abbrvs)(u'name')                 
    units  = reduce(lambda_or, units)(u'unit')
    
    grammars = []
    
    # 1 A ... is .... B 
    grammars.append((property_names + ZeroOrMore(NONLOGIC_WORDS) + LOGIC_WORDS + Optional(DEGREE_WORDS)
                     + NUMERICAL_VALUE + Optional(units))(notation))
    
    # 2 A =/of B
    grammars.append((property_names + Optional(R('^value(s)$')).hide() + Optional(LOGIC_INDICATORS) + Optional(DEGREE_WORDS) 
                     + NUMERICAL_VALUE + Optional(units))(notation))
    
    # 3 A as ? as B
    grammars.append((property_names + I('as').hide() + R('(?!as)').hide() + I('as').hide()
                     + NUMERICAL_VALUE + Optional(units))(notation))
    
    return reduce(lambda_or, grammars)
  

class NumericalProperty(BaseModel):
    name  = StringType()
    value = StringType()
    unit  = StringType()
    
class OPVPropertyParser(BaseParser):
   
    # define property abbrevations / names 
    
    pce_name  = Optional(I('power') + Optional(hyphen) + I(u'conversion')) + I(u'efficiency') 
    ff_name   = I('fill') + I('factor')             
    voc_name  = I('open') + Optional(hyphen) + I(u'circuit')  + I(u'voltage')
    jsc_name  = I('short') + Optional(hyphen) + I(u'circuit') + I(u'current') | I(u'current') + I(u'density')
    names = [pce_name, ff_name, voc_name, jsc_name]
                   
    pce_abbrv = I(u'pce') | I(u'PCEs') | W('η')
    voc_abbrv = I(u'voc')
    ff_abbrv  = I(u'ff')
    jsc_abbrv = I(u'jsc') | I(u'isc')
    abbrvs = [pce_abbrv, ff_abbrv, voc_abbrv, jsc_abbrv]
    
    #define units
    pce_units = W(u'%') | R(u'^percent(age)?$') 
    ff_units  = W(u'%') | R(u'^percent(age)?$') 
    voc_units = R(u'^v(olt(s|age(s)?)?)?$', re.I)
    jsc_units1 = R('^(m)?A$', re.I) + W('/') + R('^(c|m)?m2$', re.I)
    jsc_units2 = R('^(m)?A(c|m)?m(2|-|−)?2$', re.I) | ( R('^(m)?A$', re.I) + R('^(c|m)?m(2|-|−)?2$', re.I))
    jsc_units3 = (R('^(m)?A(c|m)?m$', re.I) | (R('^(m)?A$', re.I) + R('^(c|m)?m$', re.I))) + Optional((hyphen + W('2')) | W('(-|−)2'))
    units = [pce_units,  ff_units,  voc_units, jsc_units1, jsc_units2, jsc_units3]
    
    root = generate_grammars_to_parse_numerical_properties(names, abbrvs, units, notation=u'opv_property')
    
    unique_name_parsers = {'PCE': pce_name | pce_abbrv,
                           'JSC': jsc_name | jsc_abbrv,
                           'VOC': voc_name | voc_abbrv,
                           'FF':  ff_name  | ff_abbrv}
    
    @staticmethod
    def find_unique_name(name):
        
        for key, parser in OPVPropertyParser.unique_name_parsers.items():
            try:
                tagged_name = [[ n, key] for n in name.split()]
                if parser.parse(tagged_name, 0):
                    name = key
                    break
            except:
                pass
            
        return name
    
    def interpret(self, result, start, end):
        compound = Compound(
            opv_property=[
                NumericalProperty(
                    name = ' '.join(result.xpath('./name/text()')),
                    value= first(result.xpath('./value/text()')),
                    unit = ''.join(result.xpath('./unit/text()'))
                )
            ]
        )
        yield compound


class OPVMaterials(BaseModel):
    name  = StringType()
    
class OPVMaterialsParser(BaseParser):
    
    #root = R('^(?!VOC|JSC|ISC|PCE|FF|[0-9]+|[A-Z][a-z]*$|[a-z]+$|.{0,4}$)')(u'opv_mat')
    
    root = R('^(?!VOC|JSC|ISC|PCE|FF|[A-Z]$|[0-9]+$)([pA-Z0-9]{4,}[a-zA-Z0-9\-\(\)\[\]\:\,]*[\.]?$)')(u'opv_mat') + \
        ZeroOrMore((hyphen | quote | R('^[:\[\]\(\)\{\}/]$')) + \
                   R('^[a-zA-Z0-9\-\(\)\[\]\:\,]+[\.]?$')(u'opv_mat'))
    
    def interpret(self, result, start, end):
        if isinstance(result, list):
            opv_name = ''.join([part.text for part in result])
        else:
            opv_name = result.text
        
        if opv_name[-1] == '.': opv_name = opv_name[:-1]
        
        compound = Compound(
            opv_materials=[
                OPVMaterials(
                    name = opv_name
                )
            ]
        )
        yield compound

 