import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTreeWidget, 
                           QTreeWidgetItem, QVBoxLayout, QWidget,
                           QDialog, QLabel, QPushButton, QMenu,
                           QMessageBox, QSystemTrayIcon)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
import humanize
import shutil

def resource_path(relative_path):
    """获取资源的绝对路径，支持开发环境和打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是打包环境，就使用当前路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class DriveSelector(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('选择驱动器')
        self.setMinimumWidth(200)
        
        layout = QVBoxLayout()
        
        # 添加提示标签
        label = QLabel("请选择要扫描的驱动器：")
        layout.addWidget(label)
        
        # 获取所有可用驱动器并创建按钮
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                button = QPushButton(drive)
                button.clicked.connect(lambda checked, d=drive: self.on_button_clicked(d))
                layout.addWidget(button)
        
        # 创建取消按钮
        cancel = QPushButton('取消')
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)
        
        self.setLayout(layout)
        self.selected_drive = None

    def on_button_clicked(self, drive):
        self.selected_drive = drive
        self.accept()

    def get_selected_drive(self):
        return self.selected_drive

class FileSizeBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置应用图标
        app_icon = QIcon(resource_path("icon.ico"))
        self.setWindowIcon(app_icon)
        
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("文件大小浏览器")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 处理托盘图标的点击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示驱动器选择对话框
        dialog = DriveSelector()
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.get_selected_drive():
            selected_drive = dialog.get_selected_drive()
        else:
            sys.exit()
            
        self.setWindowTitle(f"文件大小浏览器 - {selected_drive}")
        self.setGeometry(100, 100, 800, 600)

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 创建树形视图
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小"])
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree)

        # 连接信号
        self.tree.itemExpanded.connect(self.on_item_expanded)

        # 添加右键菜单支持
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        # 加载选中的驱动器
        self.load_directory(selected_drive)

    def get_directory_size(self, path):
        """获取目录大小"""
        total_size = 0
        try:
            # 跳过特殊系统目录
            if any(skip_dir in path.lower() for skip_dir in ['$recycle.bin', 'system volume information']):
                return 0
                
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        try:
                            total_size += entry.stat().st_size
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                    elif entry.is_dir(follow_symlinks=False):
                        try:
                            total_size += self.get_directory_size(entry.path)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                except (PermissionError, FileNotFoundError, OSError):
                    continue
        except (PermissionError, FileNotFoundError, OSError):
            return 0
        return total_size

    def load_directory(self, path):
        """加载目录内容"""
        try:
            # 跳过特殊系统目录
            if any(skip_dir in path.lower() for skip_dir in ['$recycle.bin', 'system volume information']):
                return
                
            # 获取所有文件和文件夹
            items = []
            for entry in os.scandir(path):
                try:
                    # 跳过特殊系统目录
                    if any(skip_dir in entry.path.lower() for skip_dir in ['$recycle.bin', 'system volume information']):
                        continue
                        
                    if entry.is_file(follow_symlinks=False):
                        try:
                            size = entry.stat().st_size
                            items.append((entry.name, size, entry.path, True))
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                    elif entry.is_dir(follow_symlinks=False):
                        try:
                            size = self.get_directory_size(entry.path)
                            items.append((entry.name, size, entry.path, False))
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
                except (PermissionError, FileNotFoundError, OSError):
                    continue

            # 按大小排序
            items.sort(key=lambda x: x[1], reverse=True)

            # 清空现有项目
            self.tree.clear()

            # 添加排序后的项目
            for name, size, path, is_file in items:
                item = QTreeWidgetItem()
                item.setText(0, name)
                item.setText(1, humanize.naturalsize(size))
                item.setData(0, Qt.ItemDataRole.UserRole, path)
                
                # 设置图标
                if is_file:
                    item.setText(0, f"📄 {name}")
                else:
                    item.setText(0, f"📁 {name}")
                    # 添加一个临时子项目以显示展开箭头
                    temp = QTreeWidgetItem()
                    item.addChild(temp)
                
                self.tree.addTopLevelItem(item)

        except Exception as e:
            print(f"Error loading directory: {e}")

    def on_item_expanded(self, item):
        """处理项目展开事件"""
        # 获取路径
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        # 清除所有子项
        item.takeChildren()
        
        try:
            # 获取所有文件和文件夹
            items = []
            for entry in os.scandir(path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        items.append((entry.name, size, entry.path, True))
                    elif entry.is_dir(follow_symlinks=False):
                        size = self.get_directory_size(entry.path)
                        items.append((entry.name, size, entry.path, False))
                except (PermissionError, FileNotFoundError, OSError):
                    continue

            # 按大小排序
            items.sort(key=lambda x: x[1], reverse=True)

            # 添加排序后的子项目
            for name, size, path, is_file in items:
                child = QTreeWidgetItem()
                child.setText(0, name)
                child.setText(1, humanize.naturalsize(size))
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                
                if is_file:
                    child.setText(0, f"📄 {name}")
                else:
                    child.setText(0, f"📁 {name}")
                    # 添加临时子项目以显示展开箭头
                    temp = QTreeWidgetItem()
                    child.addChild(temp)
                
                item.addChild(child)

        except Exception as e:
            print(f"Error loading subdirectory: {e}")

    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.tree.itemAt(position)
        if item is None:
            return

        menu = QMenu()
        delete_action = menu.addAction("删除")
        
        # 获取选中项的路径
        path = item.data(0, Qt.ItemDataRole.UserRole)
        is_file = "📄" in item.text(0)  # 通过图标判断是文件还是文件夹
        
        # 显示菜单并获取选择的动作
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == delete_action:
            # 确认删除
            msg = f"确定要删除{'文件' if is_file else '文件夹'} '{item.text(0)}'吗？\n路径: {path}"
            reply = QMessageBox.question(self, '确认删除', msg,
                                       QMessageBox.StandardButton.Yes | 
                                       QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    if is_file:
                        os.remove(path)
                    else:
                        shutil.rmtree(path)
                    
                    # 删除成功后，从树中移除该项
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                        # 如果父项是文件夹，更新其大小
                        parent_path = parent.data(0, Qt.ItemDataRole.UserRole)
                        new_size = self.get_directory_size(parent_path)
                        parent.setText(1, humanize.naturalsize(new_size))
                    else:
                        # 如果是顶层项，从树的根部移除
                        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
                    
                    QMessageBox.information(self, "成功", "删除成功！")
                    
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")

    def tray_icon_activated(self, reason):
        """处理托盘图标的点击事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:  # 改为双击
            self.show()  # 显示窗口
            self.raise_()  # 将窗口提到最前
            self.activateWindow()  # 激活窗口

    def closeEvent(self, event):
        """重写关闭事件，点击关闭按钮时最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "文件大小浏览器",
            "应用程序已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,  # 修复 Icon 属性错误
            2000
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    app_icon = QIcon(resource_path("icon.ico"))
    app.setWindowIcon(app_icon)
    
    window = FileSizeBrowser()
    window.show()
    sys.exit(app.exec()) 