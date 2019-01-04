import unittest
from util import *
import copy
from psd_tools import BBox
from psd_tools.user_api import pil_support


class ImageBase:
    def __init__(self, size, root_group):
        self.size = size
        if not isinstance(root_group, StoredGroup):
            raise TypeError('not a StoredGroup type as root group')
        self.root_group = root_group
        root_group.parent = self

    def __repr__(self):
        base_str = "ImageBase:\nsize:%s\n" % str(self.size)
        for stored_image in self.root_group.stored_list:
            base_str += str(stored_image)
            base_str += '\n'
        return base_str

    @property
    def _image_base(self):
        return self

    @property
    def bbox(self):
        return BBox(0, 0, self.size[0], self.size[1])

    def as_stored_image(self):
        """
        把整个ImageBase合并成同样外观的一个StoredImage。在边缘之外的部分将被裁剪。
        其父节点被置为None。
        :return: 被合并完成的StoredImage。
        """
        result_img = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
        op_image = self.root_group.final_image_as_PIL
        result_img.paste(op_image, (self.root_group.bbox.x1, self.root_group.bbox.y1))
        return StoredImage(None, result_img, self.root_group.info, self.bbox)

    def collapsed_image_base(self):
        new_root_group = StoredGroup(None, copy.copy(self.root_group.info))
        new_root_group.add_stored_image(self.as_stored_image())
        collapsed_image_base = ImageBase(self.size, new_root_group)
        return collapsed_image_base

    def delete_raw_stored_image(self, raw_stored_image):
        return self.root_group.delete_raw_stored_image(raw_stored_image)

    @property
    def image(self):
        """
        整个ImageBase合并成一张以后的PIL
        :return: 合并后的PIL
        """
        return self.as_stored_image()._image


class ImageInfo:
    """
    存储图层信息的类
    """

    def __init__(self, **kwargs):
        self.visible = kwargs['visible']
        self.visible_global = kwargs['visible_global']
        self.opacity = kwargs['opacity']
        self.name = kwargs['name']

    @classmethod
    def default(cls):
        """
        得到一个默认的、名字为空的info对象，用于实现root_group
        :return:
        """
        return ImageInfo(visible=True, visible_global=True, opacity=255, name='')

    @classmethod
    def image_info_from_psd_layer(cls, psd_layer):
        """
        从读取的psd的层中直接获取info
        :param psd_layer:
        :return:
        """
        # return ImageInfo(psd_layer.visible, psd_layer.visible_global, psd_layer.opacity)
        attrs = dir(psd_layer)
        plausible_attrs = [x for x in attrs if x[0] != '_']
        attr_dict = {}
        for attr in plausible_attrs:
            attr_dict[attr] = getattr(psd_layer, attr)
            # 把可能有用的attr全部传入
        return ImageInfo(**attr_dict)

    def __repr__(self):
        return "<ImageInfo:%s>" % str(self.__dict__)


class RawStoredImage:

    def __init__(self, parent, info):
        self.parent = parent  # 这句暂时有些问题，因为parent按目前的工作流可以为None，但这样不优雅
        if not isinstance(info, ImageInfo):
            raise TypeError('Stored image info given is not ImageInfo type.')
        self.info = info

    @property
    def _image_base(self):
        """
        得到其根节点。因随parent变化，所以不用重复赋值
        :return:
        """
        return self.parent._image_base

    @property
    def name(self):
        return self.info.name

    @property
    def visible(self):
        return self.info.visible

    @visible.setter
    def visible(self, value):
        if not isinstance(value, bool):
            raise TypeError('visible property must be bool type')
        self.info.visible = value

    @property
    def opacity(self):
        return self.info.opacity

    @opacity.setter
    def opacity(self, value):
        if not isinstance(value, int):
            raise TypeError('opacity value must be int')
        if not 0 <= value <= 255:
            raise ValueError('opacity must be between 0 and 255')
        self.info.opacity = value

    @property
    def image(self):
        """
        随便写了一个image,用于被继承
        :return:
        """
        raise NotImplementedError('RawStoredImage cannot be used directly')

    @property
    def bbox(self):
        """
        随便写了一个BBox，用于被继承
        :return:
        """
        raise NotImplementedError('RawStoredImage cannot be used directly')

    @property
    def final_image_as_PIL(self):
        if not self.visible:
            blank_pic = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
            return blank_pic
        return pil_support.apply_opacity(self.image, self.opacity)

    def as_base_size_PIL(self):
        """
        返回一个ImageBase大小的图像
        :return:
        """
        result_img = new_blank_pic_as_PIL(self._image_base.bbox.width, self._image_base.bbox.height)
        result_img.paste(self.final_image_as_PIL, (self.bbox.x1, self.bbox.y1))
        return result_img

    def employ_operation(self, op):
        op(self)


class StoredGroup(RawStoredImage):

    def __init__(self, parent, info):
        super(StoredGroup, self).__init__(parent, info)
        self.stored_list = []

    def add_stored_image(self, stored_image):
        """
        将一层StoredImage添加进组
        :param stored_image: 要被添加的StoredImage
        :return:
        """
        if not isinstance(stored_image, RawStoredImage):
            raise TypeError('Not a RawStoredImage Storing')
        stored_image.parent = self
        # 添加时就改变了其parent
        self.stored_list.append(stored_image)

    def __repr__(self):
        return "<StoredGroup:%d Stored,%s>" % (len(self.stored_list), str(self.bbox))

    @property
    def bbox(self):
        if len(self.stored_list) == 0:
            return BBox(0, 0, 0, 0)
        min_x1 = min([x.bbox[0] for x in self.stored_list])
        min_y1 = min([x.bbox[1] for x in self.stored_list])
        max_x2 = max([x.bbox[2] for x in self.stored_list])
        max_y2 = max([x.bbox[3] for x in self.stored_list])
        return BBox(min_x1, min_y1, max_x2, max_y2)

    @property
    def image(self):
        return self.as_stored_image()._image

    @property
    def final_image_as_PIL(self):
        if not self.visible:
            blank_pic = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
            return blank_pic
        return pil_support.apply_opacity(self.image, self.opacity)

    def as_stored_image(self):
        """
        把自身转化为合并后的单个的StoredImage
        12.31:从collapse...函数改造
        :return: 合并完成的StoredImage
        """
        if not isinstance(self, StoredGroup):
            raise TypeError("Not a StoredGroup type being collapsing")
        group_image = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)

        for stored_image in self.stored_list[::-1]:

            relative_bbox = BBox(stored_image.bbox.x1 - self.bbox.x1,
                                 stored_image.bbox.y1 - self.bbox.y1,
                                 stored_image.bbox.x2 - self.bbox.x1,
                                 stored_image.bbox.y2 - self.bbox.y1)
            # 计算图片在整个组中的相对边界。组的边界是由整个组内部所有成员的边界确定的

            if isinstance(stored_image, StoredGroup):
                op_image = stored_image.as_stored_image().final_image_as_PIL
            else:
                op_image = stored_image.final_image_as_PIL

            temp_image = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
            # 创建一张和整个组一样大的空图
            temp_image.paste(op_image, (relative_bbox.x1, relative_bbox.y1))
            # 虽然带透明度的两张图无法直接paste，但是贴到一张全透明的空图的中却可以
            group_image = Image.alpha_composite(group_image, temp_image)
            # 带透明度没法直接paste，必须alpha_composite
        return StoredImage(None, group_image, copy.copy(self.info), copy.copy(self.bbox))

    def get_stored_layer_count(self, *, unfold_groups=False):
        """
        返回该StoredGroup中包含的StoredImage层数
        :param unfold_groups: 是否展开内部的StoredGroup,如果展开则是计算所有的StoredImage数量，
        如果不展开则把内部的StoredGroup作为StoredImage计算
        :return: 计算得到的层数
        """
        if unfold_groups:
            index = 0
            for stored_image in self.stored_list:
                if isinstance(stored_image, StoredImage):
                    index += 1
                elif isinstance(stored_image, StoredGroup):
                    index += stored_image.get_stored_layer_count(unfold_groups=unfold_groups)
            return index
        return len(self.stored_list)

    def get_stored_image_list(self, *, unfold_groups=False):
        if unfold_groups:
            stored_image_list = []
            for stored_image in self.stored_list:
                if isinstance(stored_image, StoredGroup):
                    stored_image_list += stored_image.get_stored_image_list(unfold_groups)
                elif isinstance(stored_image, StoredImage):
                    stored_image_list.append(stored_image)
            return stored_image_list
        return self.stored_list

    def delete_raw_stored_image(self, raw_stored_image):
        if raw_stored_image == self._image_base.root_group:
            raise ValueError('root group cannot be deleted')
        if not isinstance(raw_stored_image, RawStoredImage):
            raise TypeError('not a RawStoredImage type being deleting')
        try:
            self.stored_list.remove(raw_stored_image)
            raw_stored_image.parent = None
            return True
        except ValueError:
            for stored_image in self.stored_list:
                if isinstance(stored_image, StoredGroup):
                    if stored_image.delete_raw_stored_image(raw_stored_image):
                        return True
        return False

    def employ_operation(self, op):
        for stored_image in self.stored_list:
            stored_image.employ_operation(op)


class StoredImage(RawStoredImage):

    def __init__(self, parent, image, info, bbox):
        super(StoredImage, self).__init__(parent, info)
        self._image = image
        self._bbox = bbox

    def __repr__(self):
        # return "<StoredImage:%s>" % str(self.__dict__)
        return "<StoredImage:%s>" % (str(self.name) +" " + str(self._bbox))

    @classmethod
    def stored_image_from_psd_layer(cls, layer):
        return StoredImage(None, layer.as_PIL(), ImageInfo.image_info_from_psd_layer(layer), layer.bbox)

    @property
    def final_image_as_PIL(self):
        """
        blank_pic = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
        if not self.visible:
            return blank_pic
        try:
            final_pic = Image.blend(blank_pic, self.image, self.opacity/255)
            return final_pic
        except ValueError:
            print(self.bbox)
            return blank_pic
        """
        if not self.visible:
            blank_pic = new_blank_pic_as_PIL(self.bbox.width, self.bbox.height)
            return blank_pic
        return pil_support.apply_opacity(self._image, self.opacity)

    def as_full_size_PIL(self):
        width, height = self._image_base.size
        result_image = new_blank_pic_as_PIL(width, height)
        result_image.paste(self._image, (self._bbox.x1, self._bbox.y1))
        return result_image

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    @property
    def bbox(self):
        return self._bbox

    @bbox.setter
    def bbox(self, value):
        if not isinstance(value,BBox):
            raise TypeError('not a BBox type setting in the StoredImage')
        self._bbox = value




class TestImageBase(unittest.TestCase):

    def Test_info(self):
        from psd_tools import PSDImage
        psd = PSDImage.load('E:\\PyScripts\\test_dir\\RUN.psd')
        for layer in psd.layers:
            info = ImageInfo.image_info_from_psd_layer(layer)
            print(info)


if __name__ == '__main__':
    unittest.main()
