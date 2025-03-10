import math
from pathlib import Path
from lxml import etree


def create_xml(file_name, img_shape, bounding_boxes, output_folder=None):
    annotation = etree.Element("annotation")
    if output_folder is None:
        output_folder = Path(file_name).parent
    folder = etree.SubElement(annotation, "folder")
    folder.text = "images"

    filename = etree.SubElement(annotation, "filename")
    filename.text = str(file_name)

    size = etree.SubElement(annotation, "size")
    width = etree.SubElement(size, "width")
    width.text = str(img_shape[1])
    height = etree.SubElement(size, "height")
    height.text = str(img_shape[0])
    depth = etree.SubElement(size, "depth")
    depth.text = str(img_shape[2])

    for bbox in bounding_boxes:
        xmin, ymin, xmax, ymax, class_id, source, label = bbox
        obj = etree.SubElement(annotation, "object")

        name = etree.SubElement(obj, "name")
        name.text = str(label)

        bndbox = etree.SubElement(obj, "bndbox")
        xmin_elem = etree.SubElement(bndbox, "xmin")
        xmin_elem.text = str(xmin)
        ymin_elem = etree.SubElement(bndbox, "ymin")
        ymin_elem.text = str(ymin)
        xmax_elem = etree.SubElement(bndbox, "xmax")
        xmax_elem.text = str(xmax)
        ymax_elem = etree.SubElement(bndbox, "ymax")
        ymax_elem.text = str(ymax)

    tree = etree.ElementTree(annotation)
    xml_path = Path(output_folder) / Path(file_name).with_suffix('.xml').name
    tree.write(str(xml_path), pretty_print=True, xml_declaration=True, encoding="utf-8")
    print(f"Saved XML to {xml_path}")


def get_image_box(image, xmin, ymin, xmax, ymax, out_size_=5,min_size=60):
    w, h = image.size
    out_size=out_size_
    out_size_w=out_size
    out_size_h=out_size
    image_width = xmax-xmin
    image_height = ymax-ymin

    if image_width < min_size:
        out_size_w = abs(min_size-image_width)//2
    if image_height < min_size:
        out_size_h = abs(min_size-image_height)//2
    # print(f"image_width {image_width} image_height:{image_height} out_size_w:{out_size_w} image_height: {out_size_h}")
    return max(xmin - out_size_w, 0), max(ymin - out_size_h, 0), min(xmax + out_size_w, w), min(ymax + out_size_h, h)
