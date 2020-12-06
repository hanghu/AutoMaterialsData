import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
import os 

def get_tables_from_xml_file(path):
    content_list = []
    total_list = []
    sub_header = []
    all_tables = []
    all_files = []
    directory = path
    counter = 0
    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            list_of_files = os.path.join(directory, filename)
        all_files.append(list_of_files) #All the XML files in a list
    for i in all_files: #For loop that goes through the list
        tree = ET.parse(i)
        root = ET.tostring(tree.getroot())
        table_lists = tree.iter('{http://www.elsevier.com/xml/common/dtd}table')
        for table in table_lists:
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
                if len(rows) == 2:
                    entry_list = rows[1].findall('{http://www.elsevier.com/xml/common/dtd}entry')
                    for more_entry in entry_list: 
                        total2 = ''
                        for y in more_entry.itertext():
                            total2 = y + total2
                        sub_header.append(total2)
                    content_list.append(sub_header)
            lst2 = table.iter('{http://www.elsevier.com/xml/common/cals/dtd}tbody')
            for data in lst2:
                rows = data.findall('{http://www.elsevier.com/xml/common/cals/dtd}row')
                for row in rows: 
                    entry_list = row.findall('{http://www.elsevier.com/xml/common/dtd}entry')
                    row_data = []
                    for entry in entry_list:
                        content = entry.text 
                        row_data.append(content)
                    content_list.append(row_data)
            rows = content_list
            df = pd.DataFrame(rows, columns = total_list)
            #print(df)
            #df.to_csv('Table' + str(counter) + '.csv',encoding='utf-8')
            counter = counter + 1
            content_list.clear()
            total_list.clear()
            sub_header.clear()
            all_tables.append(df)
    return all_tables
get_tables_from_xml_file(path = r'C:/Users/shulo/OneDrive/Desktop/testing')