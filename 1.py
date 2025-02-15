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
        
        # 添加调试日志
        print("开始初始化主窗口")
        
        # 设置应用图标
        app_icon = QIcon(resource_path("icon.ico"))
        self.setWindowIcon(app_icon)
        
        # 设置窗口标题（添加版本号）
        self.setWindowTitle("文件大小浏览器 v2025/2/15-01")
        
        # 创建系统托盘图标
        self.init_tray_icon(app_icon)
        
        # 修改驱动器选择对话框的处理
        self.init_drive_selection()

    def init_tray_icon(self, app_icon):
        """初始化系统托盘图标"""
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
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def init_drive_selection(self):
        """初始化驱动器选择"""
        print("开始选择驱动器")
        dialog = DriveSelector()
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.get_selected_drive():
            selected_drive = dialog.get_selected_drive()
            print(f"用户选择了驱动器: {selected_drive}")
            
            try:
                # 创建主窗口部件
                self.init_main_window(selected_drive)
                
                # 尝试加载驱动器内容
                self.load_directory(selected_drive)
                print(f"成功加载驱动器: {selected_drive}")
                
            except Exception as e:
                print(f"错误: {str(e)}")
                QMessageBox.critical(self, "错误", f"初始化失败：{str(e)}")
                # 重新显示驱动器选择对话框
                self.init_drive_selection()
        else:
            print("用户取消了选择")
            sys.exit()

    def init_main_window(self, selected_drive):
        """初始化主窗口组件"""
        print("初始化主窗口组件")
        self.selected_drive = selected_drive
        # 修改标题，保持版本号显示
        self.setWindowTitle(f"文件大小浏览器 v2025/2/15-01 - {selected_drive}")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小"])
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree)

        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

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
        print(f"开始加载目录: {path}")
        try:
            # 先测试目录访问权限
            if not os.access(path, os.R_OK):
                print(f"无法访问目录: {path}")
                raise PermissionError(f"无法访问 {path}")

            # 获取所有文件和文件夹
            items = []
            try:
                print("尝试扫描目录")
                entries = list(os.scandir(path))
                print(f"找到 {len(entries)} 个项目")
            except PermissionError as e:
                print(f"扫描目录时权限错误: {str(e)}")
                raise PermissionError(f"无法访问 {path}")
            except Exception as e:
                print(f"扫描目录时发生错误: {str(e)}")
                raise

            # 处理每个项目
            for entry in entries:
                try:
                    if any(skip_dir in entry.path.lower() for skip_dir in ['$recycle.bin', 'system volume information']):
                        print(f"跳过系统目录: {entry.path}")
                        continue
                        
                    if entry.is_file(follow_symlinks=False):
                        try:
                            size = entry.stat().st_size
                            items.append((entry.name, size, entry.path, True))
                        except (PermissionError, FileNotFoundError, OSError) as e:
                            print(f"处理文件时出错: {entry.path} - {str(e)}")
                            continue
                    elif entry.is_dir(follow_symlinks=False):
                        try:
                            size = self.get_directory_size(entry.path)
                            items.append((entry.name, size, entry.path, False))
                        except (PermissionError, FileNotFoundError, OSError) as e:
                            print(f"处理目录时出错: {entry.path} - {str(e)}")
                            items.append((entry.name, 0, entry.path, False))
                except (PermissionError, FileNotFoundError, OSError) as e:
                    print(f"处理项目时出错: {entry.path} - {str(e)}")
                    continue

            # 更新界面
            self.update_tree_items(items)
            print("成功更新界面")

        except PermissionError as e:
            print(f"权限错误: {str(e)}")
            QMessageBox.warning(self, "权限错误", str(e))
        except Exception as e:
            print(f"未知错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载目录时出错：{str(e)}")

    def update_tree_items(self, items):
        """更新树形视图的项目"""
        # 按大小排序
        items.sort(key=lambda x: x[1], reverse=True)

        # 清空现有项目
        self.tree.clear()

        # 添加排序后的项目
        for name, size, path, is_file in items:
            item = QTreeWidgetItem()
            item.setText(0, f"{'📄' if is_file else '📁'} {name}")
            item.setText(1, humanize.naturalsize(size))
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            
            if not is_file:
                # 添加一个临时子项目以显示展开箭头
                temp = QTreeWidgetItem()
                item.addChild(temp)
            
            self.tree.addTopLevelItem(item)

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
        text = item.text(0)
        # 使用assert确保项目必须是文件或文件夹之一
        assert "📄" in text or "📁" in text, f"无效的项目类型: {text}"
        is_file = "📄" in text
        
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
        # 修改为单击就显示窗口
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)  # 取消最小化状态
            self.raise_()  # 将窗口提到最前
            self.activateWindow()  # 激活窗口

    def closeEvent(self, event):
        """重写关闭事件，点击关闭按钮时最小化到托盘"""
        event.ignore()
        self.hide()
        # 确保窗口状态正确保存
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.tray_icon.showMessage(
            "文件大小浏览器",
            "应用程序已最小化到系统托盘，单击托盘图标可以重新打开窗口",
            QSystemTrayIcon.MessageIcon.Information,
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