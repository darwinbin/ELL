####################################################################################################
##
##  Project:  Embedded Learning Library (ELL)
##  File:     datasetFromImages.py
##  Authors:  Byron Changuion
##
##  Requires: Python 3.x
##
####################################################################################################

import os
import sys
import argparse
import cv2
import numpy as np
import time
import math
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../pythonlibs'))
import modelHelpers

def get_example_list_from_file(file_name, categories_name):
    """
    Parses an example file. Each line in the example file is of the following 
    format:
    LABEL PATH_TO_IMAGE_FILE
    e.g.
    1.0 '/data/squirrel1.jpg'
    -1.0 '/data/bird1.jpg'
    Returns an array of tuples, where the first element is the label, 
    and the second is a path to the image file.
    """
    if categories_name:
        categories = load_categories(categories_name)
    else:
        categories = {}

    lines = []

    with open(file_name, "r") as example_file:
        lines = example_file.readlines()

    examples = []
    line_number = 0
    for line in lines:
        line_number = line_number + 1
        line = line.strip()
        line = line.replace("\t", " ")
        strings = line.split(" ", 1)
        if len(strings) > 1:
            label_number = strings[0]
            image_name = strings[1].strip()
            examples.append((label_number, image_name, label_number))
        else:
            raise ValueError("Couldn't parse line number {} in {}".format(line_number, file_name))

    return examples, categories

def get_example_list_from_folder(folder_name, categories_name, positive_category):
    """
    Walk a folder looking for subfolders of images. Images in each subfolder belong to the
    class specified by the subfolder name.
    The categories_name specifies the name of the file that contains the class categories index.
    If None, then the categories index is generated by this function and saved to 'categories.txt'.
    Returns an array of tuples, where the first element is the class label, 
    and the second is a path to the image file, and class labels.
    """
    examples = []
    class_names = []
    save_categories = False
    if categories_name:
        categories = load_categories(categories_name)
    else:
        categories = {}
        save_categories = True

    for entry in os.scandir(folder_name):
        if entry.is_dir(follow_symlinks=True):
            if positive_category:
                # This is a binary classification, set the labels to 1.0 and -1.0
                if positive_category:
                    if entry.name == positive_category:
                        label = 1.0
                    else:
                        label = -1.0
            else:
                # This is a multi-class dataset. Look up the class index.
                class_names.append(entry.name)
                label = get_category_index_from_categories(categories, entry.name)
            for fileEntry in os.scandir(os.path.join(folder_name, entry.name)):
                if fileEntry.is_file():
                    imageName = os.path.join(folder_name, entry.name, fileEntry.name)
                    examples.append((label, imageName, entry.name))
    
    if save_categories:
        file_name = "categories.txt"
        with open(file_name, mode="w") as f:
            for name in class_names:
                f.write("{}\n".format(name))
        categories = class_names
        print("Wrote class category labels to {}".format(file_name))

    return examples, categories

def set_binary_labels(input_examples, positive_label):
    """
    Replaces the class labels with 1.0 or -1.0, depending on whether 
    the class label matches 'positive_label'.
    Returns an array of tuples, where the first element is the label number 
    and the second is a path to the image file.
    """
    examples = []

    for example in input_examples:
        if example[0] == positive_label:
            examples.append(("1.0", example[1]))
        else:
            examples.append(("-1.0", example[1]))            
    return examples

def write_examples_to_dataset_file(example_list, categories, width, height, use_bgr_ordering, output_dataset):
    """
    Saves an array of examples to a dataset file.
    """
    print("Processing {} examples, using image size {}x{}, bgr={}".format(len(example_list), width, height, use_bgr_ordering))
    with open(output_dataset, 'w') as dataset_file:
        # Write header
        if categories:
            dataset_file.write("# Category labels\n")
            for i, category in enumerate(categories):
                dataset_file.write("# {} : {}\n".format(i, category))
        for example in example_list:
            # Try to read this as an image
            image = cv2.imread(example[1])
            if image is not None:
                # Write label
                dataset_file.write("{}".format(example[0]))
                print("Processing {0[0]} | {0[1]}".format(example))
                resized = modelHelpers.prepare_image_for_model(image, width, height, not use_bgr_ordering)
                # Write image data
                valuesWritten = 0
                for value in resized:
                    dataset_file.write("\t{}".format(value))
                    valuesWritten = valuesWritten + 1
                # Write label, source file as comment
                dataset_file.write("\t# class={0[2]}, source={0[1]}".format(example))
                dataset_file.write("\n")
                print("    Wrote {} data values".format(valuesWritten))
            else:
                print("Skipping {}, could not open as an image".format(example[1]))

    print()
    print("Wrote {} examples to {}".format(len(example_list), output_dataset))

def parse_size(image_size):
    """
    Parses a string like 640x480 and returns width, height.
    """
    width, height = image_size.split('x')
    return int(width), int(height)

def load_categories(file_name):
    """
    Loads the category index from file. Each category label is
    the name of a class specified on a separate line. The entry order
    is the index of the class.
    """
    labels = []
    with open(file_name) as f:
        labels = f.read().splitlines()
    categories = {}
    for category in labels:
        categories[category] = len(categories)
    return categories

def get_category_index_from_categories(categories, category):
    """
    Gets the index of a category from the categories dictionary. If the category
    doesn't exist, it creates a new entry for that category name and returns 
    the new index number.
    """
    if category not in categories:
        categories[category] = len(categories)
    return categories[category]

def main(argv):    
    arg_parser = argparse.ArgumentParser("Creates ELL dataset file from list of labelled images")
    arg_parser.add_argument("--imageSize", help="each image example data is cropped and scaled to width x height e.g. 224x224", default="224x224")
    arg_parser.add_argument("--outputDataset", help="save dataset to this file name, default is dataset.txt", default="dataset.gsdf")
    arg_parser.add_argument("--bgr", help="specify True if output data should be in BGR format (default True)", default=True)
    arg_parser.add_argument("--positiveCategory", help="if examples define a binary classification (e.g. A, not A), specifies which class category is the positive label.", default=None)
    arg_parser.add_argument("--categories", help="if examples define a multi-class classification (e.g. A, B, C), specifies the class category index file.", default=None)
    # mutually exclusive options for specifying examples
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("--exampleList", help="path to the file containing list of examples, where each line is a label number followed by whitespace path to image", default=None)
    group.add_argument("--folder", help="path to a folder, with sub-folders containing images. Each sub-folder is a class and the images inside are the examples of that class", default=None)

    args = arg_parser.parse_args(argv)

    width, height = parse_size(args.imageSize)

    start = time.time()
    if args.exampleList:
        # parse the input file to get list of examples
        examples, categories = get_example_list_from_file(args.exampleList, args.categories)
    elif args.folder:
        # walk the folders looking for image examples
        examples, categories = get_example_list_from_folder(args.folder, args.categories, args.positiveCategory)
    else:
        arg_parser.print_help()
        return

    # process the examples
    write_examples_to_dataset_file(examples, categories, width, height, args.bgr, args.outputDataset)
    end = time.time()
    print("Total time to create dataset: {:.1f} seconds".format(end - start))

if __name__ == "__main__":
    main(sys.argv[1:])    