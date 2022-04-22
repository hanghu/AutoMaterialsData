import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import re
import copy
import os

def clean_excess_space(string_list):
    new_list = []
    for entry in string_list:
        if re.match(r"^[\s\n]*$", entry):
            new_list.append('')  
        elif entry:
            new_list.append(re.sub(r"""\n\s{1,}""", " ", entry))
        else: 
            new_list.append(entry)
    
    return new_list

def get_all_files_with_extension(path, extension):
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    xml_files = list(filter(lambda f: f.endswith(extension), files))
    return [os.path.join(path, f) for f in xml_files]

def get_tables_from_xml_file(filepath):
    tree = ET.parse(filepath)
    root = ET.tostring(tree.getroot())
    content_list = []
    total_list = []
    sub_header = []
    all_tables = []
    all_headers = []
    counter = 0
    table_lists = tree.iter('{http://www.elsevier.com/xml/common/dtd}table')
    for table in table_lists:
        
        # get the head column
        header = []
        lst = table.iter('{http://www.elsevier.com/xml/common/cals/dtd}thead')
        for tags in lst:
            rows = tags.findall('{http://www.elsevier.com/xml/common/cals/dtd}row')
            entry_list = rows[0].findall('{http://www.elsevier.com/xml/common/dtd}entry')
            for every_entry in entry_list:
                total = ''
                for x in every_entry.itertext():
                    total = total + x
                total_list.append(total)
                if 'nameend' in every_entry.attrib.keys():
                    if every_entry.attrib['nameend'][:3] == 'col':
                        namest = int(every_entry.attrib['namest'][3:])
                        nameend = int(every_entry.attrib['nameend'][3:])
                        total_list = total_list + ['']*(nameend - namest)
            
            total_list = clean_excess_space(total_list)
            header.append(total_list)
            
            if len(rows) == 2:
                entry_list = rows[1].findall('{http://www.elsevier.com/xml/common/dtd}entry')
                for more_entry in entry_list: 
                    total2 = ''
                    for y in more_entry.itertext():
                        total2 =  total2 + y 
                    sub_header.append(total2)
                sub_header = clean_excess_space(sub_header)
                content_list.append(sub_header)
                header.append(sub_header)
            
        lst2 = table.iter('{http://www.elsevier.com/xml/common/cals/dtd}tbody')
        for data in lst2:
            rows = data.findall('{http://www.elsevier.com/xml/common/cals/dtd}row')
            for row in rows: 
                entry_list = row.findall('{http://www.elsevier.com/xml/common/dtd}entry')
                row_data = []
                for additional_entry in entry_list:
                    row_data_2 = ''
                    for t in additional_entry.itertext():
                        row_data_2 = row_data_2 + t
                    row_data.append(row_data_2)
                content_list.append(clean_excess_space(row_data))
        
        rows = content_list
        df = pd.DataFrame(rows, columns = total_list)
        #print(df)
        #df.to_csv('Table' + str(counter) + '.csv',encoding='utf-8')
        counter = counter + 1
        content_list.clear()
        all_headers.append(copy.deepcopy(header))
        total_list.clear()
        sub_header.clear()
        all_tables.append(df)
    
    return (all_tables, all_headers)

def reorder_headers(table_headers):
    return list(zip(*table_headers))

def match_string(patterns, strings):
    if type(strings) == tuple:
        try:
            final_strs = [''.join(x) for x in strings]
        except TypeError:
            return False
    else: 
        final_strs = strings 
    
    upper_ptns = list(map(str.upper, patterns))
    upper_strs = [str.upper(str_i.replace(" ", "")) for str_i in final_strs]
    return any([any([re.search(p, s) for p in upper_ptns]) for s in upper_strs])

def gather_properties_from_full_table(table, table_header, searching_patterns, output_headers):
    properties_table = pd.DataFrame()
    r_headers = reorder_headers(table_header)
    
    matched_cols = []
    matched_col_names = []
    for p, h in zip(searching_patterns, output_headers):
        for col in range(len(r_headers)):
            if match_string(p, r_headers[col]):
                matched_cols.append(col)
                matched_col_names.append(h)
                break
    
    if (not matched_cols): return None

    row_count = -1
    properties_table = pd.DataFrame(columns=[0,1,2]+output_headers)
    for row in range(table.shape[0]):    
        if not any(table.iloc[row, :].values):
            continue

        row_count += 1
        properties_table.loc[row_count] = ''

        properties_table[0][row_count] = table.iloc[row, 0]
        if not properties_table[0][row_count]:
            properties_table[1][row_count] = table.iloc[row, 1]
            if not properties_table[1][row_count]:
                properties_table[2][row_count] = table.iloc[row, 2]

        shift = 0
        while not table.iloc[row, :].values[shift-1]:
            shift -= 1

        for col, col_name in zip(matched_cols, matched_col_names):
            properties_table[col_name][row_count] = table.iloc[row, col+shift]
    
    return properties_table
    



















