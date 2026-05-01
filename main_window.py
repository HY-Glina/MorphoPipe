import sys
import math  # 添加这行导入
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGroupBox, QPushButton, QComboBox, 
                            QLabel, QLineEdit, QDialog, QFormLayout, QMessageBox,
                            QFrame, QRadioButton, QButtonGroup, QSizePolicy, QGridLayout, QStackedWidget)  # 添加 QGridLayout
from PyQt5.QtCore import Qt, QEvent, QPoint
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.patches import Circle, Rectangle, Ellipse, Polygon
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint
from shapely.affinity import translate, rotate
# 导入功能模块
from periodic_deformation import deform_type4_periodic, get_periodic_function_templates
from region_deformation import (Type1DeformParamDialog, Type1CanvasInteraction, 
                              RegionDeformer, CustomShapeMenu)
# 新增：导入模块4
from module4 import Module4RegionSelector
from gcode_export import GCodeExporter
from PyQt5.QtWidgets import QMenu, QAction, QFileDialog
# 新增：导入学术绘图样式
from academic_plot_style import setup_academic_plots, style_plot, get_academic_colors

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import Qt, QEvent, QPoint, QTimer  # 添加 QTimer
class ZoomWindow(QMainWindow):
    """独立的放大查看窗口"""
    def __init__(self, parent=None, plot_type="deformed"):
        super().__init__(parent)
        self.parent = parent
        self.plot_type = plot_type
        
        # 设置窗口
        self.setWindowTitle(f"Zoom View - {plot_type}")
        self.setGeometry(200, 200, 1000, 800)
        
        # 创建中央widget和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建画布
        self.canvas = MplCanvas(self, width=10, height=8, dpi=100)
        layout.addWidget(self.canvas)
        
        # 设置单图布局
        self.setup_single_plot()
        
        # 添加工具栏
        self.add_toolbar()
        
        # 存储数据引用
        self.base_points = None
        self.deformed_points = None
        self.base_params = None
        self.type1_region = None
        self.module4_regions = None

        # 🔧 新增：区域放大相关变量
        self.zoom_mode = False
        self.zoom_start = None
        self.zoom_rect = None
        self.original_xlim = None
        self.original_ylim = None
        
        # 🔧 新增：绑定鼠标事件
        self.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_release)

    def setup_single_plot(self):
        """设置单图布局"""
        self.canvas.fig.clear()
        if self.plot_type == "3d":
            self.ax = self.canvas.fig.add_subplot(111, projection='3d')
        else:
            self.ax = self.canvas.fig.add_subplot(111)
        self.canvas.fig.tight_layout()
        
    def add_toolbar(self):
        """添加工具栏"""
        toolbar = QToolBar("Zoom Tools")
        self.addToolBar(toolbar)
        
        # 返回按钮
        back_action = QAction("Back to Main", self)
        back_action.triggered.connect(self.close)
        toolbar.addAction(back_action)
        
        # 区域放大按钮
        zoom_action = QAction("Zoom Area", self)
        zoom_action.triggered.connect(self.activate_zoom)
        toolbar.addAction(zoom_action)
        
        # 重置视图按钮
        reset_action = QAction("Reset View", self)
        reset_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_action)
        
    def update_data(self, base_points, deformed_points, base_params, type1_region, module4_regions):
        """更新数据并重绘"""
        self.base_points = base_points
        self.deformed_points = deformed_points
        self.base_params = base_params
        self.type1_region = type1_region
        self.module4_regions = module4_regions
        self.redraw_plot()
        
    def redraw_plot(self):
        """重绘图形"""
        self.ax.clear()
        
        if self.plot_type == "original" and self.base_points:
            self.draw_original()
        elif self.plot_type == "deformed" and (self.deformed_points is not None or self.base_points is not None):
            self.draw_deformed()

        elif self.plot_type == "3d":
            self.draw_3d()
        # 🔧 新增：保存原始坐标轴范围
        if self.plot_type != "3d":
            self.original_xlim = self.ax.get_xlim()
            self.original_ylim = self.ax.get_ylim()    
        self.canvas.draw()
        
    def draw_original(self):
        """绘制原始图形"""
        if not self.base_points or not self.base_params:
            return
            
        colors = self.parent.academic_colors

        split_indices = StentUtils.get_segment_split_indices(self.base_points, self.base_params['length'])
        for j in range(len(split_indices) - 1):
            start_idx = split_indices[j]
            end_idx = split_indices[j + 1]
            segment = self.base_points[start_idx:end_idx]
            if len(segment) < 2:
                continue
            x_seg, y_seg = zip(*segment)
            self.ax.plot(x_seg, y_seg, color=colors['primary_black'], alpha=0.8, linewidth=1.0)
        
        style_plot(self.ax, 'original')
        self.ax.set_title('Original Pattern (Zoom View)')
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle='--', alpha=0.3, color=colors['light_gray'])
        # 关键修复：确保等比例显示
        self.ax.set_aspect('equal')
        
    def draw_deformed(self):
        """绘制变形图形"""
        points = self.deformed_points if self.deformed_points is not None else self.base_points
        if points is None or self.base_params is None:
            return

        colors = self.parent.academic_colors

        # 🔴 修复：使用原始点集计算拆分索引，而不是变形后的点集
        split_indices = StentUtils.get_segment_split_indices(self.base_points, self.base_params['length'])
        
        for j in range(len(split_indices) - 1):
            start_idx = split_indices[j]
            end_idx = split_indices[j + 1]
            segment = points[start_idx:end_idx]  # 🔴 注意：这里仍然使用变形后的点集数据
            if len(segment) < 2:
                continue
            x_seg, y_seg = zip(*segment)
            self.ax.plot(x_seg, y_seg, color=colors['primary_blue'], alpha=0.8, linewidth=1.2)
        
        # 绘制区域边界
        if self.type1_region:
            self.draw_region_boundary(self.ax, self.type1_region, colors['primary_red'])
        
        # 绘制模块4区域
        if self.module4_regions:
            for region in self.module4_regions:
                self.draw_module4_region(self.ax, region, colors['primary_orange'])

        style_plot(self.ax, 'deformed')
        self.ax.set_title('Deformed Pattern (Zoom View)')
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle='--', alpha=0.3, color=colors['light_gray'])

        # 关键修复：确保等比例显示
        self.ax.set_aspect('equal')


    def draw_3d(self):
        """绘制3D投影"""
        if not self.base_points or not self.base_params:
            return
            
        current_points = self.deformed_points if self.deformed_points is not None else self.base_points
        unfolded = StentUtils.generate_unfolded_path(self.base_points, current_points, self.base_params)
        
        if not unfolded:
            return
            
        cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
        
        colors = self.parent.academic_colors
        x_3d = [p[0] for p in cylinder_3d]
        y_3d = [p[1] for p in cylinder_3d]
        z_3d = [p[2] for p in cylinder_3d]
        
        self.ax.scatter(x_3d, y_3d, z_3d, s=1.0, color=colors['primary_blue'], alpha=0.7)
        self.ax.set_title('3D Cylindrical Projection (Zoom View)')

        # 🔴 关键修复：确保3D坐标轴等比例显示
        max_range = max([
            max(x_3d) - min(x_3d),
            max(y_3d) - min(y_3d),
            max(z_3d) - min(z_3d)
        ]) / 2.0
        
        mid_x = (max(x_3d) + min(x_3d)) / 2.0
        mid_y = (max(y_3d) + min(y_3d)) / 2.0
        mid_z = (max(z_3d) + min(z_3d)) / 2.0
        
        self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
        self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
        self.ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # 设置3D坐标轴的纵横比
        self.ax.set_box_aspect([1, 1, 1])  # 三个方向等比例
    def draw_region_boundary(self, ax, region, color):
        """绘制区域边界"""
        # 这里需要复制 MainWindow 中的 draw_region_boundary 方法实现
        region_type = region['type'].lower()
        
        if region_type == 'circle':
            patch = patches.Circle(region['center'], region['radius'], 
                                fill=False, edgecolor=color, 
                                linestyle='--', linewidth=1.5)
            ax.add_patch(patch)
        elif region_type == 'square':
            cx, cy = region['center']
            half_side = region['side_length'] / 2
            patch = patches.Rectangle((cx-half_side, cy-half_side), 
                                    region['side_length'], region['side_length'],
                                    fill=False, edgecolor=color, 
                                    linestyle='--', linewidth=1.5)
            ax.add_patch(patch)
        elif region_type == 'ellipse':
            patch = patches.Ellipse(region['center'], 2*region['semi_major'], 2*region['semi_minor'],
                                fill=False, edgecolor=color, 
                                linestyle='--', linewidth=1.5)
            ax.add_patch(patch)
        elif region_type == 'triangle':
            vertices = region['vertices']
            vertices_closed = vertices + [vertices[0]]
            x, y = zip(*vertices_closed)
            ax.plot(x, y, linestyle='--', color=color, linewidth=1.5)
            ax.scatter([v[0] for v in vertices], [v[1] for v in vertices], 
                    c=color, s=40, alpha=0.8)
        elif region_type in ['polygon', 'custom']:
            vertices = region['vertices']
            vertices_closed = vertices + [vertices[0]]
            x, y = zip(*vertices_closed)
            ax.plot(x, y, linestyle='--', color=color, linewidth=1.5)
        
    def draw_module4_region(self, ax, region, color):
        """绘制模块4区域边界"""
        reg_type = region['type']
        centroid = region['centroid']
        
        if reg_type == 'circle':
            patch = patches.Circle(centroid, region['radius'], 
                                fill=False, edgecolor=color, 
                                linestyle='--', linewidth=1.5)
            ax.add_patch(patch)
        elif reg_type == 'rectangle':
            if 'vertices' in region:
                vertices = region['vertices']
                if vertices and vertices[0] != vertices[-1]:
                    vertices = vertices + [vertices[0]]
                patch = patches.Polygon(vertices, fill=False,
                                        edgecolor=color,          
                                        linestyle='--', linewidth=1.5)
                ax.add_patch(patch)                             
            else:
                width, height = region['width'], region['height']
                patch = patches.Rectangle(
                    (centroid[0] - width/2, centroid[1] - height/2),
                    width, height, angle=region['angle'],
                    fill=False, edgecolor=color,                
                    linestyle='--', linewidth=1.5
                )
                ax.add_patch(patch)                             
        elif reg_type == 'ellipse':
            major, minor = region['major_axis'], region['minor_axis']
            patch = patches.Ellipse(
                centroid, major, minor, angle=region['angle'],
                fill=False, edgecolor=color,                      
                linestyle='--', linewidth=1.5
            )
            ax.add_patch(patch)                                 
        elif reg_type == 'custom':
            vertices = region['vertices']
            patch = patches.Polygon(vertices, fill=False, 
                                edgecolor=color,                 
                                linestyle='--', linewidth=1.5)
            ax.add_patch(patch)                                  
        
    def activate_zoom(self):
        """激活区域放大"""
        # 实现区域放大功能
        QMessageBox.information(self, "Info", "Area zoom feature will be implemented in next version")
        
    def reset_view(self):
        """重置视图"""
        self.redraw_plot()
        
    def closeEvent(self, event):
        """关闭事件"""
        # 清理资源
        event.accept()

    # 🔧 新增：鼠标事件处理方法
    def on_mouse_press(self, event):
        """鼠标按下事件 - 开始区域选择"""
        if not self.zoom_mode or event.inaxes != self.ax or event.button != 1:
            return
            
        # 记录起始点
        self.zoom_start = (event.xdata, event.ydata)
        self.zoom_rect = None
        
    def on_mouse_move(self, event):
        """鼠标移动事件 - 绘制选择矩形"""
        if not self.zoom_mode or self.zoom_start is None or event.inaxes != self.ax:
            return
            
        # 移除之前的矩形
        if self.zoom_rect:
            self.zoom_rect.remove()
            
        # 绘制新矩形
        x0, y0 = self.zoom_start
        x1, y1 = event.xdata, event.ydata
        
        width = x1 - x0
        height = y1 - y0
        
        self.zoom_rect = patches.Rectangle(
            (x0, y0), width, height,
            fill=False, edgecolor='red', linewidth=2, linestyle='--'
        )
        self.ax.add_patch(self.zoom_rect)
        self.canvas.draw_idle()
        
    def on_mouse_release(self, event):
        """鼠标释放事件 - 执行区域放大"""
        if not self.zoom_mode or self.zoom_start is None or event.inaxes != self.ax:
            return
            
        # 获取选择区域
        x0, y0 = self.zoom_start
        x1, y1 = event.xdata, event.ydata
        
        # 计算区域边界
        x_min = min(x0, x1)
        x_max = max(x0, x1)
        y_min = min(y0, y1)
        y_max = max(y0, y1)
        
        # 确保区域有效
        if abs(x_max - x_min) > 0.1 and abs(y_max - y_min) > 0.1:
            # 设置新的显示范围
            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(y_min, y_max)
            self.canvas.draw()
            
            # 显示放大信息
            QMessageBox.information(self, "Zoom Applied", 
                                  f"Zoomed to area:\n"
                                  f"X: {x_min:.2f} to {x_max:.2f}\n"
                                  f"Y: {y_min:.2f} to {y_max:.2f}")
        
        # 清理选择状态
        self.zoom_start = None
        if self.zoom_rect:
            self.zoom_rect.remove()
            self.zoom_rect = None
            
        # 退出区域放大模式
        self.zoom_mode = False
        
    def activate_zoom(self):
        """激活区域放大模式"""
        if self.plot_type == "3d":
            QMessageBox.warning(self, "Warning", "Area zoom is not available for 3D view.")
            return
            
        self.zoom_mode = True
        self.zoom_start = None
        self.zoom_rect = None
        
        # 改变光标样式提示用户
        self.setCursor(Qt.CrossCursor)
        QMessageBox.information(self, "Zoom Area", 
                              "Click and drag on the plot to select an area to zoom in.\n\n"
                              "Release the mouse button to apply zoom.")
        
    def reset_view(self):
        """重置视图到原始显示范围"""
        if self.original_xlim and self.original_ylim and self.plot_type != "3d":
            # 恢复原始坐标轴范围
            self.ax.set_xlim(self.original_xlim)
            self.ax.set_ylim(self.original_ylim)
            self.canvas.draw()
            
            # 恢复光标样式
            self.setCursor(Qt.ArrowCursor)
            
            QMessageBox.information(self, "View Reset", "View has been reset to original scale.")
        else:
            # 如果无法重置坐标轴，则重新绘制
            self.redraw_plot()
            
    def closeEvent(self, event):
        """关闭事件 - 确保光标恢复正常"""
        self.setCursor(Qt.ArrowCursor)
        event.accept()
# ------------------- 级联下拉框类（新增） -------------------
class CascadingComboBox(QComboBox):
    """支持级联菜单的下拉框 - 最终修复版本"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.custom_submenu = None
        self.current_custom_mode = "line"  # 默认模式
        self.is_submenu_visible = False
        
        self.setup_custom_submenu()
        
        # 设置鼠标追踪
        self.setMouseTracking(True)
        
    def setup_custom_submenu(self):
        """设置Custom选项的次级菜单"""
        self.custom_submenu = QMenu(self)
        self.custom_submenu.setObjectName("cascadingMenu")
        
        self.custom_line_action = QAction("Line", self)
        self.custom_curve_action = QAction("Curve", self)
        
        self.custom_submenu.addAction(self.custom_line_action)
        self.custom_submenu.addAction(self.custom_curve_action)
        
        # 连接菜单动作信号
        self.custom_line_action.triggered.connect(self.on_custom_line_selected)
        self.custom_curve_action.triggered.connect(self.on_custom_curve_selected)
        
        # 设置菜单样式
        self.custom_submenu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #e6f3ff;
                color: #0066cc;
            }
        """)

    def showPopup(self):
        """重写显示下拉框的方法"""
        super().showPopup()
        # 安装事件过滤器到视图
        view = self.view()
        if view and view.viewport():
            view.viewport().installEventFilter(self)
            view.setMouseTracking(True)

    def eventFilter(self, obj, event):
        """事件过滤器：处理鼠标悬停显示次级菜单"""
        try:
            # 只处理下拉列表视口的事件
            if obj != self.view().viewport():
                return super().eventFilter(obj, event)
                
            if event.type() == QEvent.MouseMove:
                # 获取鼠标位置对应的索引
                index = self.view().indexAt(event.pos())
                if index.isValid():
                    item_text = self.itemText(index.row())
                    if item_text == "Custom":
                        # 显示次级菜单
                        if not self.is_submenu_visible:
                            self.show_custom_submenu(index)
                        return False  # 让默认的高亮行为继续
                    else:
                        self.hide_custom_submenu()
                else:
                    self.hide_custom_submenu()
                    
            elif event.type() == QEvent.Leave:
                # 鼠标离开视图时延迟隐藏次级菜单
                QTimer.singleShot(300, self.hide_custom_submenu)
                
            elif event.type() == QEvent.MouseButtonPress:
                # 处理鼠标点击
                index = self.view().indexAt(event.pos())
                if index.isValid() and self.itemText(index.row()) == "Custom":
                    # 对于Custom项，显示次级菜单而不是改变选择
                    self.show_custom_submenu(index)
                    return True  # 阻止默认选择行为
                    
        except Exception as e:
            print(f"事件过滤器错误: {e}")
            
        return super().eventFilter(obj, event)

    def show_custom_submenu(self, index):
        """显示Custom选项的次级菜单"""
        if not self.custom_submenu:
            return
            
        try:
            # 保持当前选项高亮
            self.view().setCurrentIndex(index)
            
            # 获取Custom项在屏幕上的位置
            rect = self.view().visualRect(index)
            global_pos = self.view().mapToGlobal(rect.bottomRight())
            
            # 调整位置，确保次级菜单显示在右侧
            global_pos.setX(global_pos.x() + 5)
            
            # 显示次级菜单
            self.custom_submenu.popup(global_pos)
            self.is_submenu_visible = True
            
        except Exception as e:
            print(f"显示次级菜单错误: {e}")

    def hide_custom_submenu(self):
        """隐藏次级菜单"""
        if self.custom_submenu and self.is_submenu_visible:
            self.custom_submenu.hide()
            self.is_submenu_visible = False

    def on_custom_line_selected(self):
        """处理Line选项选择 - 修复版本"""
        try:
            print("Line模式被选择")  # 调试信息
            self.current_custom_mode = "line"
            
            # 设置当前选中项为Custom
            self.setCurrentText("Custom")
            
            # 通知父组件
            if hasattr(self.parent(), 'on_custom_mode_selected'):
                self.parent().on_custom_mode_selected("line")
                
            self.hide_custom_submenu()
            self.hidePopup()  # 关闭主下拉框
            
        except Exception as e:
            print(f"Custom line selected error: {e}")

    def on_custom_curve_selected(self):
        """处理Curve选项选择 - 修复版本"""
        try:
            print("=== Curve模式被选择 ===")
            self.current_custom_mode = "curve"
            print(f"下拉框内部模式设置为: {self.current_custom_mode}")
            
            # 设置当前选中项为Custom
            self.setCurrentText("Custom")
            
            # 通知父组件
            if hasattr(self.parent(), 'on_custom_mode_selected'):
                print(f"调用父组件的on_custom_mode_selected: curve")
                self.parent().on_custom_mode_selected("curve")
            else:
                print("警告：父组件没有on_custom_mode_selected方法")
                
            self.hide_custom_submenu()
            self.hidePopup()  # 关闭主下拉框
            
        except Exception as e:
            print(f"Custom curve selected error: {e}")
            import traceback
            traceback.print_exc()

    def hidePopup(self):
        """重写隐藏下拉框的方法"""
        self.hide_custom_submenu()
        super().hidePopup()

    def set_custom_mode_callback(self, callback):
        """设置自定义模式选择的回调函数"""
        self.custom_mode_callback = callback

    def on_custom_line_selected(self):
        """处理Line选项选择 - 修复版本"""
        try:
            print("=== Line模式被选择 ===")
            self.current_custom_mode = "line"
            print(f"下拉框内部模式设置为: {self.current_custom_mode}")
            
            # 设置当前选中项为Custom
            self.setCurrentText("Custom")
            
            # 使用回调函数通知
            if hasattr(self, 'custom_mode_callback') and self.custom_mode_callback:
                print(f"通过回调调用: line")
                self.custom_mode_callback("line")
            else:
                print("警告：没有设置自定义模式回调函数")
                
            self.hide_custom_submenu()
            self.hidePopup()  # 关闭主下拉框
            
        except Exception as e:
            print(f"Custom line selected error: {e}")
            import traceback
            traceback.print_exc()

    def on_custom_curve_selected(self):
        """处理Curve选项选择 - 修复版本"""
        try:
            print("=== Curve模式被选择 ===")
            self.current_custom_mode = "curve"
            print(f"下拉框内部模式设置为: {self.current_custom_mode}")
            
            # 设置当前选中项为Custom
            self.setCurrentText("Custom")
            
            # 使用回调函数通知
            if hasattr(self, 'custom_mode_callback') and self.custom_mode_callback:
                print(f"通过回调调用: curve")
                self.custom_mode_callback("curve")
            else:
                print("警告：没有设置自定义模式回调函数")
                
            self.hide_custom_submenu()
            self.hidePopup()  # 关闭主下拉框
            
        except Exception as e:
            print(f"Custom curve selected error: {e}")
            import traceback
            traceback.print_exc()
# ------------------- 基础图形生成工具类（新增片段拆分方法） -------------------
class StentUtils:
    @staticmethod
    def generate_original_points(custom_params=None):
        """生成基础菱形图案点列"""
        default_params = {
            'd': 28.0499,
            'width': 25.0,
            'length': 31.4159,
            'max_cycles': 28,
            'point_spacing': 0.1,
            'min_spacing': 0.00001
        }
        
        final_params = default_params.copy()
        if custom_params:
            for key, value in custom_params.items():
                if key in final_params:
                    final_params[key] = value
        
        points = []
        current_x, current_y = 0.0, 0.0
        direction = 1  # 1 for right, -1 for left
        
        for _ in range(final_params['max_cycles']):
            target_x = final_params['width'] if direction == 1 else 0.0
            remaining_d = final_params['d']
            
            while True:
                target_y = current_y - remaining_d
                if target_y >= -final_params['length']:
                    # 生成线段点
                    dx = target_x - current_x
                    dy = target_y - current_y
                    line_length = np.hypot(dx, dy)
                    num_points = int(line_length / final_params['point_spacing']) + 1
                    
                    for i in range(num_points):
                        x = current_x + (dx * i) / num_points
                        y = current_y + (dy * i) / num_points
                        points.append((round(x, 3), round(y, 3)))
                    
                    current_x, current_y = target_x, target_y
                    break
                else:
                    # 计算与底部边界的交点
                    k = (target_y - current_y) / (target_x - current_x) if (target_x - current_x) != 0 else 0
                    x_intersect = current_x - (current_y + final_params['length']) / k if k != 0 else current_x
                    
                    # 生成到边界的线段
                    dx = x_intersect - current_x
                    dy = -final_params['length'] - current_y
                    line_length = np.hypot(dx, dy)
                    num_points = int(line_length / final_params['point_spacing']) + 1
                    
                    for i in range(num_points):
                        x = current_x + (dx * i) / num_points
                        y = current_y + (dy * i) / num_points
                        points.append((round(x, 3), round(y, 3)))
                    
                    remaining_d -= (current_y + final_params['length'])
                    current_x, current_y = x_intersect, 0.0
            
            direction *= -1
            
        return points, final_params

    @staticmethod
    def generate_unfolded_path(original_points, deformed_folded, params):
        """生成展开路径（确保长条状显示）"""
        unfolded = []
        y_offset = 0.0
        length = params['length']
        threshold = length * 0.95  # 检测周期结束的阈值
        
        for i, ((x_orig, y_orig), (x_def, y_def)) in enumerate(zip(original_points, deformed_folded)):
            # 检测周期结束点（从底部边界回到顶部）
            if i > 0:
                prev_y_orig = original_points[i-1][1]
                if (prev_y_orig < -threshold) and (y_orig > -0.1):
                    y_offset -= length  # 累加偏移量
            
            # 计算展开后的Y坐标
            unfolded_y = y_def + y_offset
            unfolded.append((round(x_def, 3), round(unfolded_y, 3)))
            
        return unfolded

    @staticmethod
    def project_to_cylinder(unfolded_points, params):
        """投影到3D圆柱面"""
        radius = params['length'] / (2 * np.pi)
        cycle_length = params['length']
        
        cylinder_points = []
        for x, y in unfolded_points:
            y_in_cycle = y % (-cycle_length)
            theta = 2 * np.pi * (1 + y_in_cycle / cycle_length)
            
            x_3d = radius * np.cos(theta)
            y_3d = radius * np.sin(theta)
            z_3d = x
            
            cylinder_points.append((round(x_3d, 3), round(y_3d, 3), round(z_3d, 3)))
            
        return cylinder_points

    @staticmethod
    def get_segment_split_indices(points, length):
        """新增：根据Y值突变生成片段拆分索引（避免跨跳转连接）"""
        split_indices = [0]
        if len(points) < 2:
            split_indices.append(len(points))
            return split_indices
        
        # 识别“下边界（≤-length*0.99）→上边界（≥-0.01）”的跳转点
        for i in range(1, len(points)):
            prev_y = points[i-1][1]
            curr_y = points[i][1]
            if prev_y <= -length * 0.99 and curr_y >= -0.01:
                split_indices.append(i)
        
        split_indices.append(len(points))
        return split_indices
        
    @staticmethod
    def calculate_d_from_angle(theta_deg, n, width, length):
        """根据角度θ和整数n计算d值"""
        import math
        
        theta = math.radians(theta_deg)
        
        # 计算d_target = tanθ * width
        d_target = math.tan(theta) * width
        
        # 计算差值
        diff = d_target - length
        
        # 确定φ值
        if diff < 0:
            phi = 0
        else:
            phi = int(diff // length) + 1
        
        # 计算理论的小数部分
        frac = d_target / length - phi
        
        # 计算理论k值
        k_theory = frac * n
        
        # 在k_theory附近寻找与n互质的整数k
        def find_coprime_near(n, target_k):
            target_k = max(1, min(n-1, target_k))
            
            for offset in range(0, min(target_k, n-target_k)):
                # 检查较小的方向
                k = target_k - offset
                if k > 0 and math.gcd(k, n) == 1:
                    return k
                
                # 检查较大的方向
                k = target_k + offset
                if k < n and math.gcd(k, n) == 1:
                    return k
            
            for k in range(1, n):
                if math.gcd(k, n) == 1:
                    return k
            
            return 1
        
        k = find_coprime_near(n, round(k_theory))
        
        # 计算最终的d值
        d_final = (phi + k / n) * length
        
        return d_final, {
            'theta': theta,
            'theta_deg': theta_deg,
            'n': n,
            'd_target': d_target,
            'phi': phi,
            'k': k,
            'd_final': d_final
        }
# ------------------- 区域变形专用界面组件 -------------------
class Type1RegionSelectWidget(QWidget):
    """类型①：区域变形的控件组（独立组件）"""
    def __init__(self, parent=None, on_select_region=None, on_select_deform=None, on_confirm=None):
        super().__init__(parent)
        self.parent = parent  # 主窗口引用
        # 回调函数
        self.on_select_region = on_select_region  # 选择区域形状时的回调
        self.on_select_deform = on_select_deform  # 选择变形类型时的回调
        self.on_confirm = on_confirm              # 点击"确认变形"时的回调
        
        # 存储当前自定义模式
        self.current_custom_mode = "line"  # 默认值
        
        self.init_ui()

    def update_deform_combo_by_region(self):
        region_type = self.region_combo.currentText()
        index = self.deform_combo.findText("Rectangular Scaling")
        if index >= 0:
            # 允许正方形（Square）使用该变形
            self.deform_combo.model().item(index).setEnabled(region_type in ["Rectangle", "Square"])
            if self.deform_combo.currentText() == "Rectangular Scaling" and region_type not in ["Rectangle", "Square"]:
                self.deform_combo.setCurrentIndex(0)



    def init_ui(self):
        """初始化控件布局"""
        # 外层分组框
        self.type1_group = QGroupBox("3. Deformation Localization")
        
        # 设置尺寸策略，确保宽度扩展
        self.type1_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.main_layout = QVBoxLayout(self.type1_group)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setSpacing(10)

        # 区域形状选择 - 使用自定义级联下拉框
        self.region_label = QLabel("Region Shape")
        self.region_combo = CascadingComboBox(self)  # 使用自定义下拉框
        
        # 添加选项
        self.region_combo.addItems(["Circle", "Square", "Ellipse", "Triangle", "Custom"])
        self.region_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 关键修复：直接设置回调函数，而不是依赖父组件查找
        self.region_combo.set_custom_mode_callback(self.on_custom_mode_selected)
        
        # 连接主下拉框的选择事件
        self.region_combo.currentIndexChanged.connect(
            lambda: self.on_select_region(self.region_combo.currentText())
        )
        self.region_combo.currentIndexChanged.connect(
            lambda: self.update_deform_combo_by_region()
        )
        # 关键：确保事件过滤器在创建后立即安装
        self.region_combo.view().viewport().installEventFilter(self.region_combo)
        
        form_layout.addRow(self.region_label, self.region_combo)

        # 变形类型选择
        self.deform_label = QLabel("Deform Type")
        self.deform_combo = QComboBox()
        self.deform_combo.addItems([
            "Scaling", "Sine", "Twist",
            "Exponential Expansion", "Polar Wave", "Biaxial Sine Ripple",
            "Rectangular Scaling"
        ])
        self.deform_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.deform_combo.currentIndexChanged.connect(
            lambda: self.on_select_deform(self.deform_combo.currentText())
        )
        form_layout.addRow(self.deform_label, self.deform_combo)

        # 将表单布局添加到主布局
        self.main_layout.addLayout(form_layout)

        # 操作按钮
        self.btn_layout = QHBoxLayout()
        self.select_region_btn = QPushButton("Select Region")
        self.select_region_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.select_region_btn.clicked.connect(self.trigger_canvas_select)

        self.confirm_deform_btn = QPushButton("Apply Deformation")
        self.confirm_deform_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.confirm_deform_btn.clicked.connect(
            lambda: self.on_confirm(
                self.region_combo.currentText(), 
                self.deform_combo.currentText()
            )
        )
        self.confirm_deform_btn.setEnabled(False)
        self.btn_layout.addWidget(self.select_region_btn)
        self.btn_layout.addWidget(self.confirm_deform_btn)
        self.main_layout.addLayout(self.btn_layout)

        # 状态提示
        self.status_label = QLabel("Status: Select region first")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # 设置当前组件布局
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(self.type1_group)
        
        # 设置整个widget的尺寸策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


    def trigger_canvas_select(self):
        """触发画布的区域选择模式"""
        print(f"=== 触发画布选择 ===")
        print(f"当前自定义模式: {self.current_custom_mode}")
        print(f"下拉框当前文本: {self.region_combo.currentText()}")
        print(f"下拉框模式: {self.region_combo.current_custom_mode}")
        
        if self.parent and hasattr(self.parent, "enter_type1_select_mode"):
            region_type = self.region_combo.currentText()
            
            # 如果是Custom类型，传递当前选择的模式
            if region_type == "Custom":
                # 确保画布交互对象知道当前模式
                if hasattr(self.parent, "type1_canvas_interaction"):
                    print(f"设置画布交互模式为: {self.current_custom_mode}")
                    self.parent.type1_canvas_interaction.custom_mode = self.current_custom_mode
            
            self.parent.enter_type1_select_mode(region_type)

    def update_status(self, status_text):
        """更新状态提示"""
        self.status_label.setText(f"Status: {status_text}")

    def disable_confirm_btn(self, disable):
        """禁用/启用"确认变形"按钮"""
        self.confirm_deform_btn.setDisabled(disable)

    def on_custom_mode_selected(self, mode):
        """处理自定义模式选择 - 修复版本"""
        print(f"自定义模式选择回调: {mode}")  # 重要调试信息
        
        # 存储当前模式到两个地方
        self.current_custom_mode = mode
        self.region_combo.current_custom_mode = mode  # 确保下拉框也更新
        
        print(f"当前自定义模式已设置为: {self.current_custom_mode}")  # 调试信息
        print(f"下拉框模式已设置为: {self.region_combo.current_custom_mode}")  # 调试信息
        
        # 确保下拉框显示为Custom
        self.region_combo.setCurrentText("Custom")
        
        # 更新画布交互模式
        if self.parent and hasattr(self.parent, "type1_canvas_interaction"):
            self.parent.type1_canvas_interaction.custom_mode = mode
            print(f"画布交互模式已设置为: {mode}")  # 调试信息
            
        # 更新状态提示
        mode_display = "Line" if mode == "line" else "Curve"
        self.update_status(f"Region shape: Custom ({mode_display}) - click 'Select Region' to draw")
        
        # 调用原有的区域选择回调
        if self.on_select_region:
            self.on_select_region("Custom")
# ------------------- Matplotlib画布类 -------------------
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # 清除之前的子图
        self.fig.clear()
        
        # 创建子图（原有代码保持不变）
        rect1 = [0.08, 0.54, 0.38, 0.38]
        rect2 = [0.54, 0.54, 0.38, 0.38]
        rect3 = [0.33, 0.07, 0.38, 0.38]
        
        self.axes = [
            self.fig.add_axes(rect1),
            self.fig.add_axes(rect2),
            self.fig.add_axes(rect3, projection='3d')
        ]
        
        # 设置画布背景颜色
        self.fig.patch.set_facecolor('white')
        
        # 🔧 新增：添加logo水印
        self.add_logo_watermark()
    
    def add_logo_watermark(self):
        """在画布中心添加半透明logo水印"""
        try:
            # 加载logo图片（替换为您的logo文件路径）
            logo_path = r"C:\Users\HY\Desktop\支架图案设计软件\university_logo.png"  # 或者 "logo.svg", "logo.jpg"
            logo_img = plt.imread(logo_path)
            
            # 计算logo大小（根据画布尺寸调整）
            logo_size = 0.2  # 占画布宽度的20%
            
            # 在画布中心添加logo
            # 使用fig.add_axes在画布级别添加，而不是子图级别
            margin = 0.02  # 距离边缘的边距
            logo_ax = self.fig.add_axes([1 - logo_size - margin, margin, 
                                        logo_size, logo_size], 
                                    zorder=-1)
            
            # 显示logo图片
            logo_ax.imshow(logo_img, alpha=0.8)  # 设置透明度
            
            # 隐藏坐标轴
            logo_ax.axis('off')
            
            # 设置logo轴背景透明
            logo_ax.patch.set_alpha(0)
            
        except Exception as e:
            print(f"无法加载logo图片: {e}")
            # 如果logo加载失败，可以添加文字水印作为备选
            self.add_text_watermark()
    
    def add_text_watermark(self):
        """备选方案：添加文字水印"""
        text_ax = self.fig.add_axes([0, 0, 1, 1], zorder=-1000)
        text_ax.text(0.5, 0.5, "YOUR LOGO", 
                    fontsize=40, alpha=0.1, 
                    ha='center', va='center', 
                    rotation=30, transform=text_ax.transAxes)
        text_ax.axis('off')
        text_ax.patch.set_alpha(0)
# ------------------- 对话框类 -------------------
class BasePatternDialogEx(QDialog):
    """扩展的基础图形参数对话框（支持两种输入模式）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Base Pattern Parameters")
        self.setMinimumWidth(450)  # 增加宽度
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # 模式选择区域
        mode_group = QGroupBox("Input Mode")
        mode_layout = QHBoxLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Direct Input (5 parameters)")
        self.mode_combo.addItem("Angle Calculation (θ and n)")
        self.mode_combo.currentIndexChanged.connect(self.switch_mode)
        
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        
        # 创建堆叠布局
        self.stacked_widget = QStackedWidget()
        
        # 页面1：直接输入模式
        self.page1 = self.create_direct_input_page()
        self.stacked_widget.addWidget(self.page1)
        
        # 页面2：角度计算模式
        self.page2 = self.create_angle_calculation_page()
        self.stacked_widget.addWidget(self.page2)
        
        main_layout.addWidget(self.stacked_widget)
        
        # 信息标签（显示计算出的d值）
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)  # 自动换行
        self.info_label.setStyleSheet("""
            color: blue; 
            font-weight: bold; 
            background-color: #F0F8FF;
            padding: 5px;
            border: 1px solid #B0C4DE;
            border-radius: 3px;
        """)
        self.info_label.setMinimumHeight(40)  # 确保有足够高度
        main_layout.addWidget(self.info_label)
        
        # 按钮
        self.generate_btn = QPushButton("Generate Base Pattern")
        self.generate_btn.clicked.connect(self.accept)
        main_layout.addWidget(self.generate_btn)
        
        # 初始化当前模式
        self.current_mode = 0
        self.switch_mode(0)
    
    def create_direct_input_page(self):
        """创建直接输入模式页面"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.d_input = QLineEdit("28.0499")
        self.width_input1 = QLineEdit("25.0")
        self.length_input1 = QLineEdit("31.4159")
        self.cycles_input1 = QLineEdit("28")
        self.spacing_input1 = QLineEdit("0.1")
        
        layout.addRow("Ly (mm):", self.d_input)
        layout.addRow("Axial/Lx (mm):", self.width_input1)
        layout.addRow("Circumferential (mm):", self.length_input1)
        layout.addRow("Max cycles:", self.cycles_input1)
        layout.addRow("Point spacing (mm):", self.spacing_input1)
        
        return widget
    
    def create_angle_calculation_page(self):
        """创建角度计算模式页面"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.theta_input = QLineEdit("48.29")
        self.n_input = QLineEdit("28")
        self.width_input2 = QLineEdit("25.0")
        self.length_input2 = QLineEdit("31.4159")
        self.cycles_input2 = QLineEdit("28")
        self.spacing_input2 = QLineEdit("0.1")
        
        # 连接信号，当θ或n变化时重新计算d
        self.theta_input.textChanged.connect(self.calculate_d_from_angle)
        self.n_input.textChanged.connect(self.calculate_d_from_angle)
        self.width_input2.textChanged.connect(self.calculate_d_from_angle)
        self.length_input2.textChanged.connect(self.calculate_d_from_angle)
        
        layout.addRow("Winding angle θ (deg):", self.theta_input)
        layout.addRow("Pivot point n:", self.n_input)
        layout.addRow("Axial/Lx (mm):", self.width_input2)
        layout.addRow("Circumferential (mm):", self.length_input2)
        layout.addRow("Max cycles:", self.cycles_input2)
        layout.addRow("Point spacing (mm):", self.spacing_input2)
        
        return widget
    
    def switch_mode(self, index):
        """切换输入模式"""
        self.stacked_widget.setCurrentIndex(index)
        self.current_mode = index
        
        if index == 0:  # 直接输入模式
            self.info_label.setText("")
        else:  # 角度计算模式
            self.calculate_d_from_angle()
    
    def calculate_d_from_angle(self):
        """根据角度θ和n计算d值"""
        if self.current_mode != 1:
            return
            
        try:
            theta_deg = float(self.theta_input.text())
            n = int(self.n_input.text())
            width = float(self.width_input2.text())
            length = float(self.length_input2.text())
            
            d_final, calc_info = StentUtils.calculate_d_from_angle(theta_deg, n, width, length)
            
            # 优化显示格式，分成两行
            # info_text = f"Calculated d = {d_final:.4f}\n"
            # info_text += f"θ={theta_deg}°, n={n}, φ={calc_info['phi']}, k={calc_info['k']}"
            info_text = f"Calculated d = {d_final:.4f}, θ={theta_deg}°, n={n}, φ={calc_info['phi']}, k={calc_info['k']}"
            self.info_label.setText(info_text)
            
        except ValueError:
            self.info_label.setText("Please enter valid numbers for θ and n")
    
    def get_params(self):
        """获取用户输入的参数"""
        try:
            if self.current_mode == 0:  # 直接输入模式
                return {
                    'd': float(self.d_input.text()),
                    'width': float(self.width_input1.text()),
                    'length': float(self.length_input1.text()),
                    'max_cycles': int(self.cycles_input1.text()),
                    'point_spacing': float(self.spacing_input1.text())
                }
            else:  # 角度计算模式
                theta_deg = float(self.theta_input.text())
                n = int(self.n_input.text())
                width = float(self.width_input2.text())
                length = float(self.length_input2.text())
                
                # 计算d值
                d_final, _ = StentUtils.calculate_d_from_angle(theta_deg, n, width, length)
                
                return {
                    'd': d_final,
                    'width': width,
                    'length': length,
                    'max_cycles': int(self.cycles_input2.text()),
                    'point_spacing': float(self.spacing_input2.text()),
                    'theta_deg': theta_deg,
                    'n': n
                }
                
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None

class PeriodicFunctionDialog(QDialog):
    """周期性变形参数对话框"""
    def __init__(self, deform_dimension, mode, parent=None, default_x_expr=None, default_y_expr=None):
        super().__init__(parent)
        self.deform_dimension = deform_dimension
        self.mode = mode  # "preset" 或 "custom"
        self.setWindowTitle(f"Periodic Deformation - {mode.capitalize()} Mode")
        self.setMinimumWidth(550)
        
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # 模式选择区域
        self.mode_group = QGroupBox("Function Mode")
        self.mode_group.setMinimumHeight(80)
        self.mode_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(10)
        mode_layout.setContentsMargins(5, 5, 5, 5)
        
        self.preset_radio = QRadioButton("Preset Functions")
        self.custom_radio = QRadioButton("Custom Function")
        self.preset_radio.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.custom_radio.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.preset_radio)
        self.radio_group.addButton(self.custom_radio)
        self.preset_radio.setChecked(True)
        self.radio_group.buttonClicked.connect(self.update_mode)
        
        mode_layout.addWidget(self.preset_radio)
        mode_layout.addWidget(self.custom_radio)
        mode_layout.addStretch()
        
        self.mode_group.setLayout(mode_layout)
        self.main_layout.addWidget(self.mode_group)
        # 根据传入的 mode 设置选中的单选按钮
        if self.mode == "preset":
            self.preset_radio.setChecked(True)
        else:  # custom
            self.custom_radio.setChecked(True)
        # 隐藏整个模式选择分组框
        self.mode_group.setVisible(False)
        # 周期参数控件
        self.period_n_input = QLineEdit()
        self.period_n_input.setPlaceholderText("Enter number of periods")
        self.period_dir_combo = QComboBox()
        self.period_dir_combo.addItems(["length", "width"])
        
        # 预设函数区域
        self.preset_widget = QWidget()
        self.preset_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        preset_layout = QVBoxLayout(self.preset_widget)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        
        self.func_combo = QComboBox()
        for tid, name_with_expr in get_periodic_function_templates(deform_dimension):
            self.func_combo.addItem(name_with_expr, tid)
        self.func_combo.currentIndexChanged.connect(self.update_preset_params)
        preset_layout.addWidget(QLabel("Select function template:"))
        preset_layout.addWidget(self.func_combo)
        
        self.params_frame = QFrame()
        self.params_layout = QFormLayout(self.params_frame)
        self.param_inputs = {}
        preset_layout.addWidget(self.params_frame)
        
        # 周期参数区域 - 标签和输入框
        self.period_label = QLabel("Period parameters:")
        preset_layout.addWidget(self.period_label)

        self.period_params_frame = QFrame()
        period_params_layout = QFormLayout(self.period_params_frame)
        self.period_n_input = QLineEdit()
        self.period_n_input.setPlaceholderText("Enter number of periods")
        self.period_dir_label = QLabel("circumference")
        period_params_layout.addRow("Number of periods:", self.period_n_input)
        period_params_layout.addRow("Period direction:", self.period_dir_label)
        preset_layout.addWidget(self.period_params_frame)

        # 添加蓝色提示标签（初始隐藏）
        self.note_label = QLabel()
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("color: blue; font-weight: bold;")
        preset_layout.addWidget(self.note_label)
        self.note_label.hide()
        
        self.main_layout.addWidget(self.preset_widget)

        # 自定义函数区域（简化版，无参数输入）
        self.custom_widget = QWidget()
        self.custom_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        custom_layout = QVBoxLayout(self.custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)

        custom_layout.addWidget(QLabel("X deformation expression:"))
        self.x_expr_input = QLineEdit(default_x_expr if default_x_expr else "x + 0.5*sin(0.4*x)")
        custom_layout.addWidget(self.x_expr_input)
        
        custom_layout.addWidget(QLabel("Y deformation expression:"))
        self.y_expr_input = QLineEdit(default_y_expr if default_y_expr else "y")
        custom_layout.addWidget(self.y_expr_input)

        # 提示信息
        hint_label = QLabel("Supported: x, y, sin, cos, tan, exp, log, sqrt, pi, +, -, *, /, **")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 9pt;")
        custom_layout.addWidget(hint_label)

        # 周期参数（保留）
        self.custom_period_n_input = QLineEdit("2")
        self.custom_period_dir_label = QLabel("circumference")

        custom_period_frame = QFrame()
        custom_period_layout = QFormLayout(custom_period_frame)
        custom_period_layout.addRow("Number of periods:", self.custom_period_n_input)
        custom_period_layout.addRow("Period direction:", self.custom_period_dir_label)

        custom_layout.addWidget(QLabel("Period parameters:"))
        custom_layout.addWidget(custom_period_frame)

        self.main_layout.addWidget(self.custom_widget)
        
        # 生成按钮
        self.generate_btn = QPushButton("Generate Deformation")
        self.generate_btn.clicked.connect(self.accept)
        self.main_layout.addWidget(self.generate_btn)
        
        # 初始化模式显示
        self.update_mode()
        self.update_preset_params()
        self.custom_param_count = 0
        self.init_ui_by_mode()  # 调用新的初始化方法
    def update_mode(self):
        """更新模式显示"""
        is_preset = self.preset_radio.isChecked()
        self.preset_widget.setVisible(is_preset)
        self.custom_widget.setVisible(not is_preset)
        self.adjustSize()
        
        if not is_preset:
            self.custom_mode_size = self.size()
        elif is_preset and hasattr(self, 'custom_mode_size'):
            current_height = self.size().height()
            self.resize(self.custom_mode_size.width(), current_height)
    
    def update_preset_params(self):
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)
        self.param_inputs.clear()
        
        template_id = self.func_combo.currentData()
        if not template_id:
            return
            
        from periodic_deformation import PERIODIC_FUNCTION_TEMPLATES
        template = PERIODIC_FUNCTION_TEMPLATES[template_id]
        
        if template_id == 6:
            # 隐藏周期参数，显示蓝色提示
            self.period_label.hide()
            self.period_params_frame.hide()
            self.note_label.setText(
                'Note: "W" stands for "Width." Setting "boundary_strength = 1" '
                'limits deformation to the original dimensions, while "boundary_strength = 0" '
                'imposes no restrictions on the size after deformation. '
                '"x_start_decay" represents the x-coordinate where decay begins, requiring xs ≥ x.'
            )
            self.note_label.show()
        else:
            # 显示周期参数，隐藏提示
            self.period_label.show()
            self.period_params_frame.show()
            self.note_label.hide()
            # 设置周期参数默认值
            self.period_n_input.setText(str(template["params_default"]["periodic_n"]))
            self.period_dir_label.setText(template["params_default"]["period_direction"])
        
        # 添加其他参数输入框
        for param_name, default_val in template["params_default"].items():
            if param_name not in ["periodic_n", "period_direction"]:
                input_box = QLineEdit(str(default_val))
                self.param_inputs[param_name] = input_box
                self.params_layout.addRow(f"{param_name}:", input_box)
    
    def get_params(self):
        """获取用户输入的参数"""
        try:
            if self.preset_radio.isChecked():
                template_id = self.func_combo.currentData()
                if template_id == 6:
                    # 新模板：周期参数固定为 1 和 "width"
                    periodic_n = 1
                    period_direction = "width"
                else:
                    # 其他预设模板：从输入框读取（原始代码固定为 "length"）
                    periodic_n = int(self.period_n_input.text())
                    period_direction = "length"
            else:
                # 自定义模式：使用自定义周期参数输入框（与原始代码一致）
                periodic_n = int(self.custom_period_n_input.text())
                period_direction = "length"

            params = {
                "deform_dimension": self.deform_dimension,
                "periodic_n": periodic_n,
                "period_direction": period_direction,
            }

            if self.preset_radio.isChecked():
                params["func_mode"] = "preset"
                params["func_template_id"] = template_id

                for param_name, input_box in self.param_inputs.items():
                    params[param_name] = float(input_box.text())
            else:
                params["func_mode"] = "custom"
                params["x_def_expr"] = self.x_expr_input.text()
                params["y_def_expr"] = self.y_expr_input.text()


            return params
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None

    def init_ui_by_mode(self):
        """根据模式初始化界面"""
        if self.mode == "preset":
            self.preset_radio.setChecked(True)
            self.custom_radio.setEnabled(False)
        else:  # custom mode
            self.custom_radio.setChecked(True)
            self.preset_radio.setEnabled(False)
        
        self.update_mode()
        if self.mode == "preset":
            self.update_preset_params()
        self.custom_param_count = 0
           
# 新增：模块4指数膨胀变形参数对话框
class Module4ExpansionDialog(QDialog):
    """模块4指数膨胀变形参数对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exponential Expansion Parameters")
        self.setMinimumWidth(300)
        
        layout = QFormLayout(self)
        
        # 参数输入框
        self.A_input = QLineEdit("4.0")  # 膨胀强度
        self.B_input = QLineEdit("0.5")  # 膨胀影响范围
        
        layout.addRow("Expansion Strength (A):", self.A_input)
        layout.addRow("Influence Range (B):", self.B_input)
        
        # 按钮
        self.apply_btn = QPushButton("Apply Deformation")
        self.apply_btn.clicked.connect(self.accept)
        layout.addRow(self.apply_btn)
    
    def get_params(self):
        try:
            return {
                'A': float(self.A_input.text()),
                'B': float(self.B_input.text())
            }
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None

# 新增：模块4矩形正弦波变形参数对话框
class Module4RectSineWaveDialog(QDialog):
    """模块4矩形正弦波变形参数对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Biaxial Sine Ripple Parameters")
        self.setMinimumWidth(300)
        
        layout = QFormLayout(self)
        
        # 参数输入框
        self.amplitude_input = QLineEdit("0.3")  # 变形幅度
        self.transition_input = QLineEdit("2.0")  # 过渡距离
        self.cycles_input = QLineEdit("8")  # 周期数
        
        layout.addRow("Deformation Amplitude:", self.amplitude_input)
        layout.addRow("Transition Distance:", self.transition_input)
        layout.addRow("Number of Cycles (n):", self.cycles_input)
        
        # 按钮
        self.apply_btn = QPushButton("Apply Deformation")
        self.apply_btn.clicked.connect(self.accept)
        layout.addRow(self.apply_btn)
    
    def get_params(self):
        try:
            return {
                'amplitude': float(self.amplitude_input.text()),
                'transition_distance': float(self.transition_input.text()),
                'cycles': int(self.cycles_input.text())
            }
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None

# 新增：模块4极坐标波动变形参数对话框
class Module4PolarWaveDialog(QDialog):
    """模块4极坐标波动变形参数对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Polar Wave Deformation Parameters")
        self.setMinimumWidth(300)
        
        layout = QFormLayout(self)
        
        # 参数输入框
        self.A_input = QLineEdit("0.1")    # 波动振幅
        self.B_input = QLineEdit("0.08")   # 衰减系数  
        self.C_input = QLineEdit("2.0")    # 波动频率
        
        layout.addRow("Fluctuation Amplitude (A):", self.A_input)
        layout.addRow("Attenuation Coefficient (B):", self.B_input)
        layout.addRow("Fluctuation Frequency (C):", self.C_input)
        
        # 按钮
        self.apply_btn = QPushButton("Apply Deformation")
        self.apply_btn.clicked.connect(self.accept)
        layout.addRow(self.apply_btn)
    
    def get_params(self):
        try:
            return {
                'A': float(self.A_input.text()),
                'B': float(self.B_input.text()),
                'C': float(self.C_input.text())
            }
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None


# ------------------- 主窗口类（整合所有修改） -------------------
class MainWindow(QMainWindow):
    """应用主窗口"""
    def __init__(self):
        super().__init__()
        
        # 设置窗口
        self.setWindowTitle("MorphoPipe Platform")
        self.setGeometry(100, 100, 1200, 800)
        
        # 🔴 新增：初始化学术配色
        self.academic_colors = get_academic_colors()

        # 加载样式表（新增）
        self.load_modern_style()
        
        # 存储数据（原有部分不修改）
        self.base_points = None
        self.base_params = None
        self.current_deformed_points = None  # 当前变形后的点集
        self.type1_selected_region = None    # 类型①选择的区域
        self.is_type1_selecting = False      # 是否处于类型①区域选择模式
        self.current_region_type = None      # 当前选择的区域类型
        self.custom_shape_menu = None        # 自定义形状子模式菜单
        self.deform_history = []             # 变形历史栈（新增）
        
        # 新增：模块4相关变量（不修改原有变量）
        self.module4 = None                  # 模块4实例
        self.module4_regions_info = None     # 模块4返回的区域信息
        self.module4_canvas_click_conn = None# 模块4画布点击事件连接
        self.status_label = QLabel("Ready")  # 模块4状态提示（新增）
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧控制面板
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)  # 实例变量，用于添加撤销按钮
        left_panel.setMaximumWidth(300)
        
        # 1. 基础图形生成（原有部分不修改）
        base_group = QGroupBox("1. Base Pattern")
        base_layout = QVBoxLayout()
        self.generate_base_btn = QPushButton("Generate Base Pattern")
        self.generate_base_btn.clicked.connect(self.show_base_dialog)

        # 🔴 在这里添加样式设置
        self.generate_base_btn.setObjectName("primary")
        
        base_layout.addWidget(self.generate_base_btn)
        base_group.setLayout(base_layout)
        self.left_layout.addWidget(base_group)
        # 🔴 新增：放大查看按钮组
        # 在 __init__ 方法中找到Zoom View按钮组，修改为：
        zoom_group = QGroupBox("Zoom View")
        zoom_layout = QVBoxLayout()

        self.zoom_original_btn = QPushButton("Zoom Original Pattern")
        self.zoom_deformed_btn = QPushButton("Zoom Deformed Pattern") 
        # 移除这一行：self.zoom_unfolded_btn = QPushButton("Zoom Unfolded Path")
        self.zoom_3d_btn = QPushButton("Zoom 3D Projection")

        self.zoom_original_btn.clicked.connect(lambda: self.open_zoom_window("original"))
        self.zoom_deformed_btn.clicked.connect(lambda: self.open_zoom_window("deformed"))
        # 移除这一行：self.zoom_unfolded_btn.clicked.connect(lambda: self.open_zoom_window("unfolded"))
        self.zoom_3d_btn.clicked.connect(lambda: self.open_zoom_window("3d"))

        # 设置按钮样式
        self.zoom_original_btn.setObjectName("secondary")
        self.zoom_deformed_btn.setObjectName("secondary")
        self.zoom_3d_btn.setObjectName("secondary")

        zoom_layout.addWidget(self.zoom_original_btn)
        zoom_layout.addWidget(self.zoom_deformed_btn)
        # 移除这一行：zoom_layout.addWidget(self.zoom_unfolded_btn)
        zoom_layout.addWidget(self.zoom_3d_btn)

        zoom_group.setLayout(zoom_layout)
        self.left_layout.addWidget(zoom_group)
        # 2. 周期性变形（修改后）
        periodic_group = QGroupBox("2. Periodic Deformation")
        periodic_layout = QVBoxLayout()

        # 创建水平布局用于左右并排按钮
        button_layout = QHBoxLayout()

        self.preset_btn = QPushButton("Preset Functions")
        self.custom_btn = QPushButton("Custom Function")

        # 🔴 在这里添加样式设置
        self.preset_btn.setObjectName("secondary")
        self.custom_btn.setObjectName("secondary")

        button_layout.addWidget(self.preset_btn)
        button_layout.addWidget(self.custom_btn)

        # 连接新按钮的事件
        self.preset_btn.clicked.connect(lambda: self.show_periodic_dialog("preset"))
        self.custom_btn.clicked.connect(lambda: self.show_periodic_dialog("custom"))

        periodic_layout.addLayout(button_layout)

        periodic_group.setLayout(periodic_layout)
        self.left_layout.addWidget(periodic_group)
        
        # 3. 类型①：区域变形（原有部分不修改）

        self.type1_widget = Type1RegionSelectWidget(
            parent=self,
            on_select_region=self.on_type1_select_region,
            on_select_deform=self.on_type1_select_deform,
            on_confirm=self.on_type1_confirm_deform
        )
        self.left_layout.addWidget(self.type1_widget)
        
        # 在模块4布局部分，修改为：
        # 模块4布局部分
        module4_group = QGroupBox("4. Deformation Periodization")
        module4_layout = QVBoxLayout()

        # 模块4区域类型选择（单选按钮）← 状态标签移走后，这部分成为顶部
        self.module4_region_group = QButtonGroup(self)
        self.module4_circle_radio = QRadioButton("Circle")
        self.module4_rect_radio = QRadioButton("Rectangle")
        self.module4_ellipse_radio = QRadioButton("Ellipse")
        self.module4_custom_radio = QRadioButton("Custom")
        self.module4_region_group.addButton(self.module4_circle_radio, 1)
        self.module4_region_group.addButton(self.module4_rect_radio, 2)
        self.module4_region_group.addButton(self.module4_ellipse_radio, 3)
        self.module4_region_group.addButton(self.module4_custom_radio, 4)
        self.module4_circle_radio.setChecked(True)
        module4_layout.addWidget(self.module4_circle_radio)
        module4_layout.addWidget(self.module4_rect_radio)
        module4_layout.addWidget(self.module4_ellipse_radio)
        module4_layout.addWidget(self.module4_custom_radio)
        self.module4_circle_radio.toggled.connect(self.update_module4_deform_combo)
        self.module4_rect_radio.toggled.connect(self.update_module4_deform_combo)
        self.module4_ellipse_radio.toggled.connect(self.update_module4_deform_combo)
        self.module4_custom_radio.toggled.connect(self.update_module4_deform_combo)
        # 模块4激活按钮
        self.module4_activate_btn = QPushButton("Activate Module 4")
        self.module4_activate_btn.setObjectName("primary")
        self.module4_activate_btn.clicked.connect(self._module4_activate)
        module4_layout.addWidget(self.module4_activate_btn)

        # 模块4确认按钮
        self.module4_confirm_btn = QPushButton("Confirm (disabled)")
        self.module4_confirm_btn.setEnabled(False)
        self.module4_confirm_btn.clicked.connect(self._module4_confirm_regions)
        module4_layout.addWidget(self.module4_confirm_btn)

        # 模块4变形方式选择
        self.module4_deform_combo = QComboBox()
        self.module4_deform_combo.addItems([
            "Exponential Expansion",
            "Polar Wave", 
            "Biaxial Sine Ripple",
            "Scaling", "Sine", "Twist","Rectangular Scaling"
        ])
        self.module4_deform_combo.setEnabled(False)
        module4_layout.addWidget(self.module4_deform_combo)

        # 模块4应用变形按钮
        self.module4_apply_btn = QPushButton("Apply Deformation")
        self.module4_apply_btn.setEnabled(False)
        self.module4_apply_btn.clicked.connect(self._module4_apply_deform)
        module4_layout.addWidget(self.module4_apply_btn)

        # 模块4自定义模式选择
        self.module4_custom_mode_widget = QWidget()
        self.module4_custom_mode_layout = QHBoxLayout(self.module4_custom_mode_widget)
        self.module4_custom_mode_label = QLabel("Custom Mode:")
        self.module4_line_radio = QRadioButton("Line")
        self.module4_curve_radio = QRadioButton("Curve")
        self.module4_line_radio.setChecked(True)
        self.module4_custom_mode_layout.addWidget(self.module4_custom_mode_label)
        self.module4_custom_mode_layout.addWidget(self.module4_line_radio)
        self.module4_custom_mode_layout.addWidget(self.module4_curve_radio)
        self.module4_custom_radio.toggled.connect(self.update_module4_custom_mode_visibility)
        module4_layout.addWidget(self.module4_custom_mode_widget)
        self.module4_custom_mode_widget.setVisible(False)

        # 模块4状态提示 ← 移动到这里（底部）
        self.module4_status = QLabel("Status: Not activated")
        self.module4_status.setAlignment(Qt.AlignCenter)
        module4_layout.addWidget(self.module4_status)  # ← 现在在底部

        module4_group.setLayout(module4_layout)
        self.left_layout.addWidget(module4_group)

        # 连接自定义模式选择信号
        self.module4_line_radio.toggled.connect(self.on_module4_custom_mode_changed)
        self.module4_curve_radio.toggled.connect(self.on_module4_custom_mode_changed)

        # 初始隐藏自定义模式选择
        self.module4_custom_mode_widget.setVisible(False)  # 修改：设置widget的可见性
        module4_group.setLayout(module4_layout)
        self.left_layout.addWidget(module4_group)
        
        # 新增：撤销按钮（原有部分不修改，仅调整位置在模块4之后）
        self.undo_btn = QPushButton("Undo Last Deformation")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.on_undo_deform)

        # 🔴 在这里添加样式设置 - 使用特殊ID
        self.undo_btn.setObjectName("undo_btn")

        # 🔴 添加固定大小设置
        self.undo_btn.setFixedSize(40, 40)

        # 新增：Code Export按钮
        self.export_btn = QPushButton("Code Export")
        self.export_btn.setEnabled(False)

        # 🔴 在这里添加样式设置
        self.export_btn.setObjectName("secondary")
        
        self.left_layout.addWidget(self.export_btn)

        self.left_layout.addWidget(self.export_btn)

        # 创建导出菜单
        self.export_menu = QMenu(self)

        # Unfolded Path子菜单
        self.unfolded_path_action = QAction("Unfolded Path (for print code export)", self)
        self.export_menu.addAction(self.unfolded_path_action)

        # Deformed Path子菜单
        self.deformed_path_menu = QMenu("Deformed Path", self)
        self.deformed_absolute_action = QAction("Absolute Coordinates", self)
        self.deformed_relative_action = QAction("Relative Coordinates", self)
        self.deformed_path_menu.addAction(self.deformed_absolute_action)
        self.deformed_path_menu.addAction(self.deformed_relative_action)
        self.export_menu.addMenu(self.deformed_path_menu)

        self.export_btn.setMenu(self.export_menu)

        # 连接信号
        self.unfolded_path_action.triggered.connect(self.export_unfolded_path)
        self.deformed_absolute_action.triggered.connect(self.export_deformed_absolute)
        self.deformed_relative_action.triggered.connect(self.export_deformed_relative)
        # 填充剩余空间（原有部分不修改）
        self.left_layout.addStretch()
        # 新增：撤销按钮（从左侧面板移出）
        self.undo_btn = QPushButton("Undo Last Deformation")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.on_undo_deform)
        self.undo_btn.setObjectName("undo_btn")
        # 右侧图形显示区（原有部分不修改）
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        # 保存上一次用户自定义公式
        self.last_custom_x_expr = "x + 0.5*sin(0.4*x)"
        self.last_custom_y_expr = "y"

        # 创建画布
        self.canvas = MplCanvas(self, width=10, height=8, dpi=100)

        # 创建画布容器
        self.canvas_widget = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_widget)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)

        # 直接将画布添加到布局
        self.canvas_layout.addWidget(self.canvas)

        # 将撤销按钮作为画布容器的子控件（使用绝对定位）
        self.undo_btn.setParent(self.canvas_widget)
        self.undo_btn.raise_()  # 确保按钮在最上层

        # 将画布容器添加到右侧布局
        right_layout.addWidget(self.canvas_widget)
        # 🔴 新增：操作日志区域
        self.log_group = QGroupBox("Operation Log")
        log_layout = QVBoxLayout(self.log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; font-size: 9pt;")
        log_layout.addWidget(self.log_text)

        # 日志控制按钮栏
        log_control_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.save_log_btn = QPushButton("Save Log")
        self.save_log_btn.clicked.connect(self.save_operation_log)
        log_control_layout.addWidget(self.clear_log_btn)
        log_control_layout.addWidget(self.save_log_btn)
        log_control_layout.addStretch()
        log_layout.addLayout(log_control_layout)

        # 🔴 关键修改：使用分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.canvas_widget)  # 使用画布容器而不是直接使用画布
        splitter.addWidget(self.log_group)

        # 设置初始比例（画布占80%，日志占20%）
        splitter.setSizes([800, 200])

        # 可选：设置分割器手柄样式
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #cccccc;
                height: 3px;
            }
            QSplitter::handle:hover {
                background-color: #aaaaaa;
            }
        """)

        # 将分割器添加到右侧布局
        right_layout.addWidget(splitter)

     # 再添加画布

  
        # 初始化类型①的画布交互工具（使用变形图案的axes）（原有部分不修改）
        self.type1_canvas_interaction = Type1CanvasInteraction(self.canvas.axes[1], self)
        
        # 初始化自定义形状子模式菜单（原有部分不修改）
        self.custom_shape_menu = CustomShapeMenu(self, self.type1_canvas_interaction)
        
        # 绑定鼠标事件（原有部分不修改，新增模块4判断）
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_drag)
        self.canvas.mpl_connect('button_release_event', self.on_canvas_release)

        # 新增双击事件处理方法
        def on_canvas_double_click(self, event):
            """处理画布双击事件"""
            if hasattr(event, 'dblclick') and event.dblclick:
                if event.inaxes == self.canvas.axes[1] and self.is_type1_selecting:
                    self.type1_canvas_interaction._on_double_click(event)
        # 添加到主布局（原有部分不修改）
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.setCentralWidget(main_widget)
        self.update_buttons_state()
        # 在 __init__ 方法末尾添加：
        # 设置按钮初始位置（需要延迟执行，因为窗口还未完全显示）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.update_undo_button_position)
        # 🔴 新增：添加模块激活状态变量
        self.active_module = None  # "module3" 或 "module4" 或 None
    def load_modern_style(self):
        """加载现代化样式表"""
        try:
            import os
            
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            style_file = os.path.join(current_dir, "modern_style.qss")
            
            print(f"🔍 正在查找样式表文件: {style_file}")
            
            # 检查文件是否存在
            if not os.path.exists(style_file):
                print(f"❌ 文件不存在: {style_file}")
                
                # 列出目录中的所有文件，帮助调试
                print("📁 目录中的文件:")
                for file in os.listdir(current_dir):
                    print(f"   - {file}")
                return
            
            # 尝试不同编码方式读取文件
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(style_file, "r", encoding=encoding) as f:
                        style_content = f.read()
                        print(f"Successfully read the stylesheet")
                        
                        # 检查文件内容是否为空
                        if not style_content.strip():
                            continue
                        
                        # 应用样式表
                        self.setStyleSheet(style_content)
                        print("Stylesheet loaded successfully.")
                        return
                        
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    continue
            
            
        except Exception as e:
            import traceback
            traceback.print_exc()
    # ------------------- 原有方法 -------------------
    def update_buttons_state(self):
        """更新按钮状态"""
        has_base = self.base_points is not None
        # 周期性变形按钮
        self.preset_btn.setEnabled(has_base)
        self.custom_btn.setEnabled(has_base)
        
        # 其他按钮状态保持不变
        self.type1_widget.select_region_btn.setEnabled(has_base)
        
        # 模块4按钮状态
        self.module4_activate_btn.setEnabled(has_base)
        self.module4_deform_combo.setEnabled(self.module4_regions_info is not None and len(self.module4_regions_info) > 0)
        self.module4_apply_btn.setEnabled(self.module4_regions_info is not None and len(self.module4_regions_info) > 0)
        
        # 根据是否选择了区域更新确认按钮状态
        self.type1_widget.disable_confirm_btn(self.type1_selected_region is None)
        
        # 模块4状态更新
        if self.module4 and has_base:
            if self.module4_regions_info:
                self.module4_status.setText(f"Status: {len(self.module4_regions_info)} regions ready")
            else:
                self.module4_status.setText("Status: Draw region on canvas")
        else:
            self.module4_status.setText("Status: Not activated")
        # 新增：启用导出按钮
        self.export_btn.setEnabled(self.base_points is not None)
    def on_canvas_click(self, event):
        """画布鼠标点击事件"""
        # 检查是否为双击
        if hasattr(event, 'dblclick') and event.dblclick:
            if event.inaxes == self.canvas.axes[1] and self.active_module == "module3":
                self.type1_canvas_interaction._on_double_click(event)
            return
        
        # 🔴 新增：只处理当前激活模块的事件
        if self.active_module == "module3":
            # 原有：类型①交互
            if event.inaxes == self.canvas.axes[1] and self.is_type1_selecting:
                self.type1_canvas_interaction.on_mouse_press(event)
        elif self.active_module == "module4":
            # 新增：模块4交互
            if event.inaxes == self.canvas.axes[1] and self.module4:
                self.module4.on_mouse_press(event)

    def on_canvas_drag(self, event):
        """画布鼠标拖拽事件"""
        # 🔴 新增：只处理当前激活模块的事件
        if self.active_module == "module3":
            if event.inaxes == self.canvas.axes[1] and self.is_type1_selecting:
                self.type1_canvas_interaction.on_mouse_move(event)
        elif self.active_module == "module4":
            if event.inaxes == self.canvas.axes[1] and self.module4:
                self.module4.on_mouse_move(event)

    def on_canvas_release(self, event):
        """画布鼠标释放事件：适配区域闭合（新增模块4判断）"""
        if self.active_module == "module3":
            if event.inaxes == self.canvas.axes[1] and self.is_type1_selecting:
                self.type1_canvas_interaction.on_mouse_release(event)
        # 原有：类型①交互
        if event.inaxes == self.canvas.axes[1] and self.is_type1_selecting:
            self.type1_canvas_interaction.on_mouse_release(event)
            # 获取已选择的区域
            region = self.type1_canvas_interaction.selected_region
            if region:
                self.type1_selected_region = region
                # 添加基础尺寸参数
                if self.base_params:
                    self.type1_selected_region['base_width'] = self.base_params['width']
                    self.type1_selected_region['base_length'] = self.base_params['length']
                # 更新状态
                self.type1_widget.update_status(f"Selected {region['type'].capitalize()} region")
                self.update_buttons_state()
            # 仅在基础形状选择完成后退出选择模式
            base_shapes = ["circle", "square", "ellipse"]
            if self.current_region_type and self.current_region_type.lower() in base_shapes:
                self.is_type1_selecting = False
        # 新增：模块4交互
            elif self.active_module == "module4":
                if event.inaxes == self.canvas.axes[1] and self.module4:
                    self.module4.on_mouse_release(event)

    def enter_type1_select_mode(self, region_type):
        """进入类型①区域选择模式 - 使用新的切换机制"""
        print(f"进入区域选择模式，区域类型: {region_type}")
        
        if not self.base_points:
            QMessageBox.warning(self, "Warning", "Please generate base pattern first!")
            return
        
        # 🔴 修改：使用新的切换方法
        self.switch_to_module3(region_type)

    def _enter_module3_selection(self, region_type):
        """模块3的实际进入逻辑（从 switch_to_module3 调用）"""
        # 这是原有的 enter_type1_select_mode 逻辑，但移除了重置模块4的部分
        self.is_type1_selecting = True
        self.current_region_type = region_type
        
        # 清除之前的选择
        if self.type1_selected_region:
            self.type1_canvas_interaction.clear_selection()
            self.type1_selected_region = None
            self.update_buttons_state()
        
        # 根据区域类型显示不同的状态提示
        region_type_lower = region_type.lower()
        
        if region_type_lower == "custom":
            current_mode = self.type1_widget.current_custom_mode
            if not current_mode:
                current_mode = "line"
                
            mode = current_mode.capitalize()
            if mode == "Curve":
                self.type1_widget.update_status(f"Selecting Custom ({mode}) (click to add control points, curve will be auto-generated)")
            else:
                self.type1_widget.update_status(f"Selecting Custom ({mode}) (click/add points, double-click to close)")
            
            self.type1_canvas_interaction.custom_mode = current_mode
            self.type1_canvas_interaction.start_selection(region_type_lower, current_mode)
        else:
            self.type1_canvas_interaction.start_selection(region_type_lower)
            mode_display = region_type.capitalize()
            
            if region_type_lower == "circle":
                status_text = f"Selecting {mode_display} (click to set center, drag to adjust radius)"
            elif region_type_lower == "square":
                status_text = f"Selecting {mode_display} (click to set center, drag to adjust size)"
            elif region_type_lower == "ellipse":
                status_text = f"Selecting {mode_display} (click to set center, drag to adjust axes)"
            elif region_type_lower == "triangle":
                status_text = f"Selecting {mode_display} (click to add three vertices)"
            else:
                status_text = f"Selecting {mode_display} region"
                
            self.type1_widget.update_status(status_text)

    def _clean_module4_graphics_only(self):
        """仅清除Module4的图形元素，不删除数据"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
        
        # 获取变形图形所在的轴
        ax = self.canvas.axes[1] if len(self.canvas.axes) > 1 else None
        if not ax:
            return
        
        # 1. 清除所有绿色边框的图形（Module4原始区域）
        green_patches = []
        for patch in ax.patches[:]:
            try:
                if hasattr(patch, 'get_edgecolor'):
                    edgecolor = patch.get_edgecolor()
                    # 检查是否为绿色边框（Module4原始区域）
                    if len(edgecolor) == 4:
                        # RGB值接近绿色 (0, 1, 0)
                        if edgecolor[0] < 0.1 and edgecolor[1] > 0.9 and edgecolor[2] < 0.1:
                            green_patches.append(patch)
            except Exception:
                continue
        
        for patch in green_patches:
            try:
                patch.remove()
            except Exception:
                pass
        
        # 2. 清除所有橙色旋转点
        orange_patches = []
        for patch in ax.patches[:]:
            try:
                if hasattr(patch, 'get_facecolor'):
                    facecolor = patch.get_facecolor()
                    # 检查是否为橙色填充（Module4旋转点）
                    if len(facecolor) == 4:
                        # RGB值接近橙色 (1, 0.65, 0)
                        if facecolor[0] > 0.9 and facecolor[1] > 0.6 and facecolor[1] < 0.7 and facecolor[2] < 0.1:
                            orange_patches.append(patch)
            except Exception:
                continue
        
        for patch in orange_patches:
            try:
                patch.remove()
            except Exception:
                pass
        
        # 3. 清除所有蓝色/紫色虚线边框（Module4关联区域）
        colored_patches = []
        for patch in ax.patches[:]:
            try:
                if hasattr(patch, 'get_edgecolor'):
                    edgecolor = patch.get_edgecolor()
                    # 检查是否为虚线边框（Module4关联区域）
                    if len(edgecolor) == 4 and hasattr(patch, 'get_linestyle'):
                        linestyle = patch.get_linestyle()
                        # 虚线边框（--）且是蓝色或紫色
                        if linestyle == '--' and (edgecolor[0] < 0.1 or edgecolor[0] > 0.4):
                            colored_patches.append(patch)
            except Exception:
                continue
        
        for patch in colored_patches:
            try:
                patch.remove()
            except Exception:
                pass
        
        # 4. 清除Module4的预览线（绿色线条）
        green_lines = []
        for line in ax.lines[:]:
            try:
                color = line.get_color()
                # 绿色线条
                if color == 'green' or color == 'g':
                    green_lines.append(line)
            except Exception:
                continue
        
        for line in green_lines:
            try:
                line.remove()
            except Exception:
                pass
        
        # 5. 清除Module4的红色控制点
        red_collections = []
        for collection in ax.collections[:]:
            try:
                colors = collection.get_facecolor()
                if len(colors) > 0 and len(colors[0]) == 4:
                    # 红色散点 (1, 0, 0)
                    if colors[0][0] > 0.9 and colors[0][1] < 0.1 and colors[0][2] < 0.1:
                        red_collections.append(collection)
            except Exception:
                continue
        
        for collection in red_collections:
            try:
                collection.remove()
            except Exception:
                pass
        
        # 6. 重绘画布
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
        
        print("已清除Module4图形元素")
    def show_custom_shape_menu(self):
        """显示自定义形状的子模式菜单（原有部分不修改）"""
        if self.custom_shape_menu:
            # 在下拉框位置显示菜单
            combo_pos = self.type1_widget.region_combo.mapToGlobal(QPoint(0, self.type1_widget.region_combo.height()))
            self.custom_shape_menu.exec_(combo_pos)

    def on_type1_select_region(self, region_type):
        """选择区域形状时的回调（原有部分不修改）"""
        self.type1_widget.update_status(f"Region shape: {region_type} (click 'Select Region' to draw)")

    def on_type1_select_deform(self, deform_type):
        """选择变形类型时的回调（扩展支持模块4变形）"""
        status = f"Deform type: {deform_type}"
        
        # 添加模块4变形的特殊提示
        if deform_type in ["Exponential Expansion", "Polar Wave", "Biaxial Sine Ripple"]:
            status += " (Module4 algorithm)"
        elif self.type1_selected_region:
            status += " (click 'Apply Deformation' to proceed)"
            
        self.type1_widget.update_status(status)

    def on_type1_confirm_deform(self, region_type, deform_type):
        """确认应用区域变形（扩展支持 Polar Wave）"""
        if not self.type1_selected_region or not self.base_points:
            return

        # 根据变形类型选择对应的参数对话框
        if deform_type in ["Exponential Expansion", "Polar Wave", "Biaxial Sine Ripple"]:
            # 模块4变形的参数对话框
            if deform_type == "Exponential Expansion":
                dialog = Module4ExpansionDialog(self)
            elif deform_type == "Polar Wave":
                dialog = Type1DeformParamDialog("Polar Wave", self)  # 🔴 使用新的 Type1DeformParamDialog
            elif deform_type == "Biaxial Sine Ripple":
                dialog = Module4RectSineWaveDialog(self)
        else:
            # 原有类型①的对话框
            dialog = Type1DeformParamDialog(deform_type, self)
            
        # 只执行一次对话框，避免重复弹出
        if dialog.exec_() != QDialog.Accepted:
            return  # 用户取消操作
            
        params = dialog.get_params()
        if not params:
            return  # 参数无效
            
        try:
            # 保存当前状态到历史栈
            current_state = {
                'points': self.current_deformed_points.copy() if self.current_deformed_points is not None else self.base_points.copy(),
                'module4_regions': self.module4_regions_info.copy() if self.module4_regions_info else None,
                'type1_region': self.type1_selected_region.copy() if self.type1_selected_region else None
            }
            self.deform_history.append(current_state)
            self.undo_btn.setEnabled(True)
            
            # 准备变形参数
            deform_params = {"type": deform_type, **params}
            
            # 确定使用哪个点集作为输入
            input_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
            
            # 应用变形 - 根据变形类型选择不同的处理路径
            if deform_type == "Polar Wave":
                # 🔴 关键：现在使用第3部分的 Polar Wave 算法，而不是调用第4模块
                deformed_points = RegionDeformer.deform_region(
                    input_points, 
                    self.type1_selected_region, 
                    deform_params
                )
            elif deform_type in ["Exponential Expansion", "Biaxial Sine Ripple"]:
                # 其他模块4变形算法保持不变
                deformed_points = self._apply_type1_with_module4_algo(
                    input_points, self.type1_selected_region, deform_type, params
                )
            else:
                # 原有的类型①变形算法
                deformed_points = RegionDeformer.deform_region(
                    input_points, 
                    self.type1_selected_region, 
                    deform_params
                )
            
            # 生成展开路径和3D投影
            unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 更新当前变形点集
            self.current_deformed_points = deformed_points
            
            # 绘图
            title = f"Region Deformation - {region_type} + {deform_type}"
            self.plot_results(self.base_points, deformed_points, title, unfolded, cylinder_3d)
            self.add_log(f"Applied region deformation: {region_type} + {deform_type}")
            QMessageBox.information(self, "Success", "Region deformation applied successfully!")
        except Exception as e:
            print(f"Deformation error: {str(e)}")
            QMessageBox.critical(self, "Deformation Error", f"Failed to compute deformation: {str(e)}")

        # 在变形成功后添加：
        if hasattr(self, 'zoom_window') and self.zoom_window and self.zoom_window.isVisible():
            self.zoom_window.update_data(
                self.base_points,
                self.current_deformed_points,  # 更新后的点
                self.base_params,
                self.type1_selected_region,
                self.module4_regions_info
        )
    # 🔴 添加在这里 - 在 __init__ 方法之后，其他方法之前
    def add_log(self, message):
        """添加操作日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # 添加到文本区域
        self.log_text.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
        
        print(f"LOG: {log_entry}")  # 同时输出到控制台

    # 🔴 添加在这里 - 在 add_log 方法之后
    def save_operation_log(self):
        """保存操作日志到文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Operation Log", "", "Text Files (*.txt)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.add_log("Operation log saved to file")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log: {str(e)}")
    # 在 show_base_dialog 方法中修改重置逻辑：
    def show_base_dialog(self):
        """显示基础图形参数对话框"""
        # 使用新的对话框
        dialog = BasePatternDialogEx(self)  # 替换原来的 BasePatternDialog
        if dialog.exec_():
            params = dialog.get_params()
            if params:
                # 生成基础图案
                self.base_points, self.base_params = StentUtils.generate_original_points(params)
                self.current_deformed_points = None
                self.type1_selected_region = None
                self.type1_canvas_interaction.clear_selection()
                
                # 如果有角度参数，在标题中显示
                title = "Base Pattern"
                if 'theta_deg' in params:
                    title = f"Base Pattern (θ={params['theta_deg']}°, n={params['n']})"
                
                self.plot_results(self.base_points, self.base_points, title)
                self.update_buttons_state()
                self.type1_widget.update_status("Base pattern generated - select region to deform")
                QMessageBox.information(self, "Success", "Base pattern generated successfully!")
                self.add_log(f"Generated base pattern: d={params['d']}, axial={params['width']}, circumferential={params['length']}, cycles={params['max_cycles']}")
    def show_periodic_dialog(self, mode):
        if not self.base_points:
            QMessageBox.warning(self, "Warning", "Please generate base pattern first!")
            return
            
        deform_dimension = "both"
        
        if mode == "preset":
            dialog = PeriodicFunctionDialog(deform_dimension, mode, self)
        else:
            dialog = PeriodicFunctionDialog(
                deform_dimension, mode, self,
                default_x_expr=self.last_custom_x_expr,
                default_y_expr=self.last_custom_y_expr
            )
        
        if dialog.exec_():
            params = dialog.get_params()
            if params:
                # 保存当前状态到历史栈
                current_state = {
                    'points': self.current_deformed_points.copy() if self.current_deformed_points is not None else self.base_points.copy(),
                    'module4_regions': self.module4_regions_info.copy() if self.module4_regions_info else None,
                    'type1_region': self.type1_selected_region.copy() if self.type1_selected_region else None
                }
                self.deform_history.append(current_state)
                self.undo_btn.setEnabled(True)
                
                params["length"] = self.base_params["length"]
                params["width"] = self.base_params["width"]
                
                try:
                    deformed_points, _ = deform_type4_periodic(self.base_points, params)
                    unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
                    cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
                    
                    self.current_deformed_points = deformed_points
                    self.type1_selected_region = None
                    self.type1_canvas_interaction.clear_selection()
                    self.update_buttons_state()
                    
                    title = f"Periodic Deformation - {mode.capitalize()} Mode"
                    self.plot_results(self.base_points, deformed_points, title, unfolded, cylinder_3d)
                    
                    # 如果是 custom 模式，保存用户输入的表达式
                    if mode == "custom":
                        self.last_custom_x_expr = dialog.x_expr_input.text()
                        self.last_custom_y_expr = dialog.y_expr_input.text()
                    
                    self.add_log(f"Applied periodic deformation ({mode}): {params.get('func_template_id', 'custom')}, periods={params['periodic_n']}")
                    
                    if hasattr(self, 'zoom_window') and self.zoom_window and self.zoom_window.isVisible():
                        self.zoom_window.update_data(
                            self.base_points,
                            self.current_deformed_points, 
                            self.base_params,
                            self.type1_selected_region,
                            self.module4_regions_info
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Deformation Error", f"Failed to compute deformation: {str(e)}")
    def on_undo_deform(self):
        """撤销上一次变形操作（增强格式检查）"""
        if not self.deform_history:
            QMessageBox.information(self, "Info", "No deformation history to undo")
            return
        
        # 恢复上一次状态
        previous_state = self.deform_history.pop()
        
        # 增强格式检查：支持新旧两种格式
        if isinstance(previous_state, dict):
            # 新格式：字典类型
            if 'points' in previous_state:
                self.current_deformed_points = previous_state['points']
            else:
                self.current_deformed_points = None
                
            if 'module4_regions' in previous_state:
                self.module4_regions_info = previous_state['module4_regions']
            else:
                self.module4_regions_info = None
                
            if 'type1_region' in previous_state:
                self.type1_selected_region = previous_state['type1_region']
            else:
                self.type1_selected_region = None
                
        elif isinstance(previous_state, list):
            # 旧格式：直接是点集列表（兼容性处理）
            self.current_deformed_points = previous_state
            self.module4_regions_info = None
            self.type1_selected_region = None
        else:
            # 未知格式，重置到基础状态
            QMessageBox.warning(self, "Warning", "Invalid history format, resetting to base pattern")
            self.current_deformed_points = None
            self.module4_regions_info = None
            self.type1_selected_region = None
            self.deform_history = []  # 清空历史栈
        
        # 如果撤销后没有模块4区域，完全重置Module4
        if not self.module4_regions_info:
            self._reset_module4_completely()
        
        # 生成展开图和3D图
        current_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
        unfolded = StentUtils.generate_unfolded_path(
            self.base_points, 
            current_points, 
            self.base_params
        )
        cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
        
        # 重新绘图
        title = "Undo: Previous State"
        if self.module4_regions_info:
            title += " (Module4 regions kept)"
        self.plot_results(
            self.base_points, 
            current_points, 
            title, 
            unfolded, 
            cylinder_3d
        )
        
        # 更新撤销按钮状态
        self.undo_btn.setEnabled(len(self.deform_history) > 0)
        
        # 更新所有按钮状态
        self.update_buttons_state()
        
        # 显示撤销信息
        if self.module4_regions_info:
            QMessageBox.information(self, "Undo", "Deformation undone, Module4 regions kept")
        else:
            QMessageBox.information(self, "Undo", "All changes undone")
        self.add_log("Undo last deformation")
    def plot_results(self, original, deformed, title, unfolded=None, cylinder_3d=None):

        """修改后：应用自定义布局并确保等比例显示"""
        # 获取学术配色
        colors = self.academic_colors
        
        # 清除现有图形
        for ax in self.canvas.axes:
            ax.clear()
        
        # 生成默认展开图和3D图（如果未提供）
        current_points = deformed if deformed is not None else original
        if unfolded is None and self.base_params:
            unfolded = StentUtils.generate_unfolded_path(original, current_points, self.base_params)
        if cylinder_3d is None and unfolded and self.base_params:
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)

        # 1. 原始图形（左上）
        ax1 = self.canvas.axes[0]
        split_indices = StentUtils.get_segment_split_indices(original, self.base_params['length'])
        for j in range(len(split_indices) - 1):
            start_idx = split_indices[j]
            end_idx = split_indices[j + 1]
            segment = original[start_idx:end_idx]
            if len(segment) < 2:
                continue
            x_seg, y_seg = zip(*segment)
            ax1.plot(x_seg, y_seg, color=colors['primary_black'], alpha=0.8, linewidth=1.0)
        
        # 应用学术样式到原始图形
        style_plot(ax1, 'original')
        ax1.set_title('Original Pattern', fontsize=12, color=colors['primary_black'], pad=10)
        ax1.set_xlabel('X (mm)', fontsize=11, color=colors['primary_black'])
        ax1.set_ylabel('Y (mm)', fontsize=11, color=colors['primary_black'])
        ax1.set_aspect('equal')  # 🔴 确保等比例显示
        ax1.grid(True, linestyle='--', alpha=0.3, color=colors['light_gray'])
        
        # 2. 变形图形（右上）
        ax2 = self.canvas.axes[1]
        for j in range(len(split_indices) - 1):
            start_idx = split_indices[j]
            end_idx = split_indices[j + 1]
            segment = deformed[start_idx:end_idx]
            if len(segment) < 2:
                continue
            x_seg, y_seg = zip(*segment)
            ax2.plot(x_seg, y_seg, color=colors['primary_blue'], alpha=0.8, linewidth=1.2)
        
        # 绘制区域边界（原有代码保持不变）
        if self.type1_selected_region:
            region = self.type1_selected_region
            region_type = region['type'].lower()
            
            if region_type == 'circle':
                patch = patches.Circle(region['center'], region['radius'], 
                                    fill=False, edgecolor=colors['primary_red'], 
                                    linestyle='--', linewidth=1.5)
                ax2.add_patch(patch)
            elif region_type == 'square':
                cx, cy = region['center']
                half_side = region['side_length'] / 2
                patch = patches.Rectangle((cx-half_side, cy-half_side), 
                                        region['side_length'], region['side_length'],
                                        fill=False, edgecolor=colors['primary_red'], 
                                        linestyle='--', linewidth=1.5)
                ax2.add_patch(patch)
            elif region_type == 'ellipse':
                # 🔴 修复：添加角度参数
                angle = region.get('angle', 0)  # 获取角度，默认为0
                patch = patches.Ellipse(
                    region['center'], 
                    2*region['semi_major'], 
                    2*region['semi_minor'],
                    angle=angle,  # 🔴 添加角度参数
                    fill=False, 
                    edgecolor=colors['primary_red'], 
                    linestyle='--', 
                    linewidth=1.5
                )
                ax2.add_patch(patch)
            elif region_type == 'triangle':
                vertices = region['vertices']
                vertices_closed = vertices + [vertices[0]]
                x, y = zip(*vertices_closed)
                ax2.plot(x, y, linestyle='--', color=colors['primary_red'], linewidth=1.5)
                ax2.scatter([v[0] for v in vertices], [v[1] for v in vertices], 
                        c=colors['primary_red'], s=40, alpha=0.8)
            elif region_type in ['polygon', 'custom']:
                vertices = region['vertices']
                vertices_closed = vertices + [vertices[0]]
                x, y = zip(*vertices_closed)
                ax2.plot(x, y, linestyle='--', color=colors['primary_red'], linewidth=1.5)
        
        # 绘制模块4区域边界
        if self.module4_regions_info:
            for i, region in enumerate(self.module4_regions_info):
                # 根据索引选择颜色和线型
                if i == 0:
                    edgecolor = 'green'          # 原始区域：绿色实线
                    linestyle = '-'
                else:
                    edgecolor = colors['primary_orange']  # 关联区域：橙色虚线
                    linestyle = '--'

                # 只要存在 vertices，就使用 Polygon 绘制
                if 'vertices' in region and region['vertices']:
                    vertices = region['vertices']
                    # 确保顶点闭合（如果首尾不同则添加第一个点）
                    if vertices and vertices[0] != vertices[-1]:
                        vertices = vertices + [vertices[0]]
                    patch = patches.Polygon(vertices, fill=False,
                                            edgecolor=edgecolor,
                                            linestyle=linestyle,
                                            linewidth=1.5)
                else:
                    # 兼容无 vertices 的情况（旧数据）
                    reg_type = region['type']
                    centroid = region['centroid']
                    if reg_type == 'circle':
                        patch = patches.Circle(centroid, region['radius'],
                                            fill=False, edgecolor=edgecolor,
                                            linestyle=linestyle, linewidth=1.5)
                    elif reg_type == 'rectangle':
                        width, height = region['width'], region['height']
                        patch = patches.Rectangle(
                            (centroid[0]-width/2, centroid[1]-height/2),
                            width, height, angle=region['angle'],
                            fill=False, edgecolor=edgecolor,
                            linestyle=linestyle, linewidth=1.5
                        )
                    elif reg_type == 'ellipse':
                        major, minor = region['major_axis'], region['minor_axis']
                        patch = patches.Ellipse(
                            centroid, major, minor, angle=region['angle'],
                            fill=False, edgecolor=edgecolor,
                            linestyle=linestyle, linewidth=1.5
                        )
                    elif reg_type == 'custom':
                        vertices = region.get('vertices')
                        if vertices and len(vertices) >= 3:
                            if vertices[0] != vertices[-1]:
                                vertices = vertices + [vertices[0]]
                            patch = patches.Polygon(vertices, fill=False,
                                                    edgecolor=edgecolor,
                                                    linestyle=linestyle,
                                                    linewidth=1.5)
                        else:
                            continue  # 无有效顶点，跳过
                    else:
                        continue  # 未知类型，跳过

                ax2.add_patch(patch)
        
        # 应用学术样式到变形图形
        style_plot(ax2, 'deformed')
        ax2.set_title('Deformed Pattern', fontsize=12, color=colors['primary_black'], pad=10)
        ax2.set_xlabel('X (mm)', fontsize=11, color=colors['primary_black'])
        ax2.set_ylabel('Y (mm)', fontsize=11, color=colors['primary_black'])
        ax2.set_aspect('equal')  # 🔴 确保等比例显示
        ax2.grid(True, linestyle='--', alpha=0.3, color=colors['light_gray'])
        
        # 3. 3D圆柱投影（底部中间）
        ax3 = self.canvas.axes[2]
        if cylinder_3d:
            x_3d = [p[0] for p in cylinder_3d]
            y_3d = [p[1] for p in cylinder_3d]
            z_3d = [p[2] for p in cylinder_3d]
            
            ax3.scatter(x_3d, y_3d, z_3d, s=1.0, color=colors['primary_blue'], alpha=0.7)
            
            # 应用学术样式到3D图形
            style_plot(ax3, '3d_cylinder')
            ax3.set_title('3D Cylindrical Projection', fontsize=12, color=colors['primary_black'], pad=10)
            ax3.set_xlabel('X (mm)', fontsize=11, color=colors['primary_black'])
            ax3.set_ylabel('Y (mm)', fontsize=11, color=colors['primary_black'])
            ax3.set_zlabel('Z (mm)', fontsize=11, color=colors['primary_black'])
            
            # 🔴 确保3D等比例显示
            max_range = max([
                max(x_3d) - min(x_3d),
                max(y_3d) - min(y_3d),
                max(z_3d) - min(z_3d)
            ]) / 2.0
            
            mid_x = (max(x_3d) + min(x_3d)) / 2.0
            mid_y = (max(y_3d) + min(y_3d)) / 2.0
            mid_z = (max(z_3d) + min(z_3d)) / 2.0
            
            ax3.set_xlim(mid_x - max_range, mid_x + max_range)
            ax3.set_ylim(mid_y - max_range, mid_y + max_range)
            ax3.set_zlim(mid_z - max_range, mid_z + max_range)
            ax3.set_box_aspect([1, 1, 1])  # 🔴 确保3D等比例
        
        # 刷新显示
        self.canvas.fig.suptitle(title, fontsize=14, color=colors['primary_black'])
        
        # 由于使用自定义坐标布局，不需要额外的tight_layout调整
        self.canvas.draw()
    def _reset_module4_completely(self):
        """完全重置模块4的所有状态"""
        # 先清除图形
        self._clean_module4_graphics_only()
        
        # 重置变量
        self.module4 = None
        self.module4_regions_info = None
        
        # 重置确认按钮状态
        self.module4_confirm_btn.setText("Confirm (disabled)")
        self.module4_confirm_btn.setEnabled(False)
        
        # 重置变形下拉框状态
        self.module4_deform_combo.setEnabled(False)
        self.module4_apply_btn.setEnabled(False)

        
        # 🔴 新增：隐藏自定义模式选择widget
        self.module4_custom_mode_widget.setVisible(False)
        
        # 清除所有可能的事件绑定
        if hasattr(self, 'module4_canvas_click_conn') and self.module4_canvas_click_conn:
            try:
                self.canvas.mpl_disconnect(self.module4_canvas_click_conn)
            except:
                pass
            self.module4_canvas_click_conn = None
        
        # 更新按钮状态
        self.update_buttons_state()

    def _clean_module4_patches(self):
        """清除画布上所有 Module4 相关的图形元素"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        ax = self.canvas.axes[1]  # 变形图形所在的轴
        if not ax:
            return
        
        # 移除所有橙色边框的图形（Module4 区域标记）
        for patch in ax.patches[:]:
            if hasattr(patch, 'get_edgecolor'):
                # 检查是否是 Module4 的橙色边框
                edgecolor = patch.get_edgecolor()
                if len(edgecolor) == 4 and edgecolor[0] == 1.0 and edgecolor[1] == 0.65 and edgecolor[2] == 0.0:  # 橙色
                    try:
                        patch.remove()
                    except:
                        pass
        
        # 重绘画布
        try:
            self.canvas.draw_idle()
        except:
            pass
    def update_module4_deform_combo(self):
        is_rectangle = self.module4_rect_radio.isChecked()
        index = self.module4_deform_combo.findText("Rectangular Scaling")
        if index >= 0:
            print(f"更新模块4下拉框：Rectangular Scaling 启用 = {is_rectangle}")
            self.module4_deform_combo.model().item(index).setEnabled(is_rectangle)
            # 如果当前选中的变形是被禁用的项，则切换到第一个可用项
            if self.module4_deform_combo.currentText() == "Rectangular Scaling" and not is_rectangle:
                self.module4_deform_combo.setCurrentIndex(0)

    # 连接四个单选按钮的信号

    # ------------------- 新增：模块4专用方法（不影响原有逻辑） -------------------
    def _module4_activate(self):
        """激活模块4，准备区域选择（完整修复版本）"""
        if not self.base_points:
            QMessageBox.warning(self, "Warning", "Please generate base pattern first!")
            return
        
        # 🔴 根据当前Custom单选按钮状态更新自定义模式widget可见性
        self.update_module4_custom_mode_visibility(self.module4_custom_radio.isChecked())
        
        # 🔴 确定区域类型和自定义模式
        region_type = 'circle'  # 默认值
        custom_mode = None
        
        if self.module4_rect_radio.isChecked():
            region_type = 'rectangle'
        elif self.module4_ellipse_radio.isChecked():
            region_type = 'ellipse'
        elif self.module4_custom_radio.isChecked():
            region_type = 'custom'
            if self.module4_line_radio.isChecked():
                custom_mode = 'line'
            elif self.module4_curve_radio.isChecked():
                custom_mode = 'curve'
            print(f"Module4激活: region_type={region_type}, custom_mode={custom_mode}")
        
        # 🔴 新增：清除3.Deformation Localization的选框
        self.type1_selected_region = None
        self.type1_canvas_interaction.clear_selection()
        self.is_type1_selecting = False
        
        # 更新类型①的状态提示
        self.type1_widget.update_status("select region to deform")
        self.type1_widget.disable_confirm_btn(True)
        
        # 停止其他模块交互
        self.is_type1_selecting = False
        
        # 完全重置模块4状态
        self._reset_module4_completely()
        
        # 初始化模块4
        self.module4 = Module4RegionSelector(
            ax=self.canvas.axes[1],
            params=self.base_params,
            callback=self._module4_on_regions_confirmed,
            parent=self
        )
        
        # 设置PyQt按钮引用
        self.module4.set_qt_button(self.module4_confirm_btn)
        
        # 🔴 关键：传递自定义模式参数
        self.module4.set_region_type(region_type, custom_mode)
        
        # 更新状态
        self.module4_status.setText("Status: Draw region on canvas")
        
        # 确保事件绑定正确
        self.update_buttons_state()
        
        # 🔧 关键修改：重新绘制所有内容，包括变形图案
        self._force_redraw_all()
        self.add_log(f"Module4 activated: {region_type} selection")
        # 设置完区域类型后，更新下拉框状态
        self.update_module4_deform_combo()
    def _enter_module4_selection(self, region_type, custom_mode):
        """模块4的实际激活逻辑（从 switch_to_module4 调用）"""
        # 这是原有的 _module4_activate 逻辑，但移除了重置模块3的部分
        
        # 完全重置模块4状态
        self._reset_module4_completely()
        
        # 初始化模块4
        self.module4 = Module4RegionSelector(
            ax=self.canvas.axes[1],
            params=self.base_params,
            callback=self._module4_on_regions_confirmed,
            parent=self
        )
        
        # 设置PyQt按钮引用
        self.module4.set_qt_button(self.module4_confirm_btn)
        
        # 设置区域类型
        self.module4.set_region_type(region_type, custom_mode)
        
        # 更新状态
        self.module4_status.setText("Status: Draw region on canvas")
        
        # 确保事件绑定正确
        self.update_buttons_state()
        
        # 关键修改：重新绘制所有内容，包括变形图案
        self._force_redraw_all()
        self.add_log(f"Module4 activated: {region_type} selection")
    def get_current_unfolded_path(self):
        """获取当前的unfold path坐标"""
        if not self.base_points or not self.base_params:
            return None
        
        current_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
        return StentUtils.generate_unfolded_path(self.base_points, current_points, self.base_params)

    def get_current_deformed_path_absolute(self):
        """获取当前deformed path的绝对坐标"""
        if self.current_deformed_points is not None:
            return self.current_deformed_points
        elif self.base_points:
            return self.base_points
        else:
            return None

    def get_current_deformed_path_relative(self):
        """获取当前deformed path的相对坐标（第一个点为绝对，后续为相对偏移）"""
        absolute_points = self.get_current_deformed_path_absolute()
        if not absolute_points:
            return None
        
        relative_points = [absolute_points[0]]  # 第一个点保留绝对坐标
        for i in range(1, len(absolute_points)):
            prev_x, prev_y = absolute_points[i-1]
            curr_x, curr_y = absolute_points[i]
            
            rel_x = curr_x - prev_x
            rel_y = curr_y - prev_y
            
            relative_points.append((round(rel_x, 3), round(rel_y, 3)))
        
        return relative_points
    def _module4_on_canvas_click(self, event):
        if not self.module4 or not event.inaxes == self.canvas.axes[1]:
            return
        # 移除旧的 draw_initial_region 调用，改为启动绘制
        self.module4.start_drawing(center=(event.xdata, event.ydata))  # 直接调用新方法

    # 在这里添加 _module4_confirm_regions 方法
    def _module4_confirm_regions(self):
        """模块4确认区域选择"""
        if self.module4:
            self.module4.on_confirm_button_clicked()
    def on_module4_custom_mode_changed(self, checked):
        """处理Module4自定义模式变更"""
        # 检查：只有当按钮被选中时才处理
        if not checked:
            return
        
        # 确定当前选中的模式
        if self.sender() == self.module4_line_radio:
            mode = 'line'
        elif self.sender() == self.module4_curve_radio:
            mode = 'curve'
        else:
            return
        
        print(f"Module4自定义模式更改为: {mode}")
        
        # 🔴 关键：更新Module4实例的模式
        if self.module4 and self.module4.region_type == 'custom':
            print(f"设置Module4的custom_mode为: {mode}")
            self.module4.set_custom_mode(mode)
            
            # 更新状态提示
            if mode == 'curve':
                self.module4_status.setText("Status: Click to add control points, curve will be auto-generated")
            else:
                self.module4_status.setText("Status: Click to add points, double-click to close")
        else:
            print(f"警告：无法设置Module4模式，当前region_type={self.module4.region_type if self.module4 else 'None'}")
    # 在 MainWindow 类的 _module4_on_regions_confirmed 方法中修改：
    def _module4_on_regions_confirmed(self, regions_info):
        """模块4区域确认回调：接收区域信息"""
        # 保存当前状态到历史栈（包括当前点集和区域信息）
        current_state = {
            'points': self.current_deformed_points.copy() if self.current_deformed_points is not None else self.base_points.copy(),
            'module4_regions': None,  # 上一状态没有模块4区域
            'type1_region': self.type1_selected_region  # 保留类型①区域
        }
        self.deform_history.append(current_state)
        self.undo_btn.setEnabled(True)  # 启用undo按钮
        
        self.module4_regions_info = regions_info
        self.update_buttons_state()
        

        # 根据区域类型过滤变形方式
        # 所有变形对所有形状可用
        # 所有变形对所有形状可用，无需过滤
        if regions_info:
            # 只需启用下拉框，不需要重新设置内容
            self.module4_deform_combo.setEnabled(True)
            
        # 更新状态提示
        self.module4_status.setText(f"Status: {len(regions_info)} regions ready - All deformation types available")
                
        # 重绘画布以显示选区框
        self._refresh_canvas_after_module4_change()
        self.add_log(f"Module4 regions confirmed: {len(regions_info)} regions")
    def _apply_independent_expansion(self, points, regions_info, A, B):
        """应用独立膨胀算法 - 修复：让B参数对所有形状都有效"""
        pts_x, pts_y = zip(*points)
        pts_x = np.array(pts_x)
        pts_y = np.array(pts_y)
        
        dx_total = np.zeros_like(pts_x)
        dy_total = np.zeros_like(pts_y)
        
        for region in regions_info:
            centroid = region['centroid']
            reg_type = region['type']
            
            if reg_type == 'circle':
                # 🔴 修复：圆形区域让B参数生效
                cx, cy = centroid
                radius = region['radius']
                
                # 变形强度直接使用A
                strength = A
                
                # 获取边界参数
                base_width = self.base_params['width']
                base_length = self.base_params['length']
                
                # 检查边界点
                border_mask = (
                    (np.abs(pts_x) < 1e-6) |
                    (np.abs(pts_x - base_width) < 1e-6) |
                    (np.abs(pts_y) < 1e-6) |
                    (np.abs(pts_y + base_length) < 1e-6)
                )
                
                rx = pts_x - cx
                ry = pts_y - cy
                r = np.sqrt(rx**2 + ry**2)
                
                # 只对圆形内且非边界点的点应用变形
                mask = (r <= radius) & (~border_mask)
                
                # 计算归一化距离
                t = np.zeros_like(r)
                t[mask] = r[mask] / radius
                
                # 🔴 修复：使用统一的过渡函数，让B参数生效
                # 过渡函数：(1 - t^2.5)^2 * exp(-B * t)
                transition = (1 - t[mask]**2.5) ** 2
                exponential_decay = np.exp(-B * t[mask])  # 🔴 B参数在这里生效！
                weight = strength * transition * exponential_decay
                
                # 应用变形（加法变形）
                dx = np.zeros_like(rx)
                dy = np.zeros_like(ry)
                dx[mask] = rx[mask] * weight
                dy[mask] = ry[mask] * weight
                
                dx_total += dx
                dy_total += dy
                
            elif reg_type == 'rectangle':
                # 矩形区域的膨胀 - 修复过渡函数，与其他形状保持一致
                cx, cy = centroid
                angle = region['angle']
                width = region['width']
                height = region['height']
                
                # 将角度转换为弧度
                angle_rad = np.radians(angle)
                cos_angle = np.cos(angle_rad)
                sin_angle = np.sin(angle_rad)
                
                # 将点转换到矩形的局部坐标系
                dx = pts_x - cx
                dy = pts_y - cy
                
                # 旋转到矩形的局部坐标系
                dx_rot = dx * cos_angle + dy * sin_angle
                dy_rot = -dx * sin_angle + dy * cos_angle
                
                # 计算点在矩形内的归一化距离
                x_norm = np.abs(dx_rot) / (width/2)
                y_norm = np.abs(dy_rot) / (height/2)
                norm_dist = np.maximum(x_norm, y_norm)
                
                # 🔴 修复：使用统一的过渡区域支持
                transition_factor = min(B * 0.3, 0.8)  # 过渡区域因子，限制最大值
                max_dist = 1.0 + transition_factor  # 最大有效距离（包含过渡区域）
                
                # 应用变形到矩形内和过渡区域内的点
                mask = norm_dist <= max_dist
                
                # 计算变形位移
                for i in np.where(mask)[0]:
                    dist_val = norm_dist[i]
                    
                    if dist_val <= 1.0:
                        # 区域内：使用统一的指数衰减公式
                        # 🔴 修复：使用与圆形一致的过渡函数 (1 - dist^2.5)^2
                        transition = (1 - dist_val**2.5) ** 2
                        exponential_decay = np.exp(-B * dist_val)
                        weight = A * transition * exponential_decay
                    else:
                        # 🔴 修复：过渡区域内，使用边界处的变形强度并衰减
                        transition_ratio = (max_dist - dist_val) / transition_factor
                        if transition_ratio > 0:
                            # 边界处的变形强度（dist_val=1.0）
                            border_transition = (1 - 1.0**2.5) ** 2
                            border_exponential = np.exp(-B * 1.0)
                            border_strength = A * border_transition * border_exponential
                            
                            # 计算衰减的变形强度
                            weight = border_strength * 0.15 * transition_ratio
                        else:
                            weight = 0
                    
                    if weight > 0:
                        # 在局部坐标系中应用变形
                        # 使用原始点到中心的距离，而不是归一化距离
                        dx_local = dx_rot[i] * weight
                        dy_local = dy_rot[i] * weight
                        
                        # 转换回全局坐标系
                        dx_global = dx_local * cos_angle - dy_local * sin_angle
                        dy_global = dx_local * sin_angle + dy_local * cos_angle
                        
                        dx_total[i] += dx_global
                        dy_total[i] += dy_global
                
            elif reg_type == 'ellipse':
                # 椭圆区域的膨胀 - 修复过渡函数
                cx, cy = centroid
                major_axis = region['major_axis']
                minor_axis = region['minor_axis']
                angle = region['angle']
                
                # 将角度转换为弧度
                angle_rad = np.radians(angle)
                cos_angle = np.cos(angle_rad)
                sin_angle = np.sin(angle_rad)
                
                # 将点转换到椭圆的局部坐标系
                dx = pts_x - cx
                dy = pts_y - cy
                
                # 旋转到椭圆的主轴坐标系
                dx_rot = dx * cos_angle + dy * sin_angle
                dy_rot = -dx * sin_angle + dy * cos_angle
                
                # 计算归一化距离（椭圆方程）
                norm_dist = np.sqrt((dx_rot / (major_axis/2))**2 + (dy_rot / (minor_axis/2))**2)
                
                # 只对椭圆内的点应用变形
                mask = norm_dist <= 1.0
                
                # 🔴 修复：使用统一的过渡函数
                scale = np.ones_like(pts_x)
                # 在椭圆区域内应用变形
                if np.any(mask):
                    # 计算变形权重：A * exp(-B * norm_dist) * (1 - norm_dist^2.5)^2
                    transition = (1 - norm_dist[mask]**2.5) ** 2
                    exponential_decay = np.exp(-B * norm_dist[mask])
                    scale_factor = A * transition * exponential_decay
                    scale[mask] = 1 + scale_factor
                
                # 应用变形（在局部坐标系中）
                dx_rot_deformed = dx_rot * scale
                dy_rot_deformed = dy_rot * scale
                
                # 转换回全局坐标系
                dx_deformed = dx_rot_deformed * cos_angle - dy_rot_deformed * sin_angle
                dy_deformed = dx_rot_deformed * sin_angle + dy_rot_deformed * cos_angle
                
                # 计算变形位移
                dx_total += dx_deformed - dx
                dy_total += dy_deformed - dy
                
            elif reg_type == 'custom':
                # 自定义区域的膨胀 - 修复过渡函数
                vertices = region['vertices']
                custom_polygon = ShapelyPolygon(vertices)
                
                # 计算区域中心
                centroid_x, centroid_y = centroid
                
                # 计算多边形的近似内接圆半径（最大内接圆）
                # 这是点到各边最小距离的最大值
                max_inscribed_radius = 0.0
                n = len(vertices)
                
                # 创建一个包含多边形内点的网格来计算内接圆半径
                # 简化的方法：计算中心点到各边的最小距离
                min_dist_to_edges = float('inf')
                for j in range(n):
                    x1, y1 = vertices[j]
                    x2, y2 = vertices[(j+1) % n]
                    
                    # 计算中心点到线段的距离
                    line_length_squared = (x2 - x1)**2 + (y2 - y1)**2
                    if line_length_squared == 0:
                        dist = math.hypot(centroid_x - x1, centroid_y - y1)
                    else:
                        t = max(0, min(1, ((centroid_x - x1) * (x2 - x1) + (centroid_y - y1) * (y2 - y1)) / line_length_squared))
                        proj_x = x1 + t * (x2 - x1)
                        proj_y = y1 + t * (y2 - y1)
                        dist = math.hypot(centroid_x - proj_x, centroid_y - proj_y)
                    
                    if dist < min_dist_to_edges:
                        min_dist_to_edges = dist
                
                approx_radius = min_dist_to_edges  # 内接圆半径
                
                for i in range(len(pts_x)):
                    point = ShapelyPoint(pts_x[i], pts_y[i])
                    if custom_polygon.contains(point):
                        # 计算点到区域中心的距离
                        dx = pts_x[i] - centroid_x
                        dy = pts_y[i] - centroid_y
                        dist = math.sqrt(dx**2 + dy**2)
                        
                        # 计算归一化距离（0在中心，1在边界）
                        if approx_radius > 0:
                            norm_dist = dist / approx_radius
                            norm_dist = max(0, min(1, norm_dist))
                            
                            # 🔴 修复：使用统一的过渡函数
                            transition = (1 - norm_dist**2.5) ** 2
                            exponential_decay = math.exp(-B * norm_dist)
                            scale_factor = A * transition * exponential_decay
                            
                            # 应用膨胀
                            dx_deform = dx * scale_factor
                            dy_deform = dy * scale_factor
                            
                            dx_total[i] += dx_deform
                            dy_total[i] += dy_deform
        
        # 应用总位移
        deformed_x = pts_x + dx_total
        deformed_y = pts_y + dy_total
        
        # 返回变形后的点
        return [(round(x, 3), round(y, 3)) for x, y in zip(deformed_x, deformed_y)]
    def _apply_single_circle_expansion(self, points, circle_region, A, B):
        """对单个圆形区域应用中心圆形的膨胀算法"""
        deformed = points.copy()
        cx, cy = circle_region['centroid']
        radius = circle_region['radius']
        
        # 变形强度直接使用A
        strength = A
        
        # 获取边界参数
        base_width = self.base_params['width']
        base_length = self.base_params['length']
        
        for i, (x, y) in enumerate(deformed):
            # 检查是否为边界点
            is_border_point = (
                math.isclose(x, 0, abs_tol=1e-6) or 
                math.isclose(x, base_width, abs_tol=1e-6) or 
                math.isclose(y, 0, abs_tol=1e-6) or 
                math.isclose(y, -base_length, abs_tol=1e-6)
            )
            
            if is_border_point:
                continue  # 边界点不变形
                
            dx = x - cx
            dy = y - cy
            distance = math.sqrt(dx**2 + dy**2)
            
            # 计算点到圆心的距离
            if distance <= radius:
                # 使用中心圆形的变形公式
                t = distance / radius
                # 中心圆形的过渡函数：(1 - t^2.5)^2
                transition = (1 - t**2.5) ** 2
                weight = strength * transition
                
                # 加法变形公式（与示例代码完全一致）
                new_x = x + dx * weight
                new_y = y + dy * weight
                
                # 四舍五入到小数点后3位
                deformed[i] = (round(new_x, 3), round(new_y, 3))
        
        return deformed
    # 修改 _module4_apply_deform 方法，在变形前保存状态：
    def _module4_apply_deform(self):
        """应用模块4变形（Code①/②/③逻辑）"""
        print("进入 _module4_apply_deform")
        deform_type = self.module4_deform_combo.currentText()
        print(f"当前变形类型: {deform_type}")
        if not self.module4_regions_info or not self.base_points:
            QMessageBox.warning(self, "Warning", "Select regions via Module 4 first!")
            return
        
        deform_type = self.module4_deform_combo.currentText()
        input_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
        
        # 保存当前状态到历史栈（包括当前点集和区域信息）
        current_state = {
            'points': input_points.copy(),
            'module4_regions': self.module4_regions_info.copy() if self.module4_regions_info else None,
            'type1_region': self.type1_selected_region.copy() if self.type1_selected_region else None
        }
        self.deform_history.append(current_state)
        self.undo_btn.setEnabled(True)
        
        # 类型①变形：弹出参数对话框
        if deform_type in ["Scaling", "Sine", "Twist"]:
            dialog = Type1DeformParamDialog(deform_type, self)
            if not dialog.exec_():
                return  # 用户取消
            params = dialog.get_params()
            if not params:
                return
            
            # 应用类型①变形算法
            deformed_points = self._apply_module4_with_type1_algo(
                input_points, self.module4_regions_info, deform_type, params
            )
            
            # 生成展开和3D投影
            unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 更新并绘图
            self.current_deformed_points = deformed_points
            self.plot_results(
                self.base_points, 
                deformed_points, 
                f"Deformation Periodization: {deform_type}",
                unfolded,
                cylinder_3d
            )
            # 🔴 在这里添加日志
            self.add_log(f"Applied Deformation Periodization (Type1 algo): {deform_type}")
            QMessageBox.information(self, "Success", "Deformation Periodization applied successfully!")
        
        # Code①：弹出参数对话框
        elif deform_type == "Exponential Expansion":
            # 现有代码...
            dialog = Module4ExpansionDialog(self)
            if not dialog.exec_():
                return  # 用户取消
            params = dialog.get_params()
            if not params:
                return
            A = params['A']
            B = params['B']
            
            # 应用独立膨胀算法（现在直接传递区域信息）
            deformed_points = self._apply_independent_expansion(input_points, self.module4_regions_info, A, B)
            
            # 生成展开和3D投影
            unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 更新并绘图
            self.current_deformed_points = deformed_points
            self.plot_results(
                self.base_points, 
                deformed_points, 
                f"Deformation Periodization: {deform_type}",
                unfolded,
                cylinder_3d
            )
            # 🔴 在这里添加日志
            self.add_log(f"Applied Deformation Periodization: Exponential Expansion, A={A}, B={B}")
            QMessageBox.information(self, "Success", "Deformation Periodization applied successfully!")
        elif deform_type == "Rectangular Scaling":
            rect_regions = [r for r in self.module4_regions_info if r['type'] == 'rectangle']
            if not rect_regions:
                QMessageBox.warning(self, "Warning", "No rectangular regions found for Rectangular Scaling.")
                return
            dialog = Type1DeformParamDialog(deform_type, self)
            if not dialog.exec_():
                return
            params = dialog.get_params()
            if not params:
                return
            deformed_points = input_points.copy()
            for idx, region in enumerate(rect_regions):
                print(f"\n--- Applying Rectangular Scaling to region {idx} ---")
                print(f"Region type: {region.get('type')}")
                if 'vertices' in region:
                    print(f"Vertices count: {len(region['vertices'])}")
                    print(f"Vertices: {region['vertices']}")
                else:
                    print("No vertices in region")
                
                type1_region = self._convert_module4_region_to_type1(region)
                print(f"Type1 region type: {type1_region.get('type')}")
                if 'vertices' in type1_region:
                    print(f"Type1 vertices count: {len(type1_region['vertices'])}")
                
                points_np = np.array(deformed_points)
                region_mask = RegionDeformer._point_in_region(points_np, type1_region)
                mask_sum = np.sum(region_mask)
                print(f"Points in region: {mask_sum} out of {len(points_np)}")
                
                if mask_sum == 0:
                    print("WARNING: No points in region! Deformation will have no effect.")
                    continue
                
                deformed_points = RegionDeformer._apply_rectangular_scaling(
                    points_np, region_mask, type1_region, params
                )
                
                # 检查变形前后是否有变化
                diff = np.linalg.norm(deformed_points - points_np, axis=1)
                changed = np.sum(diff > 1e-6)
                print(f"Points changed after deformation: {changed}")
            
            # ✅ 更新当前变形结果
            self.current_deformed_points = deformed_points

            # ✅ 重新绘图
            self.plot_results(
                self.base_points, 
                deformed_points, 
                "Module4: Rectangular Scaling",
                None,
                None
            )

            # ✅ 日志
            self.add_log("Applied Module4: Rectangular Scaling")

            # ✅ 提示
            QMessageBox.information(self, "Success", "Rectangular Scaling applied successfully!")
        # Code②：旋转矩形正弦波动
        elif deform_type == "Biaxial Sine Ripple":
            # 支持所有形状
            rect_regions = self.module4_regions_info
            
            # 弹出参数对话框
            dialog = Module4RectSineWaveDialog(self)
            if not dialog.exec_():
                return  # 用户取消
            params = dialog.get_params()
            if not params:
                return
            
            amplitude = params['amplitude']
            transition_distance = params['transition_distance']
            cycles = params['cycles']
            
            deformed_points = input_points.copy()
            
            # 遍历所有区域应用变形
            for region in rect_regions:
                centroid = region['centroid']
                reg_type = region['type']
                
                if reg_type == 'rectangle':
                    # 原有矩形处理逻辑
                    angle = region['angle']
                    width = region['width']
                    height = region['height']
                    
                    # 动态计算有效长度和ω
                    tilt_angle_rad = np.radians(angle)
                    effective_length = max(width, height)
                    omega = (cycles * 2 * np.pi) / effective_length
                    
                    cos_theta = np.cos(tilt_angle_rad)
                    sin_theta = np.sin(tilt_angle_rad)
                    
                    for i, (x, y) in enumerate(deformed_points):
                        # 转换到局部坐标系
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        
                        local_x = dx * cos_theta + dy * sin_theta
                        local_y = -dx * sin_theta + dy * cos_theta
                        
                        # 检查点是否在矩形内
                        if abs(local_x) <= width/2 and abs(local_y) <= height/2:
                            # 计算到矩形边界的距离（用于过渡权重）
                            dist_to_edge_x = width/2 - abs(local_x)
                            dist_to_edge_y = height/2 - abs(local_y)
                            min_dist = min(dist_to_edge_x, dist_to_edge_y)
                            
                            # 计算过渡权重
                            if min_dist >= transition_distance:
                                weight = 1.0
                            elif min_dist > 0:
                                weight = 0.5 * (1 + np.cos(np.pi * (transition_distance - min_dist) / transition_distance))
                            else:
                                weight = 0.0
                            
                            # 正弦波动
                            deform_x = amplitude * weight * np.sin(omega * local_x)
                            deform_y = amplitude * weight * np.sin(omega * local_y)
                            
                            # 应用变形
                            local_x_def = local_x + deform_x
                            local_y_def = local_y + deform_y
                            
                            x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                            y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                            deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                            
                elif reg_type == 'circle':
                    # 圆形区域的矩形正弦波
                    radius = region['radius']
                    
                    # 为圆形定义一个默认方向（比如水平方向）
                    angle = 0  # 水平方向
                    effective_length = radius * 2  # 使用直径作为有效长度
                    
                    cos_theta = np.cos(np.radians(angle))
                    sin_theta = np.sin(np.radians(angle))
                    
                    for i, (x, y) in enumerate(deformed_points):
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        r = np.sqrt(dx**2 + dy**2)
                        
                        # 检查点是否在圆形内
                        if r <= radius:
                            # 转换到局部坐标系
                            local_x = dx * cos_theta + dy * sin_theta
                            local_y = -dx * sin_theta + dy * cos_theta
                            
                            # 计算到边界的距离
                            dist_to_edge = radius - r
                            
                            # 计算过渡权重
                            if dist_to_edge >= transition_distance:
                                weight = 1.0
                            elif dist_to_edge > 0:
                                weight = 0.5 * (1 + np.cos(np.pi * (transition_distance - dist_to_edge) / transition_distance))
                            else:
                                weight = 0.0
                            
                            # 正弦波动
                            omega = (cycles * 2 * np.pi) / effective_length
                            deform_x = amplitude * weight * np.sin(omega * local_x)
                            deform_y = amplitude * weight * np.sin(omega * local_y)
                            
                            # 应用变形
                            local_x_def = local_x + deform_x
                            local_y_def = local_y + deform_y
                            
                            x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                            y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                            deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                            
                elif reg_type == 'ellipse':
                    # 椭圆区域的矩形正弦波
                    major_axis = region['major_axis']
                    minor_axis = region['minor_axis']
                    angle = region['angle']  # 使用椭圆的角度作为方向
                    
                    effective_length = major_axis  # 使用长轴作为有效长度
                    
                    cos_theta = np.cos(np.radians(angle))
                    sin_theta = np.sin(np.radians(angle))
                    
                    for i, (x, y) in enumerate(deformed_points):
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        
                        # 转换到椭圆的主轴坐标系
                        dx_rot = dx * cos_theta + dy * sin_theta
                        dy_rot = -dx * sin_theta + dy * cos_theta
                        
                        # 检查点是否在椭圆内
                        normalized_r = np.sqrt((dx_rot / (major_axis/2))**2 + (dy_rot / (minor_axis/2))**2)
                        
                        if normalized_r <= 1.0:
                            # 计算到边界的距离（近似）
                            dist_to_edge = (1.0 - normalized_r) * min(major_axis/2, minor_axis/2)
                            
                            # 计算过渡权重
                            if dist_to_edge >= transition_distance:
                                weight = 1.0
                            elif dist_to_edge > 0:
                                weight = 0.5 * (1 + np.cos(np.pi * (transition_distance - dist_to_edge) / transition_distance))
                            else:
                                weight = 0.0
                            
                            # 正弦波动
                            omega = (cycles * 2 * np.pi) / effective_length
                            deform_x = amplitude * weight * np.sin(omega * dx_rot)
                            deform_y = amplitude * weight * np.sin(omega * dy_rot)
                            
                            # 应用变形
                            local_x_def = dx_rot + deform_x
                            local_y_def = dy_rot + deform_y
                            
                            x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                            y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                            deformed_points[i] = (round(x_def, 3), round(y_def, 3))

                elif reg_type == 'custom':
                    # 自定义区域的矩形正弦波
                    vertices = region['vertices']
                    custom_polygon = ShapelyPolygon(vertices)
                    
                    # 使用最小外接矩形确定方向
                    min_rotated_rect = custom_polygon.minimum_rotated_rectangle
                    rect_coords = list(min_rotated_rect.exterior.coords)
                    
                    # 计算主轴方向
                    dx_dir = rect_coords[1][0] - rect_coords[0][0]
                    dy_dir = rect_coords[1][1] - rect_coords[0][1]
                    angle = math.degrees(math.atan2(dy_dir, dx_dir))
                    angle_rad = math.radians(angle)
                    
                    cos_theta = math.cos(angle_rad)
                    sin_theta = math.sin(angle_rad)
                    
                    # 计算有效长度（使用外接矩形的对角线长度）
                    width = math.hypot(rect_coords[1][0] - rect_coords[0][0], rect_coords[1][1] - rect_coords[0][1])
                    height = math.hypot(rect_coords[2][0] - rect_coords[1][0], rect_coords[2][1] - rect_coords[1][1])
                    effective_length = max(width, height)
                    
                    for i, (x, y) in enumerate(deformed_points):
                        point = ShapelyPoint(x, y)
                        if custom_polygon.contains(point):
                            # 转换到局部坐标系
                            dx_local = x - centroid[0]
                            dy_local = y - centroid[1]
                            
                            local_x = dx_local * cos_theta + dy_local * sin_theta
                            local_y = -dx_local * sin_theta + dy_local * cos_theta
                            
                            # 计算到边界的距离
                            min_dist = float('inf')
                            n = len(vertices)
                            for j in range(n):
                                x1, y1 = vertices[j]
                                x2, y2 = vertices[(j+1) % n]
                                
                                # 计算点到线段的距离
                                line_length_squared = (x2 - x1)**2 + (y2 - y1)**2
                                if line_length_squared == 0:
                                    dist = math.hypot(x - x1, y - y1)
                                else:
                                    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_squared))
                                    proj_x = x1 + t * (x2 - x1)
                                    proj_y = y1 + t * (y2 - y1)
                                    dist = math.hypot(x - proj_x, y - proj_y)
                                
                                if dist < min_dist:
                                    min_dist = dist
                            
                            # 计算过渡权重
                            if min_dist >= transition_distance:
                                weight = 1.0
                            elif min_dist > 0:
                                weight = 0.5 * (1 + math.cos(math.pi * (transition_distance - min_dist) / transition_distance))
                            else:
                                weight = 0.0
                            
                            # 正弦波动
                            omega = (cycles * 2 * math.pi) / effective_length
                            deform_x = amplitude * weight * math.sin(omega * local_x)
                            deform_y = amplitude * weight * math.sin(omega * local_y)
                            
                            # 应用变形
                            local_x_def = local_x + deform_x
                            local_y_def = local_y + deform_y
                            
                            x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                            y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                            
                            # 检查变形是否有效
                            if not (math.isnan(x_def) or math.isnan(y_def)):
                                deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                
            # 生成展开和3D投影
            unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 更新并绘图
            self.current_deformed_points = deformed_points
            self.plot_results(
                self.base_points, 
                deformed_points, 
                f"Deformation Periodization: {deform_type}",
                unfolded,
                cylinder_3d
            )
            # 🔴 在这里添加日志
            self.add_log(f"Applied Deformation Periodization: Biaxial Sine Ripple, amplitude={amplitude}, cycles={cycles}")
            QMessageBox.information(self, "Success", "Deformation Periodization applied successfully!")
        
        # Code③：极坐标波动（圆形/椭圆/矩形/自定义）
        elif deform_type == "Polar Wave":
            # 检查是否有区域
            polar_regions = self.module4_regions_info
            
            # 添加调试信息
            print(f"Polar Wave: Applying to {len(polar_regions)} regions")
            for i, region in enumerate(polar_regions):
                print(f"Region {i}: type={region['type']}, centroid={region['centroid']}")
            
            # 弹出参数对话框
            dialog = Module4PolarWaveDialog(self)
            if not dialog.exec_():
                return  # 用户取消
            params = dialog.get_params()
            if not params:
                return
            
            A = params['A']
            B = params['B'] 
            C = params['C']
            
            # 添加参数调试信息
            print(f"Polar Wave parameters: A={A}, B={B}, C={C}")
            
            deformed_points = input_points.copy()
            
            # 遍历所有区域应用变形
            for region in polar_regions:
                centroid = region['centroid']
                reg_type = region['type']
                
                if reg_type == 'circle':
                    # 圆形区域的极坐标波动
                    radius = region['radius']
                    
                    for i, (x, y) in enumerate(deformed_points):
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        r = np.sqrt(dx**2 + dy**2)
                        
                        # 检查点是否在圆形内
                        if r <= radius:
                            # 极坐标波动计算
                            wave_term = A * np.cos(C * r) * np.exp(-B * r)
                            r_deformed = r * (1 + wave_term)
                            
                            # 计算角度
                            theta = np.arctan2(dy, dx)
                            
                            # 转换回笛卡尔坐标
                            x_deformed = r_deformed * np.cos(theta) + centroid[0]
                            y_deformed = r_deformed * np.sin(theta) + centroid[1]
                            deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
                            
                elif reg_type == 'ellipse':
                    # 椭圆区域的极坐标波动
                    major_axis = region['major_axis']
                    minor_axis = region['minor_axis']
                    angle = region['angle']
                    
                    # 旋转角度（弧度）
                    angle_rad = np.radians(angle)
                    cos_angle = np.cos(angle_rad)
                    sin_angle = np.sin(angle_rad)
                    
                    for i, (x, y) in enumerate(deformed_points):
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        
                        # 旋转到椭圆的主轴坐标系
                        dx_rot = dx * cos_angle + dy * sin_angle
                        dy_rot = -dx * sin_angle + dy * cos_angle
                        
                        # 检查点是否在椭圆内
                        normalized_r = np.sqrt((dx_rot / (major_axis/2))**2 + (dy_rot / (minor_axis/2))**2)
                        
                        if normalized_r <= 1.0:
                            # 计算实际距离
                            r = np.sqrt(dx**2 + dy**2)
                            
                            # 极坐标波动计算
                            wave_term = A * np.cos(C * r) * np.exp(-B * r)
                            r_deformed = r * (1 + wave_term)
                            
                            # 计算角度
                            theta = np.arctan2(dy, dx)
                            
                            # 转换回笛卡尔坐标
                            x_deformed = r_deformed * np.cos(theta) + centroid[0]
                            y_deformed = r_deformed * np.sin(theta) + centroid[1]
                            deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
                elif reg_type == 'triangle':
                    # 🔴 修正：确保这里使用的是Polar Wave参数A、B、C
                    vertices = region['vertices']
                    
                    # 创建三角形多边形
                    triangle_polygon = ShapelyPolygon(vertices)
                    
                    # 计算三角形内点到中心的最大距离
                    max_r_in_triangle = 0.0
                    for vx, vy in vertices:
                        dist = math.hypot(vx - centroid[0], vy - centroid[1])
                        if dist > max_r_in_triangle:
                            max_r_in_triangle = dist
                    
                    if max_r_in_triangle > 0:
                        for i, (x, y) in enumerate(deformed_points):
                            point = ShapelyPoint(x, y)
                            if triangle_polygon.contains(point):
                                dx = x - centroid[0]
                                dy = y - centroid[1]
                                r = math.hypot(dx, dy)
                                
                                # 使用三角形内最大距离进行归一化
                                normalized_r = r / max_r_in_triangle
                                
                                # 🔴 关键：使用Polar Wave参数A、B、C
                                wave_term = A * math.cos(C * normalized_r) * math.exp(-B * normalized_r)
                                r_deformed = r * (1 + wave_term)
                                
                                theta = math.atan2(dy, dx)
                                x_deformed = centroid[0] + r_deformed * math.cos(theta)
                                y_deformed = centroid[1] + r_deformed * math.sin(theta)
                                deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
                            
                elif reg_type == 'rectangle':
                    # 矩形区域的极坐标波动
                    width = region['width']
                    height = region['height']
                    angle = region['angle']
                    
                    # 旋转角度（弧度）
                    angle_rad = np.radians(angle)
                    cos_angle = np.cos(angle_rad)
                    sin_angle = np.sin(angle_rad)
                    
                    for i, (x, y) in enumerate(deformed_points):
                        dx = x - centroid[0]
                        dy = y - centroid[1]
                        
                        # 旋转到矩形的局部坐标系
                        dx_rot = dx * cos_angle + dy * sin_angle
                        dy_rot = -dx * sin_angle + dy * cos_angle
                        
                        # 检查点是否在矩形内
                        if abs(dx_rot) <= width/2 and abs(dy_rot) <= height/2:
                            # 计算到矩形中心的实际距离和角度（在全局坐标系中）
                            r = np.sqrt(dx**2 + dy**2)
                            theta = np.arctan2(dy, dx)
                            
                            # 极坐标波动计算
                            wave_term = A * np.cos(C * r) * np.exp(-B * r)
                            r_deformed = r * (1 + wave_term)
                            
                            # 转换回笛卡尔坐标
                            x_deformed = r_deformed * np.cos(theta) + centroid[0]
                            y_deformed = r_deformed * np.sin(theta) + centroid[1]
                            deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
                
                elif reg_type == 'custom':
                    # 自定义区域的极坐标波动
                    vertices = region['vertices']
                    custom_polygon = ShapelyPolygon(vertices)
                    
                    for i, (x, y) in enumerate(deformed_points):
                        point = ShapelyPoint(x, y)
                        if custom_polygon.contains(point):
                            dx = x - centroid[0]
                            dy = y - centroid[1]
                            r = math.sqrt(dx**2 + dy**2)
                            
                            # 极坐标波动计算
                            wave_term = A * math.cos(C * r) * math.exp(-B * r)
                            r_deformed = r * (1 + wave_term)
                            
                            # 计算角度
                            theta = math.atan2(dy, dx)
                            
                            # 转换回笛卡尔坐标
                            x_deformed = r_deformed * math.cos(theta) + centroid[0]
                            y_deformed = r_deformed * math.sin(theta) + centroid[1]
                            deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
            
            # 在 Polar Wave 变形的循环结束后添加统计信息
            deformed_count = 0
            for i in range(len(input_points)):
                if input_points[i] != deformed_points[i]:
                    deformed_count += 1

            print(f"Polar Wave: {deformed_count} points were deformed out of {len(input_points)} total points")

            if deformed_count == 0:
                print("Warning: No points were deformed. Possible issues:")
                print("- Points are outside the selected regions")
                print("- Parameters A, B, C might be too small")
                print("- Check region boundaries")
            
            # 生成展开和3D投影
            unfolded = StentUtils.generate_unfolded_path(self.base_points, deformed_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 更新并绘图
            self.current_deformed_points = deformed_points
            self.plot_results(
                self.base_points, 
                deformed_points, 
                f"Deformation Periodization: {deform_type}",
                unfolded,
                cylinder_3d
            )
            
            QMessageBox.information(self, "Success", "Polar Wave deformation applied successfully!")
            self.add_log(f"Applied Deformation Periodization: {deform_type}")

    def _apply_type1_with_module4_algo(self, points, region, deform_type, params):
        """在类型①区域中应用模块4的变形算法"""
        # 将类型①的区域格式转换为模块4的区域信息格式
        module4_region = self._convert_type1_region_to_module4(region)
        regions_info = [module4_region]  # 包装成列表，因为模块4算法需要区域列表
        
        # 调用对应的模块4变形算法
        if deform_type == "Exponential Expansion":
            A = params['A']
            B = params['B']
            return self._apply_independent_expansion(points, regions_info, A, B)
        elif deform_type == "Biaxial Sine Ripple":
            amplitude = params['amplitude']
            transition_distance = params['transition_distance']
            cycles = params['cycles']
            return self._apply_rect_sine_wave_to_points(points, regions_info, amplitude, transition_distance, cycles)
        else:
            return points  # 其他类型返回原值

    def _convert_type1_region_to_module4(self, type1_region):
        """将类型①的区域格式转换为模块4的区域信息格式"""
        region_type = type1_region['type']
        module4_region = {}
        
        if region_type == 'circle':
            module4_region = {
                'type': 'circle',
                'centroid': type1_region['center'],
                'radius': type1_region['radius']
            }
        elif region_type == 'square':
            # 模块4中没有正方形，我们用矩形表示，宽度和高度相等
            module4_region = {
                'type': 'rectangle',
                'centroid': type1_region['center'],
                'width': type1_region['side_length'],
                'height': type1_region['side_length'],
                'angle': 0  # 类型①的正方形没有旋转，所以角度为0
            }
        elif region_type == 'ellipse':
            module4_region = {
                'type': 'ellipse',
                'centroid': type1_region['center'],
                'major_axis': type1_region['semi_major'] * 2,  # 类型①存储的是半轴，模块4存储的是整个轴长
                'minor_axis': type1_region['semi_minor'] * 2,
                'angle': 0  # 类型①的椭圆没有旋转，所以角度为0
            }
        elif region_type in ['triangle', 'custom']:
            # 对于三角形和自定义多边形，我们转换为自定义区域
            module4_region = {
                'type': 'custom',
                'centroid': type1_region['center'],
                'vertices': type1_region['vertices']
            }
        
        return module4_region
    def _apply_polar_wave_to_points(self, points, regions_info, A, B, C):
        """将极坐标波动算法应用到点集"""
        deformed_points = points.copy()
        
        for region in regions_info:
            centroid = region['centroid']
            reg_type = region['type']
            
            for i, (x, y) in enumerate(deformed_points):
                dx = x - centroid[0]
                dy = y - centroid[1]
                r = math.sqrt(dx**2 + dy**2)
                
                # 检查点是否在区域内
                if self._is_point_in_region((x, y), region):
                    # 极坐标波动计算
                    wave_term = A * math.cos(C * r) * math.exp(-B * r)
                    r_deformed = r * (1 + wave_term)
                    
                    # 计算角度
                    theta = math.atan2(dy, dx)
                    
                    # 转换回笛卡尔坐标
                    x_deformed = r_deformed * math.cos(theta) + centroid[0]
                    y_deformed = r_deformed * math.sin(theta) + centroid[1]
                    deformed_points[i] = (round(x_deformed, 3), round(y_deformed, 3))
        
        return deformed_points

    def _apply_rect_sine_wave_to_points(self, points, regions_info, amplitude, transition_distance, cycles):
        """将矩形正弦波算法应用到点集（支持所有区域类型）"""
        deformed_points = points.copy()
        
        for region in regions_info:
            centroid = region['centroid']
            reg_type = region['type']
            
            if reg_type == 'rectangle':
                # 矩形区域的矩形正弦波
                width = region['width']
                height = region['height']
                angle = region.get('angle', 0)
                
                # 动态计算有效长度和ω
                tilt_angle_rad = math.radians(angle)
                effective_length = max(width, height)
                omega = (cycles * 2 * math.pi) / effective_length
                
                cos_theta = math.cos(tilt_angle_rad)
                sin_theta = math.sin(tilt_angle_rad)
                
                for i, (x, y) in enumerate(deformed_points):
                    # 转换到局部坐标系
                    dx = x - centroid[0]
                    dy = y - centroid[1]
                    
                    local_x = dx * cos_theta + dy * sin_theta
                    local_y = -dx * sin_theta + dy * cos_theta
                    
                    # 检查点是否在矩形内
                    if abs(local_x) <= width/2 and abs(local_y) <= height/2:
                        # 计算到矩形边界的距离（用于过渡权重）
                        dist_to_edge_x = width/2 - abs(local_x)
                        dist_to_edge_y = height/2 - abs(local_y)
                        min_dist = min(dist_to_edge_x, dist_to_edge_y)
                        
                        # 计算过渡权重
                        if min_dist >= transition_distance:
                            weight = 1.0
                        elif min_dist > 0:
                            weight = 0.5 * (1 + math.cos(math.pi * (transition_distance - min_dist) / transition_distance))
                        else:
                            weight = 0.0
                        
                        # 正弦波动
                        deform_x = amplitude * weight * math.sin(omega * local_x)
                        deform_y = amplitude * weight * math.sin(omega * local_y)
                        
                        # 应用变形
                        local_x_def = local_x + deform_x
                        local_y_def = local_y + deform_y
                        
                        x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                        y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                        deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                        
            elif reg_type == 'circle':
                # 圆形区域的矩形正弦波
                radius = region['radius']
                
                # 为圆形定义一个默认方向（比如水平方向）
                angle = 0  # 水平方向
                effective_length = radius * 2  # 使用直径作为有效长度
                
                cos_theta = math.cos(math.radians(angle))
                sin_theta = math.sin(math.radians(angle))
                
                for i, (x, y) in enumerate(deformed_points):
                    dx = x - centroid[0]
                    dy = y - centroid[1]
                    r = math.sqrt(dx**2 + dy**2)
                    
                    # 检查点是否在圆形内
                    if r <= radius:
                        # 转换到局部坐标系
                        local_x = dx * cos_theta + dy * sin_theta
                        local_y = -dx * sin_theta + dy * cos_theta
                        
                        # 计算到边界的距离
                        dist_to_edge = radius - r
                        
                        # 计算过渡权重
                        if dist_to_edge >= transition_distance:
                            weight = 1.0
                        elif dist_to_edge > 0:
                            weight = 0.5 * (1 + math.cos(math.pi * (transition_distance - dist_to_edge) / transition_distance))
                        else:
                            weight = 0.0
                        
                        # 正弦波动
                        omega = (cycles * 2 * math.pi) / effective_length
                        deform_x = amplitude * weight * math.sin(omega * local_x)
                        deform_y = amplitude * weight * math.sin(omega * local_y)
                        
                        # 应用变形
                        local_x_def = local_x + deform_x
                        local_y_def = local_y + deform_y
                        
                        x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                        y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                        deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                        
            elif reg_type == 'ellipse':
                # 椭圆区域的矩形正弦波
                major_axis = region['major_axis']
                minor_axis = region['minor_axis']
                angle = region['angle']  # 使用椭圆的角度作为方向
                
                effective_length = major_axis  # 使用长轴作为有效长度
                
                cos_theta = math.cos(math.radians(angle))
                sin_theta = math.sin(math.radians(angle))
                
                for i, (x, y) in enumerate(deformed_points):
                    dx = x - centroid[0]
                    dy = y - centroid[1]
                    
                    # 转换到椭圆的主轴坐标系
                    dx_rot = dx * cos_theta + dy * sin_theta
                    dy_rot = -dx * sin_theta + dy * cos_theta
                    
                    # 检查点是否在椭圆内
                    normalized_r = math.sqrt((dx_rot / (major_axis/2))**2 + (dy_rot / (minor_axis/2))**2)
                    
                    if normalized_r <= 1.0:
                        # 计算到边界的距离（近似）
                        dist_to_edge = (1.0 - normalized_r) * min(major_axis/2, minor_axis/2)
                        
                        # 计算过渡权重
                        if dist_to_edge >= transition_distance:
                            weight = 1.0
                        elif dist_to_edge > 0:
                            weight = 0.5 * (1 + math.cos(math.pi * (transition_distance - dist_to_edge) / transition_distance))
                        else:
                            weight = 0.0
                        
                        # 正弦波动
                        omega = (cycles * 2 * math.pi) / effective_length
                        deform_x = amplitude * weight * math.sin(omega * dx_rot)
                        deform_y = amplitude * weight * math.sin(omega * dy_rot)
                        
                        # 应用变形
                        local_x_def = dx_rot + deform_x
                        local_y_def = dy_rot + deform_y
                        
                        x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                        y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                        deformed_points[i] = (round(x_def, 3), round(y_def, 3))
                
            elif reg_type == 'custom':
                # 自定义区域的矩形正弦波
                vertices = region['vertices']
                custom_polygon = ShapelyPolygon(vertices)
                
                # 使用最小外接矩形确定方向
                min_rotated_rect = custom_polygon.minimum_rotated_rectangle
                rect_coords = list(min_rotated_rect.exterior.coords)
                
                # 计算主轴方向
                dx_dir = rect_coords[1][0] - rect_coords[0][0]
                dy_dir = rect_coords[1][1] - rect_coords[0][1]
                angle = math.degrees(math.atan2(dy_dir, dx_dir))
                angle_rad = math.radians(angle)
                
                cos_theta = math.cos(angle_rad)
                sin_theta = math.sin(angle_rad)
                
                # 计算有效长度（使用外接矩形的对角线长度）
                width = math.hypot(rect_coords[1][0] - rect_coords[0][0], rect_coords[1][1] - rect_coords[0][1])
                height = math.hypot(rect_coords[2][0] - rect_coords[1][0], rect_coords[2][1] - rect_coords[1][1])
                effective_length = max(width, height)
                
                for i, (x, y) in enumerate(deformed_points):
                    point = ShapelyPoint(x, y)
                    if custom_polygon.contains(point):
                        # 转换到局部坐标系
                        dx_local = x - centroid[0]
                        dy_local = y - centroid[1]
                        
                        local_x = dx_local * cos_theta + dy_local * sin_theta
                        local_y = -dx_local * sin_theta + dy_local * cos_theta
                        
                        # 计算到边界的距离
                        min_dist = float('inf')
                        n = len(vertices)
                        for j in range(n):
                            x1, y1 = vertices[j]
                            x2, y2 = vertices[(j+1) % n]
                            
                            # 计算点到线段的距离
                            line_length_squared = (x2 - x1)**2 + (y2 - y1)**2
                            if line_length_squared == 0:
                                dist = math.hypot(x - x1, y - y1)
                            else:
                                t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_squared))
                                proj_x = x1 + t * (x2 - x1)
                                proj_y = y1 + t * (y2 - y1)
                                dist = math.hypot(x - proj_x, y - proj_y)
                            
                            if dist < min_dist:
                                min_dist = dist
                        
                        # 计算过渡权重
                        if min_dist >= transition_distance:
                            weight = 1.0
                        elif min_dist > 0:
                            weight = 0.5 * (1 + math.cos(math.pi * (transition_distance - min_dist) / transition_distance))
                        else:
                            weight = 0.0
                        
                        # 正弦波动
                        omega = (cycles * 2 * math.pi) / effective_length
                        deform_x = amplitude * weight * math.sin(omega * local_x)
                        deform_y = amplitude * weight * math.sin(omega * local_y)
                        
                        # 应用变形
                        local_x_def = local_x + deform_x
                        local_y_def = local_y + deform_y
                        
                        x_def = local_x_def * cos_theta - local_y_def * sin_theta + centroid[0]
                        y_def = local_x_def * sin_theta + local_y_def * cos_theta + centroid[1]
                        
                        # 检查变形是否有效
                        if not (math.isnan(x_def) or math.isnan(y_def)):
                            deformed_points[i] = (round(x_def, 3), round(y_def, 3))
        
        return deformed_points

    def _is_point_in_region(self, point, region):
        """判断点是否在区域内（简化版本）"""
        x, y = point
        centroid = region['centroid']
        reg_type = region['type']
        
        if reg_type == 'circle':
            radius = region['radius']
            dx = x - centroid[0]
            dy = y - centroid[1]
            return math.sqrt(dx**2 + dy**2) <= radius
        elif reg_type == 'rectangle':
            width = region['width']
            height = region['height']
            angle = region.get('angle', 0)
            
            # 旋转到局部坐标系
            angle_rad = math.radians(angle)
            cos_angle = math.cos(angle_rad)
            sin_angle = math.sin(angle_rad)
            
            dx = x - centroid[0]
            dy = y - centroid[1]
            
            local_x = dx * cos_angle + dy * sin_angle
            local_y = -dx * sin_angle + dy * cos_angle
            
            return abs(local_x) <= width/2 and abs(local_y) <= height/2
        elif reg_type == 'ellipse':
            major_axis = region['major_axis']
            minor_axis = region['minor_axis']
            angle = region.get('angle', 0)
            
            # 旋转到椭圆的主轴坐标系
            angle_rad = math.radians(angle)
            cos_angle = math.cos(angle_rad)
            sin_angle = math.sin(angle_rad)
            
            dx = x - centroid[0]
            dy = y - centroid[1]
            
            dx_rot = dx * cos_angle + dy * sin_angle
            dy_rot = -dx * sin_angle + dy * cos_angle
            
            # 检查是否在椭圆内
            normalized_r = math.sqrt((dx_rot / (major_axis/2))**2 + (dy_rot / (minor_axis/2))**2)
            return normalized_r <= 1.0
        elif reg_type == 'custom':
            # 对于自定义区域，使用简单的边界框检查
            vertices = region['vertices']
            min_x = min(v[0] for v in vertices)
            max_x = max(v[0] for v in vertices)
            min_y = min(v[1] for v in vertices)
            max_y = max(v[1] for v in vertices)
            return min_x <= x <= max_x and min_y <= y <= max_y
        
        return False
    def _get_rectangle_vertices(self, rect_info):
        """计算矩形的四个顶点（考虑旋转）"""
        cx, cy = rect_info['centroid']
        width = rect_info['width']
        height = rect_info['height']
        angle = rect_info.get('angle', 0)  # 旋转角度（度）
        
        print(f"🔍 DEBUG _get_rectangle_vertices:")
        print(f"  centroid: ({cx}, {cy})")
        print(f"  width: {width}, height: {height}")
        print(f"  angle: {angle}")
        
        # 矩形的四个角（未旋转前）
        half_w = width / 2
        half_h = height / 2
        corners = [
            (-half_w, -half_h),  # 左下
            (half_w, -half_h),   # 右下
            (half_w, half_h),    # 右上
            (-half_w, half_h)    # 左上
        ]
        
        # 如果有旋转角度，旋转所有顶点
        if angle != 0:
            angle_rad = math.radians(angle)
            cos_theta = math.cos(angle_rad)
            sin_theta = math.sin(angle_rad)
            
            rotated_corners = []
            for dx, dy in corners:
                # 旋转顶点
                dx_rot = dx * cos_theta - dy * sin_theta
                dy_rot = dx * sin_theta + dy * cos_theta
                # 平移到中心点位置
                rotated_corners.append((cx + dx_rot, cy + dy_rot))
                
            print(f"  rotated vertices: {rotated_corners}")
            return rotated_corners
        
        # 没有旋转的情况
        vertices = [
            (cx - half_w, cy - half_h),  # 左下
            (cx + half_w, cy - half_h),  # 右下
            (cx + half_w, cy + half_h),  # 右上
            (cx - half_w, cy + half_h)   # 左上
        ]
        
        print(f"  no rotation vertices: {vertices}")
        return vertices
    def _convert_module4_region_to_type1(self, module4_region):
        """将模块4的区域格式转换为类型①的区域格式"""
        print(f"🔍 DEBUG _convert_module4_region_to_type1:")
        print(f"  Input region type: {module4_region.get('type')}")
        print(f"  Input data keys: {list(module4_region.keys())}")
        if 'angle' in module4_region:
            print(f"  Input angle: {module4_region.get('angle')}")
        region_type = module4_region['type']
        type1_region = {}
        
        if region_type == 'circle':
            type1_region = {
                'type': 'circle',
                'center': module4_region['centroid'],
                'radius': module4_region['radius']
            }
            
            
        elif region_type == 'ellipse':
            type1_region = {
                'type': 'ellipse',
                'center': module4_region['centroid'],
                'semi_major': module4_region['major_axis'] / 2,
                'semi_minor': module4_region['minor_axis'] / 2,
                'angle': module4_region.get('angle', 0)  # 添加旋转角度
            }
            
        elif region_type == 'custom':
            type1_region = {
                'type': 'custom',
                'center': module4_region['centroid'],
                'vertices': module4_region['vertices']
            }
        elif region_type == 'rectangle':
            if 'vertices' in module4_region and module4_region['vertices']:
                vertices = module4_region['vertices']
                type1_region = {
                    'type': 'rectangle',
                    'center': module4_region['centroid'],
                    'width': module4_region['width'],
                    'height': module4_region['height'],
                    'angle': module4_region.get('angle', 0),
                    'vertices': vertices   # 保留原始顶点
                }
            else:
                # 兼容旧数据
                type1_region = {
                    'type': 'rectangle',
                    'center': module4_region['centroid'],
                    'width': module4_region['width'],
                    'height': module4_region['height'],
                    'angle': module4_region.get('angle', 0)
                }
        
        # 添加基础尺寸参数
        if hasattr(self, 'base_params') and self.base_params:
            type1_region['base_length'] = self.base_params['length']
            type1_region['base_width'] = self.base_params['width']
        print(f"  Output type1_region type: {type1_region.get('type')}")
        if 'vertices' in type1_region:
            print(f"  Output vertices: {type1_region.get('vertices')}")
        return type1_region
    def _apply_module4_with_type1_algo(self, points, module4_regions, deform_type, params):
        """在模块4区域中应用类型①的变形算法"""
        deformed_points = points.copy()
        
        for idx, module4_region in enumerate(module4_regions):
            # 添加调试：打印区域类型和顶点信息
            print(f"\n--- Applying {deform_type} to region {idx} ---")
            print(f"Region type: {module4_region.get('type')}")
            if 'vertices' in module4_region:
                print(f"Vertices count: {len(module4_region['vertices'])}")
                print(f"Vertices: {module4_region['vertices']}")
            else:
                print("No vertices in region")
            
            type1_region = self._convert_module4_region_to_type1(module4_region)
            print(f"Type1 region type: {type1_region.get('type')}")
            if 'vertices' in type1_region:
                print(f"Type1 vertices count: {len(type1_region['vertices'])}")
            
            # 计算掩码并打印点数
            points_np = np.array(deformed_points)
            region_mask = RegionDeformer._point_in_region(points_np, type1_region)
            mask_sum = np.sum(region_mask)
            print(f"Points in region: {mask_sum} out of {len(points_np)}")
            
            if mask_sum == 0:
                print("WARNING: No points in region! Deformation will have no effect.")
                continue
            
            # 应用变形
            deform_params = {"type": deform_type, **params}
            region_deformed_points = RegionDeformer.deform_region(
                deformed_points, 
                type1_region, 
                deform_params
            )
            
            # 检查变形前后是否有变化
            diff = np.linalg.norm(np.array(region_deformed_points) - points_np, axis=1)
            changed = np.sum(diff > 1e-6)
            print(f"Points changed after deformation: {changed}")
            
            deformed_points = region_deformed_points
        
        return deformed_points

    def _convert_ellipse_to_polygon(self, ellipse_region, num_points=100):
        """将椭圆（支持旋转）转换为多边形（采样点）"""
        cx, cy = ellipse_region['center']
        a = ellipse_region['semi_major']  # 半长轴
        b = ellipse_region['semi_minor']  # 半短轴
        angle = ellipse_region.get('angle', 0)  # 旋转角度（度）
        
        # 转换为弧度
        angle_rad = math.radians(angle)
        
        # 生成椭圆的采样点
        vertices = []
        for i in range(num_points):
            # 参数方程中的角度
            theta = 2 * math.pi * i / num_points
            
            # 未旋转的椭圆上的点
            x_unrotated = a * math.cos(theta)
            y_unrotated = b * math.sin(theta)
            
            # 应用旋转
            x_rotated = x_unrotated * math.cos(angle_rad) - y_unrotated * math.sin(angle_rad)
            y_rotated = x_unrotated * math.sin(angle_rad) + y_unrotated * math.cos(angle_rad)
            
            # 平移到中心点
            x = cx + x_rotated
            y = cy + y_rotated
            
            vertices.append((x, y))
        
        # 创建自定义多边形区域
        polygon_region = {
            'type': 'custom',
            'center': ellipse_region['center'],
            'vertices': vertices,
            'original_type': 'ellipse',  # 记录原始类型，便于调试
            'original_angle': angle,
            'original_semi_major': a,
            'original_semi_minor': b
        }
        
        # 保留基础尺寸参数
        if 'base_length' in ellipse_region:
            polygon_region['base_length'] = ellipse_region['base_length']
        if 'base_width' in ellipse_region:
            polygon_region['base_width'] = ellipse_region['base_width']
        
        return polygon_region
    # 添加刷新画布的方法：
    def _refresh_canvas_after_module4_change(self):
        """模块4状态变化后刷新画布显示（不重绘所有内容）"""
        # 只刷新画布，不重新绘制所有图形
        # 这样可以保留Module4绘制的参考线
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.draw_idle()
            # 保存当前坐标轴范围
            ax2 = self.canvas.axes[1]
            current_xlim = ax2.get_xlim()
            current_ylim = ax2.get_ylim()
            
            current_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
            unfolded = StentUtils.generate_unfolded_path(self.base_points, current_points, self.base_params)
            cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
            
            # 绘制结果
            self.plot_results(
                self.base_points, 
                current_points, 
                "Module4 Region Selection", 
                unfolded, 
                cylinder_3d
            )
    # 🔧 新增方法：强制重绘所有内容
    def _force_redraw_all(self):
        """强制重绘所有内容，确保变形图案和参考线都正确显示"""
        if not self.base_points:
            return
            
        # 获取当前点集
        current_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
        
        # 生成展开路径和3D投影
        unfolded = StentUtils.generate_unfolded_path(self.base_points, current_points, self.base_params)
        cylinder_3d = StentUtils.project_to_cylinder(unfolded, self.base_params)
        
        # 绘制结果
        self.plot_results(
            self.base_points, 
            current_points, 
            "Module4 Region Selection", 
            unfolded, 
            cylinder_3d
        )
    def get_current_unfolded_path(self):
        """获取当前的unfold path坐标"""
        if not self.base_points or not self.base_params:
            return None
        
        current_points = self.current_deformed_points if self.current_deformed_points is not None else self.base_points
        return StentUtils.generate_unfolded_path(self.base_points, current_points, self.base_params)

    def get_current_deformed_path_absolute(self):
        """获取当前deformed path的绝对坐标"""
        if self.current_deformed_points is not None:
            return self.current_deformed_points
        elif self.base_points:
            return self.base_points
        else:
            return None

    def get_current_deformed_path_relative(self):
        """获取当前deformed path的相对坐标（第一个点为绝对，后续为相对偏移）"""
        absolute_points = self.get_current_deformed_path_absolute()
        if not absolute_points:
            return None
        
        relative_points = [absolute_points[0]]  # 第一个点保留绝对坐标
        for i in range(1, len(absolute_points)):
            prev_x, prev_y = absolute_points[i-1]
            curr_x, curr_y = absolute_points[i]
            
            rel_x = curr_x - prev_x
            rel_y = curr_y - prev_y
            
            relative_points.append((round(rel_x, 3), round(rel_y, 3)))
        
        return relative_points

    def export_unfolded_path(self):
        """导出unfolded path为坐标文本"""
        unfolded_points = self.get_current_unfolded_path()
        if not unfolded_points:
            QMessageBox.warning(self, "Warning", "No unfolded path data to export!")
            return
        
        # 对点进行均匀采样和过滤
        resampled_points = GCodeExporter.resample_points(unfolded_points, target_step=0.2)
        filtered_points = GCodeExporter.remove_close_points(resampled_points, min_distance=0.18)
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Unfolded Path Coordinates", 
            "", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            # 确保文件扩展名为.txt
            if not filename.endswith('.txt'):
                filename += '.txt'
                
            success = GCodeExporter.export_unfolded_path_to_txt(filtered_points, filename)
            if success:
                QMessageBox.information(self, "Success", f"Unfolded path coordinates exported to {filename}")
            else:
                QMessageBox.critical(self, "Error", "Failed to export coordinates")
            self.add_log("Exported unfolded path coordinates")
    def export_deformed_absolute(self):
        """导出deformed path的绝对坐标"""
        absolute_points = self.get_current_deformed_path_absolute()
        if absolute_points is None or len(absolute_points) == 0:
            QMessageBox.warning(self, "Warning", "No deformed path data to export!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Absolute Coordinates", 
            "", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            # 确保文件扩展名为.txt
            if not filename.endswith('.txt'):
                filename += '.txt'
                
            success = GCodeExporter.export_points_to_txt(absolute_points, filename, "absolute")
            if success:
                QMessageBox.information(self, "Success", f"Absolute coordinates exported to {filename}")
                self.add_log("Exported deformed path (absolute coordinates)")  
            else:
                QMessageBox.critical(self, "Error", "Failed to export coordinates")


    def export_deformed_relative(self):
        """导出deformed path的相对坐标"""
        relative_points = self.get_current_deformed_path_relative()
        if relative_points is None or len(relative_points) == 0:  
            QMessageBox.warning(self, "Warning", "No deformed path data to export!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Relative Coordinates", 
            "", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            # 确保文件扩展名为.txt
            if not filename.endswith('.txt'):
                filename += '.txt'
                
            success = GCodeExporter.export_points_to_txt(relative_points, filename, "relative")
            if success:
                QMessageBox.information(self, "Success", f"Relative coordinates exported to {filename}")
                self.add_log("Exported deformed path (relative coordinates)")  # 添加这行
            else:
                QMessageBox.critical(self, "Error", "Failed to export coordinates")
    def resizeEvent(self, event):
        """重写窗口大小改变事件，更新撤销按钮位置"""
        super().resizeEvent(event)
        self.update_undo_button_position()

    def update_undo_button_position(self):
        """更新撤销按钮在画布内部的位置"""
        if hasattr(self, 'canvas_widget') and self.canvas_widget:
            # 获取画布容器的尺寸
            container_size = self.canvas_widget.size()
            
            # 计算按钮位置：距离右边缘15px，上边缘15px
            button_width = self.undo_btn.width()
            button_height = self.undo_btn.height()
            
            x_pos = container_size.width() - button_width - 15  # 距离右边缘15px
            y_pos = 15  # 距离上边缘15px
            
            # 设置按钮位置
            self.undo_btn.move(x_pos, y_pos)

    def open_zoom_window(self, plot_type):
        """打开放大窗口"""
        if not self.base_points:
            QMessageBox.warning(self, "Warning", "Please generate base pattern first!")
            return
            
        # 创建放大窗口
        self.zoom_window = ZoomWindow(self, plot_type)
        
        # 传递当前数据
        self.zoom_window.update_data(
            self.base_points,
            self.current_deformed_points,
            self.base_params,
            self.type1_selected_region,
            self.module4_regions_info
        )
        
        self.zoom_window.show()

    def open_zoom_window(self, plot_type):
        """打开放大窗口"""
        if not self.base_points:
            QMessageBox.warning(self, "Warning", "Please generate base pattern first!")
            return
            
        try:
            # 创建放大窗口
            self.zoom_window = ZoomWindow(self, plot_type)
            
            # 🔧 确保传递正确的数据
            self.zoom_window.update_data(
                self.base_points,
                self.current_deformed_points,
                self.base_params,
                self.type1_selected_region,
                self.module4_regions_info
            )
            
            self.zoom_window.show()
            self.add_log(f"Opened zoom view for {plot_type}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open zoom window: {str(e)}")

    def switch_to_module3(self, region_type):
        """切换到模块3，完全重置模块4"""
        print(f"切换到模块3: {region_type}")
        
        # 1. 标记当前激活模块
        self.active_module = "module3"
        
        # 2. 完全重置模块4
        self._reset_module4_completely()
        
        # 3. 重置模块4的所有交互状态
        if self.module4:
            self.module4.is_interacting = False
            self.module4.is_drawing = False
            self.module4.is_dragging = False
            self.module4.is_rotating = False
            self.module4.is_custom_selecting = False
            self.module4.selected_points = []
        
        # 4. 清除所有可能残留的图形
        self._clean_all_module4_graphics()
        
        # 5. 执行原有的进入模块3逻辑
        self._enter_module3_selection(region_type)

    def switch_to_module4(self, region_type=None, custom_mode=None):
        """切换到模块4，完全重置模块3"""
        print(f"切换到模块4: {region_type}")
        
        # 1. 标记当前激活模块
        self.active_module = "module4"
        
        # 2. 完全重置模块3
        self._reset_module3_completely()
        
        # 3. 清除所有可能残留的图形
        self._clean_all_module3_graphics()
        
        # 4. 执行原有的激活模块4逻辑
        self._enter_module4_selection(region_type, custom_mode)

    def _clean_all_module4_graphics(self):
        """完全清除模块4的所有图形元素"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
        
        ax = self.canvas.axes[1] if len(self.canvas.axes) > 1 else None
        if not ax:
            return
        
        # 清除所有可能由模块4添加的图形元素
        self._clean_module4_patches(ax)
        self._clean_module4_lines(ax)
        self._clean_module4_collections(ax)
        
        # 重绘画布
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
        
        print("✅ 已清除所有模块4图形元素")

    def _clean_module4_patches(self, ax):
        """清除模块4的所有patches"""
        patches_to_remove = []
        for patch in ax.patches[:]:
            try:
                # 根据特征识别模块4的patches
                if isinstance(patch, (patches.Circle, patches.Rectangle, patches.Ellipse, patches.Polygon)):
                    # 检查颜色特征
                    edgecolor = patch.get_edgecolor()
                    facecolor = patch.get_facecolor()
                    
                    # 绿色边框（原始区域）
                    if len(edgecolor) >= 3:
                        if edgecolor[0] < 0.1 and edgecolor[1] > 0.9 and edgecolor[2] < 0.1:
                            patches_to_remove.append(patch)
                    
                    # 橙色填充（旋转控制点）
                    if len(facecolor) >= 3:
                        if facecolor[0] > 0.9 and facecolor[1] > 0.6 and facecolor[1] < 0.7 and facecolor[2] < 0.1:
                            patches_to_remove.append(patch)
                    
                    # 虚线边框（关联区域）
                    linestyle = patch.get_linestyle()
                    if linestyle == '--':
                        patches_to_remove.append(patch)
            except Exception:
                continue
        
        for patch in patches_to_remove:
            try:
                patch.remove()
            except Exception:
                pass

    def _clean_module4_lines(self, ax):
        """清除模块4的所有lines"""
        lines_to_remove = []
        for line in ax.lines[:]:
            try:
                # 绿色预览线
                color = line.get_color()
                if color in ['green', 'g', '#00ff00', '#008000']:
                    lines_to_remove.append(line)
                
                # 虚线（预览线）
                linestyle = line.get_linestyle()
                if linestyle in ['--', ':', '-.']:
                    lines_to_remove.append(line)
            except Exception:
                continue
        
        for line in lines_to_remove:
            try:
                line.remove()
            except Exception:
                pass

    def _clean_module4_collections(self, ax):
        """清除模块4的所有collections"""
        collections_to_remove = []
        for collection in ax.collections[:]:
            try:
                # 红色控制点
                facecolors = collection.get_facecolor()
                if len(facecolors) > 0 and len(facecolors[0]) >= 3:
                    # 红色 (1, 0, 0)
                    if facecolors[0][0] > 0.9 and facecolors[0][1] < 0.1 and facecolors[0][2] < 0.1:
                        collections_to_remove.append(collection)
                    # 橙色 (1, 0.65, 0)
                    if facecolors[0][0] > 0.9 and facecolors[0][1] > 0.6 and facecolors[0][1] < 0.7 and facecolors[0][2] < 0.1:
                        collections_to_remove.append(collection)
            except Exception:
                continue
        
        for collection in collections_to_remove:
            try:
                collection.remove()
            except Exception:
                pass

    def _clean_all_module3_graphics(self):
        """完全清除模块3的所有图形元素"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
        
        ax = self.canvas.axes[1] if len(self.canvas.axes) > 1 else None
        if not ax:
            return
        
        # 清除所有红色虚线或实线图形
        self._clean_module3_patches(ax)
        self._clean_module3_lines(ax)
        self._clean_module3_collections(ax)
        
        # 重绘画布
        try:
            self.canvas.draw_idle()
        except Exception:
            pass
        
        print("✅ 已清除所有模块3图形元素")

    def _clean_module3_patches(self, ax):
        """清除模块3的所有patches"""
        patches_to_remove = []
        for patch in ax.patches[:]:
            try:
                edgecolor = patch.get_edgecolor()
                # 红色边框（模块3选区）
                if len(edgecolor) >= 3:
                    if edgecolor[0] > 0.9 and edgecolor[1] < 0.1 and edgecolor[2] < 0.1:
                        patches_to_remove.append(patch)
            except Exception:
                continue
        
        for patch in patches_to_remove:
            try:
                patch.remove()
            except Exception:
                pass

    def _clean_module3_lines(self, ax):
        """清除模块3的所有lines"""
        lines_to_remove = []
        for line in ax.lines[:]:
            try:
                # 红色线条（预览线或最终边界）
                color = line.get_color()
                if color in ['red', 'r', '#ff0000', '#ff3300']:
                    lines_to_remove.append(line)
            except Exception:
                continue
        
        for line in lines_to_remove:
            try:
                line.remove()
            except Exception:
                pass

    def _clean_module3_collections(self, ax):
        """清除模块3的所有collections"""
        collections_to_remove = []
        for collection in ax.collections[:]:
            try:
                # 红色散点（控制点）
                facecolors = collection.get_facecolor()
                if len(facecolors) > 0 and len(facecolors[0]) >= 3:
                    if facecolors[0][0] > 0.9 and facecolors[0][1] < 0.1 and facecolors[0][2] < 0.1:
                        collections_to_remove.append(collection)
            except Exception:
                continue
        
        for collection in collections_to_remove:
            try:
                collection.remove()
            except Exception:
                pass

    def _reset_module3_completely(self):
        """完全重置模块3的所有状态"""
        # 重置状态变量
        self.type1_selected_region = None
        self.is_type1_selecting = False
        self.current_region_type = None
        
        # 重置画布交互
        if hasattr(self, 'type1_canvas_interaction'):
            self.type1_canvas_interaction.clear_selection()
        
        # 重置按钮状态
        if hasattr(self, 'type1_widget'):
            self.type1_widget.disable_confirm_btn(True)
            self.type1_widget.update_status("Module3 reset")

    def update_module4_custom_mode_visibility(self, checked):
        """更新Module4自定义模式选择的可见性"""
        self.module4_custom_mode_widget.setVisible(checked)
# ------------------- 程序入口 -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())