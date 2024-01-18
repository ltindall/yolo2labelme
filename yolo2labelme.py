import base64
from PIL import Image
import json, yaml, os, argparse
import shutil

image_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')

def tobase64(file_path):
    with open(file_path, "rb") as image_file:
        data = base64.b64encode(image_file.read())
        return data.decode()

def img_filename_to_ext(img_filename, ext='txt'):
    for img_ext in image_extensions:
        if img_filename.lower().endswith(img_ext):
            return img_filename[:-len(img_ext)] + ext

def is_image_file(file_path):
    file_path = file_path.lower()
    for ext in image_extensions:
        if file_path.endswith(ext):
            return True
    return False

def get_shapes(txt_path, width, height, class_labels):
    shapes = open(txt_path).read().split('\n')
    result = []
    for shape in shapes:
        if not shape:
            continue
        values = shape.split()

        class_id = values[0]
        r_shape = dict()
        r_shape["label"] = class_labels[int(class_id)]

        values = [float(value) for value in values[1:]]
        points = []
        x_center,y_center,w,h = values
        x_min = (x_center - 0.5*w) * width
        y_min = (y_center - 0.5*h) * height
        x_max = (x_center + 0.5*w) * width
        y_max = (y_center + 0.5*h) * height
        # for i in range(len(values)//2):
        #     points.append([values[2*i]*width, values[2*i+1]*height])
        points = [[x_min, y_min],[x_max, y_max]]
        r_shape['points'] = points

        r_shape.update({ "group_id": None,
            "description": "",
            "shape_type": "rectangle",
            "flags": {}
        })
        result.append(r_shape)
    return result

def yolo2labelme_single(txt_path, img_path, class_labels, output_dir):
    img = Image.open(img_path)
    result = {"version": "5.2.1", "flags": {}}
    result['shapes'] = get_shapes(txt_path, img.width, img.height, class_labels)
    result["imagePath"] = img_path
    result["imageData"] = tobase64(img_path)
    result["imageHeight"] = img.height
    result["imageWidth"] = img.width

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    
    img_filename = os.path.basename(img_path)
    json_path = img_filename_to_ext(img_filename,'.json')
    json_path = os.path.join(output_dir,json_path)
    with open(json_path,'w') as f:
        f.write(json.dumps(result))
    shutil.copyfile(img_path, os.path.join(output_dir, img_filename) )

def yolo2labelme(dataset_yaml, dataset_dir=None, output_dir=None, skip=False):
    
    #yaml_path = os.path.join(data_dir,"dataset.yaml")

    with open(dataset_yaml, 'r') as stream:
        data_loaded = yaml.safe_load(stream)
        class_labels = data_loaded['names']

    if output_dir is None:
        if dataset_dir:
            output_dir = os.path.join(os.path.abspath(dataset_dir),'..','labelmeDataset')
        else:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(dataset_yaml)), 'labelmeDataset')
    print(f"Ouput will be in {output_dir}.")

    search_dirs = []
    if dataset_dir: 
        search_dirs.append(dataset_dir)
    else:
        for dir_type in ['test', 'train', 'val']:
            if dir_type in data_loaded:
                dir_path = os.path.join(os.path.dirname(os.path.abspath(dataset_yaml)), data_loaded[dir_type])
                dir_path = os.path.abspath(dir_path)
                search_dirs.append(dir_path)
            else: 
                print(f"No {dir_type} directory defined in {dataset_yaml}.")
    if not search_dirs: 
        raise ValueError(f"dataset_dir is None and no directories found in dataset.yaml")
    
    for dir_path in search_dirs:
        for filename in os.listdir(dir_path):
            img_file = os.path.join(dir_path,filename)
            if is_image_file(img_file):
                print(f"{img_file=}")
                print(f"{os.path.dirname(os.path.dirname(img_file))=}")
                if 'images' in img_file:
                    txt_file = img_filename_to_ext(img_file.replace('images','labels'), '.txt')
                else:
                    txt_file = img_filename_to_ext(os.path.join(os.path.dirname(os.path.dirname(img_file)),'labels',os.path.basename(img_file)), '.txt')
                print(f"{txt_file=}")
                if os.path.exists(txt_file):
                    yolo2labelme_single(txt_file, img_file, class_labels, output_dir)
                else:
                    if skip == False:
                        raise FileNotFoundError(f"{txt_file} is expected to exist."
                                                +"Pass skip=True to skip silently.\n"
                                                +"skip='print' to print missed paths.")
                    elif skip == 'print':
                        print(f'Missing {txt_file}')

y2l = yolo2labelme

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('dataset_yaml')
    argparser.add_argument('--dataset_dir', default=None, required=False)
    argparser.add_argument('--output_dir', default=None, required=False)
    argparser.add_argument('--skip', default=False, required=False)
    args = argparser.parse_args()
    yolo2labelme(args.dataset_yaml, args.dataset_dir, args.output_dir, args.skip)

if __name__ == '__main__':
    main()