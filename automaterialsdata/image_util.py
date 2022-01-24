from skimage import io
import os

def read_measurements(filename):
    """
    A helper function to read all the rectangular boxes
    Args:
    ----
    filename: str, the file path that contains the all rectangular boxes coordinates 
    
    Return:
    ----
    list of list
    """
    measurements = []
    with open(filename, 'r') as f:
        line = f.readline()
        line = f.readline()
        while line != "":
            entires = line.split()
            measurements.append(list(map(int, entires[1:])))
            line = f.readline()

    return measurements 

def save_measurements(filename, measurements):
    """
    A helper function to save all the rectangular boxes
    Args:
    ----
    filename: str, the file path that contains the all rectangular boxes coordinates 
    measurements: list of list
    
    """
    header = '    ' + '    '.join(['BX', 'BY' , 'Width', 'Height']) + '\n'
    lines = [header]
    for i in range(len(measurements)):
        lines.append('    '.join([str(i+1)] + list(map(str, measurements[i]))) + '\n')

    with open(filename, 'w') as f:
        f.writelines(lines)

    return 

def normalize_coordinates(inp, shape):
    """
    A helper function to normalize the box coordiantes
    Args:
    ----
    inp: list of int with dimension 4, the absolute coordiantes of a rectangular box
    shape: a list or tuple with dimension at least 2, contains the shape of the image 

    Return:
    ----
    list of float with dimension 4, the relative coordiantes of a rectangular box 
    """
    
    return [inp[0] / shape[1], inp[1] / shape[0], 
            inp[2] / shape[1], inp[3] / shape[0]]

def revert_coordinates_normalization(inp, shape):
    """
    A helper function to revert the box coordiantes normaliztion
    Args:
    ----
    inp: list of int with dimension 4, the relative coordiantes of a rectangular box
    shape: a list or tuple with dimension at least 2, contains the shape of the image 

    Return:
    ----
    list of float with dimension 4, the absolute coordiantes of a rectangular box 
    """
    return [int(inp[0] * shape[1]), int(inp[1] * shape[0]),
            int(inp[2] * shape[1]), int(inp[3] * shape[0])]

def scale_bounding_box(bbox, scale, shape):

    cX = bbox[0] + int(bbox[2]/2) 
    cY = bbox[1] + int(bbox[3]/2)
    scaled_w = int(bbox[2] * scale)
    scaled_h = int(bbox[3] * scale)
    
    scaled_bbox = [ max(cX - int(scaled_w / 2), 0),
                    max(cY - int(scaled_h / 2), 0),
                    min(scaled_w, shape[1]),
                    min(scaled_h, shape[0])]

    return scaled_bbox 

class labeledImage():
    """
     a data structure class to store information of a labeled images     
    """
    
    def __init__(self, image_path):
        """
        Class Constructor
        Args:
        ----
        image_path: str, a path where an image is stored
        """
        self.path = image_path
        self.name = image_path.split('/')[-1] 
        self.shape = io.imread(image_path).shape
        self.labels = {}
    
        return

    def add_labels(self, tag, regions):
        """
        Add lablels to the image
        Args:
        ----
        tag: str, label name
        regions: list of list, the inner list should have dimension of 4 that
                 contains the [BX, BY, Wihth, Height] of a retangular box 
        """
        
        if tag not in self.labels.keys():
            self.labels[tag] = regions
        else:
            self.labels[tag] += regions

        return
    
    def add_labels_from_file(self, tag, filename):
        """
        Add labels form a file

        """
        self.add_labels(tag, read_measurements(filename)) 
        
        return
    
    def write_labels_to_file(self, tag, filename):
        """
        Write labels to a file
        """
        save_measurements(filename, self.labels[tag])

        return
    
    def save_cropped_images_based_on_labels(self, output_folder, output_format='png', scale_bbox=None, saved_tags=None):
        """
        Save labeled parts to output folder
        """
        assert output_format in ['png', 'jpg', 'jepg']

        if saved_tags is None:
            saved_tags = self.labels.keys()
        else:
            saved_tags = [i for i in saved_tags if i in self.labels.keys()]

        for i in range(len(saved_tags)):
            tag = saved_tags[i]
            labels = self.labels[tag] 
            output_prefix = os.path.join(output_folder, '_'.join(self.name.split('.')[:-1]) + '_' + tag) 
            image = io.imread(self.path)
            count = 0
            for l in labels:
                if scale_bbox is not None: l = scale_bounding_box(l, scale_bbox, image.shape)
                cropped = image[l[1]:l[1]+l[3], l[0]:l[0]+l[2]]
                output = output_prefix + '_' + str(count) + '.' + output_format 
                io.imsave(output, cropped)
                count += 1

        return 

    def __str__(self):
        """
        Overriding the printing function, such that when calling
        print(labeledImage) will give all the information
        """
        
        print_str = 'Labeled image ' + self.name + '\n'
        print_str += '    location: ' + self.path + '\n'
        print_str += '    shape: ' + str(self.shape) + '\n'
        print_str += '    lables:'  + '\n'
        for t, labels in self.labels.items():
            print_str += '    - ' + str(t) + ': \n'
            for l in labels:
                print_str += '      ' + str(l) + '\n'
        
        return print_str 

def convert_to_yolo_format(labeled_images, output_path=None, tags=None):
    """ 
    This function converts a list of images labels 
      from ImageJ format: absolute coordinates [Begin_X, Begin_Y, Width, Height]
      to yolo format:     relative coordinates [Center_X, Center_Y, Width, Height] 
    
    Args:
    ----
    labeled_images: list of labledImage
    output_path:  str, by default it will save to the same directory when you execute
                       this script
    tags: pre-assigned tags
    """
    
    # collection all the labels
    if tags is None:
        tags = set()
        for img in labeled_images:
            tags.update(img.labels.keys())
    
        tags = list(tags)
    
    # generate yolo labels for each labeled_images
    if output_path is None:
        output_path = '.'
    
    for img in labeled_images:
        fname = os.path.join(output_path, img.name.split('.')[0] + '.txt')
        
        
        with open(fname, 'w') as f:
            for tag, labels in img.labels.items():
                tag_id = tags.index(tag)
                for l in labels:
                    # compute relative coordinates
                    bx, by, w, h = normalize_coordinates(l, img.shape)
                    cx = bx + w / 2.0
                    cy = by + h / 2.0
                    
                    f.write('%d %.6f %.6f %.6f %.6f \n' %(tag_id, cx, cy, w, h)) 
        
        print('successfully generated labels for image ', img.name)
    
    return tags
