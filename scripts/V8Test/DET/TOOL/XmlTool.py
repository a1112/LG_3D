import xml.etree.ElementTree as ET
from PIL import Image
from .SaveXml import *

def xml_reader(filename, imageUrl=None):
    """ Parse a PASCAL VOC xml file """
    tree = ET.parse(filename)

    if imageUrl:
        width, height = Image.open(imageUrl).size
    else:
        size = tree.find('size')
        width = int(size.find('width').text)
        height = int(size.find('height').text)
    objects = []
    for obj in tree.findall('object'):
        obj_struct = {}
        obj_struct['name'] = obj.find('name').text
        bbox = obj.find('bndbox')
        obj_struct['bbox'] = [int(bbox.find('xmin').text),
                              int(bbox.find('ymin').text),
                              int(bbox.find('xmax').text),
                              int(bbox.find('ymax').text)]
        objects.append(obj_struct['bbox'] + [obj_struct['name']])
    objects.sort(key=lambda item: item[0])
    return width, height, objects