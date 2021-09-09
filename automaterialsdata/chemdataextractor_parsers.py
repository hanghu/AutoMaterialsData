import chemdataextractor as cde
from chemdataextractor import Document
from chemdataextractor.reader import acs,base,cssp,HtmlReader,NlmXmlReader,PdfReader,RscHtmlReader,XmlReader
from chemdataextractor.model import Compound, UvvisSpectrum, UvvisPeak, BaseModel, StringType, ListType, ModelType
from chemdataextractor.parse.common import hyphen, lbrct, dt, rbrct
from chemdataextractor.parse.base import BaseParser
from chemdataextractor.utils import first

from chemdataextractor.parse.actions import strip_stop, merge, join
from chemdataextractor.parse.elements import W, I, T, R, Optional, ZeroOrMore, OneOrMore, Or, And, Not, Any
from chemdataextractor.parse.cem import chemical_name, cem, chemical_label, lenient_chemical_label, solvent_name
from chemdataextractor.doc import Paragraph, Sentence, Caption, Figure,Table, Heading
from chemdataextractor.doc.table import Table, Cell

from functools import reduce

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
COMMON_TEXT = R('(\w+)?\D(\D+)+(\w+)?').hide()
#COMMON_TEXT = R('\w+').hide()
NUMERICAL_VALUE = (R(u'\d+(\.\d*)?') | R(u'\b([0-9]|[1-9][0-9]|100)\b'))(u'value')
LOGIC_INDICATOR = (W('=') | W('of') | W('was') | W('is') | W('being') | 
                   W('at') | (W('up') + W('to')) | W('average') | W('as') ).hide() 
                   
#                   W('reached') | W('reach') | W('reaches') |
#                   W('result')  | W('resulted') | W('results')).hide() 

#RANGE_INDICATOR = (I('about') | I('around') | I('roughly') |
#                   Optional(I('in') + I('the') + I('range') + Optional(I('of')) ).hide()    
                
#JOINED_RANGE = R('^[\+\-–−]?\d+(\.\d+)?[\-–−~∼˜]\d+(\.\d+)?$')('value').add_action(merge)
#SPACED_RANGE = (R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(units).hide() + 
#                (R('^[\-–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?$') 
#                 | R('^[\+\-–−]\d+(\.\d+)?$')))('value').add_action(merge)
#TO_RANGE = (R('^[\+\-–−]?\d+(\.\d+)?$') + Optional(units).hide() + 
#            (I('to') + R('^[\+\-–−]?\d+(\.\d+)?$') 
#             | R('^[\+\-–−]\d+(\.\d+)?$')))('value').add_action(join)

def generate_grammers_to_parse_numerical_properties(names, abbrvs, units, notation=None):
    
    if notation is None: notation = u'numerical_property'
    
    lambda_or = lambda a, b: a | b
    
    names  = reduce(lambda_or, names)
    abbrvs = reduce(lambda_or, abbrvs)
    properties = ((names + Optional(lbrct + abbrvs + rbrct)) | abbrvs)(u'name')                 
    units  = reduce(lambda_or, units)(u'unit')
    
    grammers = []
    
    # 1 
    grammers.append((properties + LOGIC_INDICATOR 
                     + NUMERICAL_VALUE + Optional(units))((notation)))
    #grammers.append((properties + LOGIC_INDICATOR + NUMERICAL_VALUE + Optional(units))(notation))
    
    # 2
    grammers.append((properties + Optional(lbrct) + NUMERICAL_VALUE + Optional(units) + Optional(rbrct))((notation)))
    
    return reduce(lambda_or, grammers)
    

class NumericalProperty(BaseModel):
    name = StringType()
    value = StringType()
    unit = StringType()
    
class OPVPropertyParser(BaseParser):
   
    # define property abbrevations / names 
    
    pce_name  = (I(u'power') + I(u'conversion') + I(u'efficiency')) | I(u'efficiency')
    ff_name   = I(u'fill') + I(u'factor')             
    voc_name  = I(u'open') + I(u'circuit') + I(u'voltage')
    names = [pce_name, ff_name, voc_name]
                   
    pce_abbrv = I(u'pce') | I(u'PCEs')
    voc_abbrv = I(u'voc')
    ff_abbrv  = I(u'ff')
    abbrvs = [pce_abbrv, ff_abbrv, voc_abbrv]
    
    #define units
    pce_units =  W(u'%') | I(u'percent') | I(u'percentage')
    ff_units  =  W(u'%') | I(u'percent') | I(u'percentage')
    voc_units =  I(u'v') | I(u'volt') | I(u'volts') | I(u'voltage') | I(u'voltage') 
    units = [pce_units,  ff_units,  voc_units]
    
    root = generate_grammers_to_parse_numerical_properties(names, abbrvs, units, notation=u'opv_property')
    
    def interpret(self, result, start, end):
        print(result)
        compound = Compound(
            opv_property=[
                NumericalProperty(
                    name =first(result.xpath('./name/text()')),
                    value=first(result.xpath('./value/text()')),
                    unit =first(result.xpath('./unit/text()'))
                )
            ]
        )
        yield compound
    

# PCE Parser
class Pce(BaseModel):
    value = StringType()
    units = StringType()

class PceParser(BaseParser):
    
    units = (W(u'%') | I(u'percent'))(u'units')
    abbrv_prefix = (I(u'PCE') | I(u'PCEs') | I(u'pce')).hide()
    words_pref = (I(u'power') + I(u'conversion') + I(u'efficiency')).hide()
    hyphanated_pref = (I(u'power') + I(u'-') + I('conversion') + I(u'efficiency')| I(u'efﬁciency')).hide()
    prefix = Optional(I('a')).hide() \
        + (Optional(lbrct) + abbrv_prefix + Optional(rbrct) | I('power') + Optional(I('conversion')) \
        + Optional((I('efficiency') | I(u'efﬁciency') | I('range') | words_pref)) \
        + Optional((I('temperature') | I('range')))).hide() \
        + Optional(lbrct + W('PCE') + rbrct) \
        + Optional (W('thus')) \
        + Optional (W('reached')) \
        + Optional (W('result')) \
        + Optional (W('up')) \
        + Optional(W('=') | W('¼') | I('of') | I('was') | I('is') | I('average') | I('high') | I('at') | I('to')).hide() \
        + Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') | ('around') | I('%')).hide()
    
    pce_first  = (words_pref + (Optional(lbrct) + abbrv_prefix + Optional(rbrct)) 
                  + ZeroOrMore(COMMON_TEXT) + NUMERICAL_VALUE + Optional(units))(u'pce')

    pce_second = (prefix + NUMERICAL_VALUE + Optional(units))(u'pce')
   
    pce_pattern = pce_first | pce_second
    root = pce_pattern
    
    def interpret(self, result, start, end):
        print(result)
        compound = Compound(
            pce_pattern=[
                Pce(
                    value=first(result.xpath('./value/text()')),
                    units=first(result.xpath('./units/text()'))
                )
            ]
        )
        yield compound

# Fill factor parser
class Ff(BaseModel):
    value = StringType()
    units = StringType()
    

class FfParser(BaseParser):
    units = (W(u'%') | I(u'percent'))(u'units') 
    abbrv_prefix = (I(u'FF') | I(u'ff')).hide()
    words_pref = (I(u'fill') | I(u'fill') + I(u'factor')).hide()
    hyphanated_pref = (I(u'fill') | I(u'fill') + I(u'-') + I('factor')).hide()
    
    prefix = Optional(I('a')).hide() \
        + (Optional(lbrct) + W('FF') + Optional(rbrct) 
           | I('fill') | I('ﬁll') + Optional(I('factor'))).hide() \
        + Optional(lbrct + W('FF') + rbrct) \
        + Optional(W('=') | W('¼') | W(';') | W(',') | I('of') | I('was') | I('is') | I('at')).hide() \
        + Optional(I('in') + I('the') + I('range') + Optional(I('of')) | I('about') 
                   | I('average') | I('to') |I('around')| I ('%')).hide()

    ff_first  = (words_pref + (Optional(lbrct) + abbrv_prefix + Optional(rbrct)) 
                 + ZeroOrMore(COMMON_TEXT) + NUMERICAL_VALUE + Optional(units))(u'ff')
    ff_second = (prefix + NUMERICAL_VALUE + Optional(units))(u'ff')
    ff_third = (abbrv_prefix + prefix + NUMERICAL_VALUE)(u'ff')
    ff_pattern = ff_first | ff_second | ff_third
    
    root = ff_pattern

    def interpret(self, result, start, end):
        compound = Compound(
            ff_pattern=[
                Ff(
                    value=first(result.xpath('./value/text()')),
                    units=first(result.xpath('./units/text()'))
                )
            ]
        )
        yield compound
    

def parse_ff(list_of_sentences):
    
    #Takes a list of sentences and parses for quantified PCE
    #information and relationships to chemicals/chemical labels
    
    Sentence.parsers.append(FfParser())

    cde_senteces = [Sentence(sent).records.serialize()
                    for sent in list_of_sentences]
    return cde_senteces

# Voc Parser
class Voc(BaseModel):
    value = StringType()
    units = StringType()

class VocParser(BaseParser):

    units = (W(u'V') | I(u'v') | I(u'volt') | I(u'volts'))(u'units').add_action(merge)
    abbrv_prefix = (I(u'Voc') | I(u'voc') | I(u'VOC')).hide()
    words_pref = (I(u'open') + I(u'circuit') + I(u'voltage')).hide()
    hyphanated_pref = (I(u'open') + I(u'-') + I('circuit') + I(u'voltage')).hide()

    prefix = Optional(I('a')).hide() \
        + (Optional(lbrct) + I('Voc') + Optional(rbrct) | Optional(I('open')) 
           + Optional(I('circuit')) + Optional((I('voltage')))).hide() \
        + Optional(lbrct + W('Voc') + rbrct) \
        + Optional(W('=') | W('¼') | I('of') | I('was') | I('is') | I('at')).hide() \
        + Optional(I('in') + I('the') + I('range') + Optional(I('of')) 
                   | I('about') | I('average') | ('around') | I('V')).hide()

    voc_first  = (words_pref + (Optional(lbrct) + abbrv_prefix + Optional(rbrct)) 
                  + ZeroOrMore(COMMON_TEXT) + Optional(lbrct) + NUMERICAL_VALUE 
                  + Optional(rbrct) + units)(u'voc')
    voc_second = (prefix + Optional(lbrct) + NUMERICAL_VALUE 
                  + Optional(rbrct) + units)(u'voc')
    voc_pattern = voc_first | voc_second
    root = voc_pattern

    def interpret(self, result, start, end):
        compound = Compound(
            voc_pattern=[
                Voc(
                    value=first(result.xpath('./value/text()')),
                    units=first(result.xpath('./units/text()'))
                )
            ]
        )
        yield compound

    
    
    