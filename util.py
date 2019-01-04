from PIL import Image


def new_blank_pic_as_PIL(width, height):
    """
    新建一个特定大小的透明PIL图片
    :param width: 宽
    :param height: 高
    :return: 透明PIL图片
    """
    blank_pic = Image.new(
        "RGBA",
        (width, height),
        color=(255, 255, 255, 0)
    )
    return blank_pic


def resize_pil_image_by_percentage(pil_image, percentage):
    if not isinstance(pil_image, Image.Image):
        raise TypeError('not a pil Image type being resizing')
    if percentage <= 0:
        raise ValueError('scale must be greater than 0')
    x, y = pil_image.size
    new_x = int(x*(percentage/100))
    new_y = int(y*(percentage/100))
    return pil_image.resize((new_x, new_y))
