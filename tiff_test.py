import copy
from psd_tools import PSDImage, Layer, Group, BBox
from image_base import *


'''
psd = PSDImage.load('E:\\PyScripts\\test_dir\\Midterm.psd')
print(psd.header)
print(psd.layers)
print(isinstance(psd.layers[0], Layer))
'''

"""
for layer in psd.layers:
    try:
        layer_image = layer.as_PIL()
    except ValueError:
        print(layer)
        continue
    layer_image.save('E:\\PyScripts\\test_dir\\output\\+%s.png' % layer.name)
"""


def extract_image_base_of_psd(psd, *, unfold_groups=False, full_size=False):
    """
    把读取的psd转换为自己写的ImageBase数据类型。
    自己写的数据结构和库里的数据结构类似，StoredGroup类似于Group类型的layers，ImageBase则相当于psd
    但是自己写的文件类型直接操作起来更放心，直接读取的psd除了导出为PIL并没提供编辑功能
    :param psd: 需要被提取的psd
    :param unfold_groups: 是否展开所有组
    :param full_size: 是否把每层都展开为原PSD大小
    :return: 被转换完成的ImageBase
    """
    index, root_group = extract_stored_image_of_layers(psd.layers, unfold_groups=unfold_groups, full_size=full_size)
    image_base = ImageBase((psd.header.width, psd.header.height), root_group)
    return image_base


def extract_stored_image_of_layers(layers, *, unfold_groups=False, full_size=False, index=0, **kwargs):
    """
    把读取的的layers（原Group类型数据）存储为自己的数据结构StoredGroup。
    自己写的数据结构和库里的数据结构类似，StoredGroup类似于Group类型的layers，ImageBase则相当于psd
    但是自己写的文件类型直接操作起来更放心，直接读取的psd除了导出为PIL并没提供编辑功能
    :param layers:
    :param unfold_groups: 是否展开所有的组，True则展开
    :param full_size: 是否把每层都展开为原PSD大小。此选项会丢失原有bbox数据。
    :param index: 在直接调用时不应填写此项。函数递归内部展开计数用。
    :param kwargs: 其他参数
    :return: 被展开的StoredGroup
    """
    if index == 0 or not unfold_groups:
        the_one_group = StoredGroup(None, ImageInfo.default())
    else:
        the_one_group = kwargs['the_one_group']
    for layer in layers:
        try:
            if unfold_groups and isinstance(layer, Group):
                index = extract_stored_image_of_layers(layer.layers, unfold_groups=unfold_groups, full_size=full_size,
                                                       index=index, the_one_group=the_one_group)[0]
                continue
            elif not unfold_groups and isinstance(layer, Group):
                index, stored_image = extract_stored_image_of_layers(layer.layers, unfold_groups=unfold_groups,
                                                                     full_size=full_size, index=index)
            else:
                stored_image = StoredImage.stored_image_from_psd_layer(layer)
                if full_size:
                    layer_image = layer.as_PIL()
                    full_size_pic = new_blank_pic_as_PIL(layer._psd.bbox.width, layer._psd.bbox.height)
                    # 此处需要直接访问根节点PSD以获取其整个PSD文件的大小，故访问了其受保护的成员
                    # print(full_size_pic.size)
                    full_size_pic.paste(layer_image, (layer.bbox.x1, layer.bbox.y1))
                    layer_image = full_size_pic
                    bbox = copy.copy(layer._psd.bbox)
                    stored_image = StoredImage(None, layer_image, ImageInfo.image_info_from_psd_layer(layer), bbox)
                index += 1
            print(stored_image)
            the_one_group.add_stored_image(stored_image)
        except ValueError:
            print(layer)
            continue
    return index, the_one_group


def collapse_group_into_stored_image(stored_group):
    """
    把一个自己的StoredGroup合并成一个StoredImage，就像Photoshop里的合并图层

    还差的地方：如果bbox中信息和实际图像大小不符的话？
    另外未考虑NORMAL以外的混合模式
    未考虑各种蒙版，因为PSD实在有点复杂
    12.29:边缘总是会多一个像素，考虑crop
    12.30:边缘多一个像素被证明是图层内容本来就超出边界的原因
    :param stored_group:
    :return:一个合并完成的StoredImage
    """
    if not isinstance(stored_group, StoredGroup):
        raise TypeError("Not a StoredGroup type being collapsing")
    group_image = new_blank_pic_as_PIL(stored_group.bbox.width, stored_group.bbox.height)

    for stored_image in stored_group.stored_list[::-1]:

        relative_bbox = BBox(stored_image.bbox.x1-stored_group.bbox.x1, stored_image.bbox.y1-stored_group.bbox.y1,
                             stored_image.bbox.x2-stored_group.bbox.x1, stored_image.bbox.y2-stored_group.bbox.y1)
        # 计算图片在整个组中的相对边界。组的边界是由整个组内部所有成员的边界确定的

        if isinstance(stored_image, StoredGroup):
            op_image = collapse_group_into_stored_image(stored_image).final_image_as_PIL
        else:
            op_image = stored_image.final_image_as_PIL

        temp_image = new_blank_pic_as_PIL(stored_group.bbox.width, stored_group.bbox.height)
        # 创建一张和整个组一样大的空图
        temp_image.paste(op_image, (relative_bbox.x1, relative_bbox.y1))
        # 虽然带透明度的两张图无法直接paste，但是贴到一张全透明的空图的中却可以
        group_image = Image.alpha_composite(group_image, temp_image)
        # 带透明度没法直接paste，必须alpha_composite
    return StoredImage(None, group_image, copy.copy(stored_group.info), copy.copy(stored_group.bbox))


def image_base_as_PIL(image_base):
    """
    把整个ImageBase导出为图片
    让我感觉很高兴的是，库里直接导出png会透明度偏高而这个函数就不会
    :param image_base:
    :return:
    """
    if not isinstance(image_base, ImageBase):
        raise TypeError('Not a ImageBase type converting into PIL')
    result_img = new_blank_pic_as_PIL(image_base.bbox.width, image_base.bbox.height)
    op_image = image_base.root_group.image
    try:
        result_img.paste(op_image, (image_base.root_group.bbox.x1, image_base.root_group.bbox.y1))
    except ValueError:
        print(op_image.bbox)
    return result_img


def stored_image_as_full_size_PIL(stored_image):
    pass


def form_grid_atlas_from_image_base(image_base, column_count=5, *, unfold_groups=False, reverse=False):
    """
    把一个ImageBase转换为影格PIL。
    :param image_base: 被转换的ImageBase
    :param column_count: 影格列数
    :param unfold_groups: 是否打开所有的组
    :param reverse: 是否反序
    :return:生成的影格，一个PIL Image
    """
    if not isinstance(image_base, ImageBase):
        raise TypeError('not a ImageBase type being forming a grid')
    if not isinstance(column_count, int):
        raise TypeError('column_count must be int type')
    if column_count < 1:
        raise ValueError('column_count must be greater than 1')
    grid_width = image_base.size[0]
    grid_height = image_base.size[1]
    stored_image_list = image_base.root_group.get_stored_image_list(unfold_groups=unfold_groups)
    if reverse:
        stored_image_list = list(reversed(stored_image_list))
    total_count = len(stored_image_list)
    if column_count > total_count:
        column_count = total_count
    row_count = total_count//column_count
    if total_count % column_count > 0:
        row_count += 1
    total_width = column_count * grid_width
    total_height = row_count * grid_height
    result_img = new_blank_pic_as_PIL(total_width, total_height)
    for i in range(total_count):
        x1 = (i % column_count)*grid_width
        y1 = (i // column_count)*grid_height
        result_img.paste(stored_image_list[i].as_base_size_PIL(), (x1, y1))
    return result_img


def create_anim_clip_from_image_base(image_base, *, unfold_groups=False, reverse=False):
    """
    返回一个ImageBase尺寸的PIL的列表,可视为连续动画帧
    :param image_base:
    :param unfold_groups:
    :param reverse:
    :return:
    """
    if not isinstance(image_base, ImageBase):
        raise TypeError('not a ImageBase type being forming a grid')
    stored_image_list = image_base.root_group.get_stored_image_list(unfold_groups=unfold_groups)
    if reverse:
        stored_image_list = list(reversed(stored_image_list))
    return [x.as_base_size_PIL() for x in stored_image_list]


def save_gif_from_clip(clip, filename, fps=24, bg_color=(255, 255, 255, 255)):
    """
    保存gif
    :param clip:
    :param filename:
    :param fps:
    :param bg_color:
    :return:
    """
    # bg_colored_clip = [Image.new("RGBA", x.size, color=bg_color).paste(x, (0, 0)) for x in clip]
    bg_colored_clip = []
    for image in clip:
        if bg_color is not None:
            bg_img = Image.new("RGBA", image.size, color=bg_color)
            #bg_img.paste(image, (0, 0))
            bg_img = Image.alpha_composite(bg_img, image)
            bg_colored_clip.append(bg_img)
        else:
            bg_colored_clip.append(image)
    duration = int(1000/fps)
    bg_colored_clip[0].save(filename, format='GIF', append_images=bg_colored_clip[1:], save_all=True, duration=duration,
                            loop=0)


def to_l_mode_operation(stored_image):
    """
    将StoredImage中的image转换为黑白
    :param stored_image:
    :return:
    """
    if not isinstance(stored_image, StoredImage):
        raise TypeError('Not a StoredImage type operating')

    a = stored_image.image.split()[-1]
    r, g, b = stored_image.image.convert('L').convert('RGB').split()
    stored_image.image = Image.merge('RGBA', (r, g, b, a))


def to_1_mode_operation(stored_image):
    """
    将StoredImage中的image转换为二值图像
    :param stored_image:
    :return:
    """
    if not isinstance(stored_image, StoredImage):
        raise TypeError('Not a StoredImage type operating')

    a = stored_image.image.split()[-1]
    r, g, b = stored_image.image.convert('1').convert('RGB').split()
    stored_image.image = Image.merge('RGBA', (r, g, b, a))


"""
class TestPSD(unittest.TestCase):

    def Test_extract(self):
        index, group = extract_stored_image_of_layers(psd.layers, unfold_groups=True, full_size=True)
        print(group)
        index, group = extract_stored_image_of_layers(psd.layers)
        print(group)

    def Test_psd_extract(self):
        image_base = extract_image_base_of_psd(psd)
        print(image_base)

    def Test_group_collapsing(self):
        image_base = extract_image_base_of_psd(psd)
        root_group = image_base.root_group
        # collapsed = collapse_group_into_stored_image(root_group).image
        collapsed = root_group.image
        collapsed.save('E:\\PyScripts\\test_dir\\output\\001test.png')

    def Test_convert(self):
        collapsed = psd.as_PIL()
        collapsed.save('E:\\PyScripts\\test_dir\\output\\002test.png')

    def Test_PIL_paste(self):

        这个测试的结果是PIL的paste没问题
        :return:

        blank_1 = new_blank_pic_as_PIL(100, 100)
        colored = Image.new("RGBA", (100, 100), color=(255, 0, 255, 255))
        blank_1.paste(colored, (50, 50))
        blank_1.save('E:\\PyScripts\\test_dir\\output\\tester2.png')

    def Test_image_base_convert(self):
        image_base = extract_image_base_of_psd(psd)
        collapsed = image_base.image
        collapsed.save('E:\\PyScripts\\test_dir\\output\\003test.png')

    def Test_group_layer_count(self):
        image_base = extract_image_base_of_psd(psd)
        print(image_base.root_group.get_stored_layer_count())
        print(image_base.root_group.get_stored_layer_count(unfold_groups=True))

    def Test_collapsed_image_base(self):
        image_base = extract_image_base_of_psd(psd)
        collapsed_image_base = image_base.collapsed_image_base()
        print(collapsed_image_base.root_group.get_stored_layer_count())
        collapsed_image_base.image.save('E:\\PyScripts\\test_dir\\output\\004test.png')

    def Test_stored_image_as_full_size(self):
        image_base = extract_image_base_of_psd(psd)
        index = 0
        stored_image_list = image_base.root_group.get_stored_image_list(unfold_groups=True)
        for stored_image in stored_image_list:
            stored_image.as_base_size_PIL().save('E:\\PyScripts\\test_dir\\output\\%02dfull_size_test.png' % index)
            index += 1

    def Test_grid(self):
        image_base = extract_image_base_of_psd(psd)
        grid = form_grid_atlas_from_image_base(image_base, column_count=8, reverse=True)
        grid.save('E:\\PyScripts\\test_dir\\output\\grid1.png')

    def Test_gif(self):
        image_base = extract_image_base_of_psd(psd)
        clip = create_anim_clip_from_image_base(image_base, reverse=True)
        save_gif_from_clip(clip, 'E:\\PyScripts\\test_dir\\output\\test.gif', bg_color=(255, 0, 255, 255))

    def test_employ(self):
        image_base = extract_image_base_of_psd(psd)
        image_base.root_group.employ_operation(to_1_mode_operation)
        image_base.image.save('E:\\PyScripts\\test_dir\\output\\opl.png')

if __name__ == '__main__':
    unittest.main()
"""

