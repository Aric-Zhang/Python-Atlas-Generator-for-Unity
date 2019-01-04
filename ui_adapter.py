import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from tool_ui import *
import altas_export_dialog as altas_dialog
import gif_export_dialog as gif_dialog
import os
from tiff_test import *

# 存储已打开的ImageBase的list
image_base_list = []


class AtlasExportDialog(QDialog, altas_dialog.Ui_Dialog):
    def __init__(self, parent=None, *, image_base):
        super(AtlasExportDialog, self).__init__(parent)
        self.image_base = image_base
        self.setupUi(self)

        self.spinBox.valueChanged.connect(self.generate_atlas)
        self.checkBox.stateChanged.connect(self.generate_atlas)
        self.spinBox_2.valueChanged.connect(self.show_atlas)
        # self.accept.connect(self.export_png)
        self.generate_atlas()

    def show_graphic_from_pil(self, pil_image):
        """
        在控件的GraphicsView中显示PIL图像
        :param pil_image: 要被显示的PIL图像
        :return:
        """
        pix = pil_image.toqpixmap()
        self.pix_item = QGraphicsPixmapItem(pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.pix_item)
        self.graphicsView.setScene(self.scene)
        print(self.graphicsView.rect())

    def generate_atlas(self):
        """
        根据当前ImageBase生成图集，并显示
        :return:
        """
        column_count = self.spinBox.value()
        reverse = self.checkBox.isChecked()
        grid = form_grid_atlas_from_image_base(self.image_base, column_count=column_count, reverse=reverse)
        self.current_atlas = grid
        self.show_atlas()
        return grid

    def show_atlas(self):
        """
        显示图集
        :return:
        """
        resize_percentage = self.spinBox_2.value()
        temp = resize_pil_image_by_percentage(self.current_atlas, resize_percentage)
        self.show_graphic_from_pil(temp)


class GifExportDialog(QDialog, gif_dialog.Ui_Dialog):
    def __init__(self, parent=None, *, image_base):
        super(GifExportDialog, self).__init__(parent)
        self.image_base = image_base
        self.setupUi(self)

        self.horizontalSlider.valueChanged.connect(self.show_clip)
        self.checkBox.stateChanged.connect(self.generate_anim_clip)
        self.spinBox.valueChanged.connect(self.show_clip)
        self.spinBox_2.valueChanged.connect(self.auto_set_fps)

        self.generate_anim_clip()

    def generate_anim_clip(self):
        """
        生成动画片段PIL图像列表
        :return:
        """
        reverse = self.checkBox.isChecked()
        self.anim_clip = create_anim_clip_from_image_base(self.image_base, unfold_groups=False, reverse=reverse)
        self.auto_set_fps()
        if len(self.anim_clip) > 1:
            self.horizontalSlider.setMaximum(len(self.anim_clip)-1)
        self.show_clip()
        return self.anim_clip

    def show_graphic_from_pil(self, pil_image):
        """
        在控件的GraphicsView中显示PIL图像
        :param pil_image: 要被显示的PIL图像
        :return:
        """
        pix = pil_image.toqpixmap()
        self.pix_item = QGraphicsPixmapItem(pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.pix_item)
        self.graphicsView.setScene(self.scene)
        print(self.graphicsView.rect())

    def show_clip(self):
        index = self.horizontalSlider.value()
        resize_percentage = self.spinBox.value()
        temp = resize_pil_image_by_percentage(self.anim_clip[index], resize_percentage)
        self.show_graphic_from_pil(temp)

    def auto_set_fps(self):
        self.fps = self.spinBox_2.value()


class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.current_pil_image = None

        self.actionOpen.triggered.connect(self.get_file)
        self.actionPNG.triggered.connect(self.export_png)
        self.actionJPEG.triggered.connect(self.export_jpg)
        self.actionPNG_Atlas.triggered.connect(self.export_png_atlas)
        self.actionGIF.triggered.connect(self.export_gif)
        self.actionConvert_to_Greyscale.triggered.connect(self.to_l_mode)
        self.actionConvert_to_Binary.triggered.connect(self.to_1_mode)
        self.actionImage_Base.triggered.connect(self.dock_visible_wrapper(self.get_image_base_list_dock(), True))
        self.actionLayers.triggered.connect(self.dock_visible_wrapper(self.get_image_layer_tree_dock(), True))

        # self.get_image_layer_tree_widget().clicked.connect(self.show_current_tree_item_pil)
        self.get_image_layer_tree_widget().currentItemChanged.connect(self.show_current_tree_item_pil)
        self.get_image_layer_tree_widget().setContextMenuPolicy(Qt.CustomContextMenu)
        self.get_image_layer_tree_widget().customContextMenuRequested.connect(self.custom_stored_group_context_menu)

        self.get_image_base_list_widget().itemClicked.connect(self.show_current_image_base_pil)
        self.get_view_scale_spinbox().valueChanged.connect(self.show_current_pil_image)
        self.get_layer_opacity_spinbox().valueChanged.connect(self.opacity_change)
        self.get_view_full_size_checkbox().stateChanged.connect(self.show_current_pil_image)

    def get_image_base_list_widget(self):
        """
        返回显示已打开的ImageBase的ListWidget
        :return: ListWidget of ImageBases
        """
        return self.listWidget

    def get_image_layer_tree_widget(self):
        """
        返回layers的TreeWidget
        :return: tree of layers
        """
        return self.treeWidget

    def get_view_scale_spinbox(self):
        return self.spinBox

    def get_layer_opacity_spinbox(self):
        return self.spinBox_2

    def get_image_base_list_dock(self):
        return self.dockWidget_4

    def get_image_layer_tree_dock(self):
        return self.dockWidget_5

    def get_view_full_size_checkbox(self):
        return self.checkBox

    def custom_stored_group_context_menu(self, pos):
        """
        定制显示layer信息的TreeWidget的右键菜单
        :param pos:
        :return:
        """
        menu = QMenu()
        delete_opt = menu.addAction("delete")
        to_image_base_opt = menu.addAction("convert to ImageBase")
        action = menu.exec_(self.get_image_layer_tree_widget().mapToGlobal(pos))
        if action == delete_opt:
            self.delete_current_layer()
            return
        elif action == to_image_base_opt:
            print('opt2')
            return
        else:
            print('opt3')
            return

    def get_file(self):
        """
        打开一个文件的操作
        :return:
        """
        try:
            filename, _ = QFileDialog.getOpenFileName(self, 'Open File', 'c:\\', "Files (*.psd)")
            if not os.path.exists(os.path.split(filename)[0]):
                print('open operation cancelled')
                return
            print(filename)
            _psd = PSDImage.load(filename)
            image_base = extract_image_base_of_psd(_psd)
            list_widget_item = QListWidgetItem(filename)
            list_widget_item.image_base = image_base
            self.get_image_base_list_widget().addItem(list_widget_item)
        except TypeError:
            return

    def save_file_filename(self, suffix='.png'):
        """
        获取保存文件的路径
        :param suffix:
        :return:
        """
        if self.get_image_base_list_widget().currentItem() is None:
            # raise TypeError('CurrentItem is None type')
            QMessageBox.critical(self, "Save Operation Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            raise TypeError('CurrentItem is None type')
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", "c:\\", "Files (*%s)" % suffix)
        """
        if len(_) == 0:
            raise IOError('save operation cancelled')
        """
        # print(filename)
        return filename

    def export_png(self):
        """
        导出为png格式文件
        :return:
        """
        if self.get_image_base_list_widget().currentItem() is None:
            # raise TypeError('CurrentItem is None type')
            QMessageBox.critical(self, "Save Operation Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return

        filename = self.save_file_filename()
        if not os.path.exists(os.path.split(filename)[0]):
            print('save operation cancelled')
            return
        image_pil = self.get_image_base_list_widget().currentItem().image_base.image
        image_pil.save(filename)

    def export_jpg(self):
        """
        导出为jpg格式文件
        :return:
        """
        if self.get_image_base_list_widget().currentItem() is None:
            # raise TypeError('CurrentItem is None type')
            QMessageBox.critical(self, "Save Operation Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return

        filename = self.save_file_filename('.jpg')
        if not os.path.exists(os.path.split(filename)[0]):
            print('save operation cancelled')
            return
        image_pil = self.get_image_base_list_widget().currentItem().image_base.image
        image_pil.save(filename)
        # To Fix

    def export_png_atlas(self):
        """
        打开导出精灵图集的对话框
        :return:
        """
        if self.get_image_base_list_widget().currentItem() is None:
            # raise TypeError('CurrentItem is None type')
            QMessageBox.critical(self, "Save Operation Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        try:
            dialog = AtlasExportDialog(image_base=self.get_current_image_base())
            if dialog.exec_():
                filename = self.save_file_filename()
                if not os.path.exists(os.path.split(filename)[0]):
                    print('save operation cancelled')
                    return
                atlas_img = dialog.current_atlas
                atlas_img.save(filename)
            dialog.destroy()
        except TypeError as e:
            print('type error atlas export %s' % str(e))
            return

    def export_gif(self):
        """
        打开导出GIF的对话框
        :return:
        """
        if self.get_image_base_list_widget().currentItem() is None:
            # raise TypeError('CurrentItem is None type')
            QMessageBox.critical(self, "Export Operation Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        try:
            dialog = GifExportDialog(image_base=self.get_current_image_base())
            if dialog.exec_():
                filename = self.save_file_filename('.gif')
                if not os.path.exists(os.path.split(filename)[0]):
                    print('save operation cancelled')
                    return
                anim_clip = dialog.anim_clip
                fps = dialog.fps
                save_gif_from_clip(anim_clip, filename, fps=fps, bg_color=None)
        except TypeError as e:
            print('type error atlas export %s' % str(e))
            return

    def get_current_image_base(self):
        """
        得到当前选择的ImageBase
        :return:
        """
        try:
            return self.get_image_base_list_widget().currentItem().image_base
        except AttributeError:
            return None

    def delete_current_layer(self):
        """
        删除当前层
        :return:
        """
        item = self.get_image_layer_tree_widget().currentItem()
        if item is None:
            QMessageBox.warning(self, "Delete Operation Failed", "No layer is selected",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        if item.raw_stored_image == self.get_current_image_base().root_group:
            QMessageBox.critical(self, "Delete Operation Failed", "Base layer cannot be deleted",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        try:
            item.raw_stored_image.parent.delete_raw_stored_image(item.raw_stored_image)
        except TypeError as e:
            print(e)
            return

        item.parent().removeChild(item)
        # self.init_image_tree(self.get_current_image_base())
        self.show_current_image_base_pil()

    def show_current_image_base_pil(self):
        """
        显示当前ImageBase的image
        :return:
        """
        scale_percentage = self.get_view_scale_spinbox().value()
        item = self.get_image_base_list_widget().currentItem()
        self.current_pil_image = item.image_base.image
        self.statusBar().showMessage('width:%d, height:%d' %
                                     (self.current_pil_image.width, self.current_pil_image.height))
        temp = resize_pil_image_by_percentage(item.image_base.image, scale_percentage)
        self.show_graphic_from_pil(temp)

        self.init_image_tree(item.image_base)

    def add_pix_map(self, pil_image):
        self.pix = pil_image.toqpixmap()

    def show_graphic_from_pil(self, pil_image):
        """
        在控件的GraphicsView中显示PIL图像
        :param pil_image: 要被显示的PIL图像
        :return:
        """
        pix = pil_image.toqpixmap()
        self.pix_item = QGraphicsPixmapItem(pix)
        self.scene = QGraphicsScene()
        self.scene.addItem(self.pix_item)
        self.graphicsView.setScene(self.scene)

    def show_current_tree_item_pil(self):
        """
        显示当前被选中的item的PIL图像
        :return:
        """
        scale_percentage = self.get_view_scale_spinbox().value()
        item = self.get_image_layer_tree_widget().currentItem()
        if item is None:
            return
        self.get_layer_opacity_spinbox().setValue(item.raw_stored_image.opacity)
        if self.get_view_full_size_checkbox().isChecked():
            self.current_pil_image = item.raw_stored_image.as_base_size_PIL()
        else:
            self.current_pil_image = item.raw_stored_image.final_image_as_PIL
        self.statusBar().showMessage('width:%d, height:%d' %
                                     (self.current_pil_image.width, self.current_pil_image.height))
        temp = resize_pil_image_by_percentage(self.current_pil_image, scale_percentage)
        self.show_graphic_from_pil(temp)

    def show_current_pil_image(self):
        """
        显示正在显示的PIL图像
        :return:
        """
        if self.current_pil_image is None:
            return
        scale_percentage = self.get_view_scale_spinbox().value()
        temp = resize_pil_image_by_percentage(self.current_pil_image, scale_percentage)
        self.show_graphic_from_pil(temp)

    def test_add_item(self):
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setHeaderLabels(['key', 'value'])

        root = QTreeWidgetItem(self.treeWidget)
        root.setText(0, 'root')
        self.treeWidget.setItemWidget(root, 1, self.visible_checkbox())

        child = QTreeWidgetItem(root)
        child.setText(0, '1')
        self.treeWidget.setItemWidget(child, 1, self.visible_checkbox())

        child2 = QTreeWidgetItem(child)
        child2.setText(0, '2')
        self.treeWidget.setItemWidget(child2, 1, self.visible_checkbox())

        self.treeWidget.addTopLevelItem(root)

    def visible_checkbox(self, checked=True):
        btn = QCheckBox('visible')
        btn.setChecked(checked)
        return btn

    def opacity_change(self):
        """
        透明度spinbox的槽函数
        :return:
        """
        layer_item = self.get_image_layer_tree_widget().currentItem()
        if layer_item is None:
            return
        layer_item.raw_stored_image.opacity = self.get_layer_opacity_spinbox().value()
        self.show_current_tree_item_pil()

    def to_l_mode(self):
        """
        灰阶化选项功能
        :return:
        """
        if self.get_current_image_base() is None:
            QMessageBox.critical(self, "To Greyscale Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        self.get_current_image_base().root_group.employ_operation(to_l_mode_operation)
        self.show_current_image_base_pil()

    def to_1_mode(self):
        """
        二值化选项功能
        :return:
        """
        if self.get_current_image_base() is None:
            QMessageBox.critical(self, "To Binary Failed", "No ImageBase is selected",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            return
        self.get_current_image_base().root_group.employ_operation(to_1_mode_operation)
        self.show_current_image_base_pil()

    def dock_visible_wrapper(self, dock, is_visible):
        """
        闭包，返回控制dock显示/隐藏的槽函数
        :param dock: 要被控制的dock
        :param is_visible: 让它显示还是隐藏
        :return: 槽函数
        """
        if not isinstance(dock, QDockWidget):
            raise TypeError('Not a QDockWidget type being setting visible')

        def signal():
            dock.setVisible(is_visible)
            # dock.setFloating(True)
        return signal

    def visible_change_wrapper(self, raw_stored_image, checkbox):
        """
        闭包，返回layer树中visible checkbox的槽函数
        :param raw_stored_image:
        :param checkbox:
        :return:
        """
        if not isinstance(raw_stored_image, RawStoredImage):
            raise TypeError('Not a RawStoredImage type being setting visible attr')
        if not isinstance(checkbox, QCheckBox):
            raise TypeError('not a QCheckBox type being checking to set visible attr')

        def signal():
            raw_stored_image.visible = checkbox.isChecked()
            self.show_current_tree_item_pil()
        return signal

    def tree_item_widget_from_raw_stored_image(self, raw_stored_image, parent):
        """
        把RawStoredImage翻译为TreeItemWidget
        :param raw_stored_image:
        :param parent:
        :return:
        """
        if not isinstance(raw_stored_image, RawStoredImage):
            raise TypeError('Not a RawStoredImage type being translate into TreeItemWidget')
        item = QTreeWidgetItem(parent)
        item.setText(0, raw_stored_image.name)

        checkbox = self.visible_checkbox(raw_stored_image.visible)
        checkbox.stateChanged.connect(self.visible_change_wrapper(raw_stored_image, checkbox))
        self.treeWidget.setItemWidget(item, 1, checkbox)

        item.raw_stored_image = raw_stored_image
        return item

    def layer_tree_from_image_group(self, stored_group, parent):
        """
        把StoredGroup翻译为TreeWidget的内容
        :param stored_group:
        :param parent:
        :return:
        """
        if not isinstance(stored_group, StoredGroup):
            raise TypeError('not a StoredGroup type being translate into TreeWidget')
        root = self.tree_item_widget_from_raw_stored_image(stored_group, parent)
        for stored_image in stored_group.stored_list:
            if isinstance(stored_image, StoredImage):
                self.tree_item_widget_from_raw_stored_image(stored_image, root)
            elif isinstance(stored_image, StoredGroup):
                self.layer_tree_from_image_group(stored_image, root)
        root.setText(0, 'Group')
        return root

    def pixmap_from_pil_image(self, pil_image):
        if not isinstance(pil_image, Image.Image):
            raise TypeError('not a PIL Image converting')
        return pil_image.toqpixmap()

    def init_image_tree(self, image_base):
        """
        从ImageBase生成TreeWidget的顶层内容
        :param image_base:
        :return:
        """
        self.treeWidget.setColumnCount(2)
        self.treeWidget.setHeaderLabels(['name', 'info'])
        self.treeWidget.clear()

        if not isinstance(image_base, ImageBase):
            raise TypeError('not a StoredImage type being translate into TreeWidget')

        tree = self.layer_tree_from_image_group(image_base.root_group, self.treeWidget)
        self.treeWidget.addTopLevelItem(tree)
        self.get_image_layer_tree_widget().expandAll()

    def test_image_tree(self):
        image_base = extract_image_base_of_psd(psd)
        self.init_image_tree(image_base)
        # self.show_graphic_from_pil(image_base.image)
        # self.pixmap_from_pil_image(image_base.image)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
    myWin.show()
    # myWin.test_image_tree()
    sys.exit(app.exec_())




