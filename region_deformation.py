import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QMenu, QAction, QComboBox, QWidget)
from PyQt5.QtCore import Qt
# 添加组合数计算函数
try:
    from math import comb
except ImportError:
    # 对于Python < 3.8，自己实现comb函数
    from math import factorial
    def comb(n, k):
        return factorial(n) // (factorial(k) * factorial(n - k))

class Type1DeformParamDialog(QDialog):
    """类型①区域变形的参数对话框（扩展支持 Polar Wave）"""
    def __init__(self, deform_type, parent=None):
        super().__init__(parent)
        self.deform_type = deform_type
        self.setWindowTitle(f"Deformation Parameters - {deform_type}")
        self.init_ui()
    def _toggle_late_steep_params(self, index):
        """根据选择的过渡类型显示/隐藏 Late Steep 参数"""
        is_late_steep = (self.transition_type_combo.currentText() == "Late Steep")
        self.late_steep_widget.setVisible(is_late_steep)
    def init_ui(self):
        layout = QFormLayout(self)
        
        if self.deform_type == "Scaling":
            self.factor_input = QLineEdit("1.2")
            self.transition_input = QLineEdit("0.0")
                # ----- 新增：过渡类型选择 -----
            self.transition_type_combo = QComboBox()
            self.transition_type_combo.addItems(["Default (1 - t^2.5)^2", "Cosine", "Late Steep"])
            self.transition_type_combo.currentIndexChanged.connect(self._toggle_late_steep_params)
            
            # 新增：Late Steep 参数容器（初始隐藏）
            self.late_steep_widget = QWidget()
            self.late_steep_layout = QFormLayout(self.late_steep_widget)
            self.k_input = QLineEdit("0.5")
            self.n_input = QLineEdit("2")
            self.late_steep_layout.addRow("k (cutoff):", self.k_input)
            self.late_steep_layout.addRow("n (steepness):", self.n_input)
            
            # 将控件添加到表单布局
            layout.addRow("Scaling Factor:", self.factor_input)
            layout.addRow("Transition Width (mm):", self.transition_input)
            layout.addRow("Transition Type:", self.transition_type_combo)
            layout.addRow(self.late_steep_widget)   # 占位，但会通过隐藏控制
            
            # 初始隐藏 Late Steep 参数区域
            self.late_steep_widget.setVisible(False)
        elif self.deform_type == "Sine":
            self.amplitude_input = QLineEdit("0.6")
            self.frequency_input = QLineEdit("0.2")
            self.transition_ratio_input = QLineEdit("0.2")
            layout.addRow("Amplitude (mm):", self.amplitude_input)
            layout.addRow("Frequency (1/mm):", self.frequency_input)
            layout.addRow("Transition Ratio (0~1):", self.transition_ratio_input)
        elif self.deform_type == "Twist":
            self.strength_input = QLineEdit("0.35")
            self.transition_input = QLineEdit("0.0")
            layout.addRow("Twist Strength:", self.strength_input)
            layout.addRow("Transition Width (mm):", self.transition_input)
        # 🔴 新增：Polar Wave 参数
        elif self.deform_type == "Polar Wave":
            self.A_input = QLineEdit("0.1")
            self.B_input = QLineEdit("0.08")
            self.C_input = QLineEdit("2.0")
            layout.addRow("Fluctuation Amplitude (A):", self.A_input)
            layout.addRow("Attenuation Coefficient (B):", self.B_input)
            layout.addRow("Fluctuation Frequency (C):", self.C_input)
        # 在 deform_type 的判断中添加
        elif self.deform_type == "Rectangular Scaling":
            self.scale_x_input = QLineEdit("0.7")
            self.scale_y_input = QLineEdit("1.0")
            self.core_ratio_input = QLineEdit("0.8")  # 核心区占外框的比例
            layout.addRow("Scale Factor X:", self.scale_x_input)
            layout.addRow("Scale Factor Y:", self.scale_y_input)
            layout.addRow("Core Ratio (0~1):", self.core_ratio_input)

        self.ok_btn = QPushButton("Apply")
        self.ok_btn.clicked.connect(self.accept)
        layout.addRow(self.ok_btn)
        
    def get_params(self):
        try:
            params = {}
            
            if self.deform_type == "Scaling":
                params["Factor"] = float(self.factor_input.text())
                params["Transition Width (mm)"] = float(self.transition_input.text())
                # 新增过渡类型及参数
                transition_type = self.transition_type_combo.currentText()
                params["Transition Type"] = transition_type
                if transition_type == "Late Steep":
                    params["k"] = float(self.k_input.text())
                    params["n"] = float(self.n_input.text())
            elif self.deform_type == "Sine":
                amplitude = float(self.amplitude_input.text())
                frequency = float(self.frequency_input.text())
                transition_ratio = float(self.transition_ratio_input.text())
                if amplitude < 0:
                    raise ValueError("Amplitude cannot be negative")
                if frequency < 0:
                    raise ValueError("Frequency cannot be negative")
                if not (0 <= transition_ratio <= 1):
                    raise ValueError("Transition Ratio must be between 0 and 1")
                params["Amplitude"] = amplitude
                params["Frequency"] = frequency
                params["Transition Ratio"] = transition_ratio
            elif self.deform_type == "Twist":
                strength = float(self.strength_input.text())
                if strength <= 0:
                    raise ValueError("Twist Strength must be greater than 0")
                params["Strength"] = strength
                params["Transition Width (mm)"] = float(self.transition_input.text())
            # 🔴 新增：Polar Wave 参数获取
            elif self.deform_type == "Polar Wave":
                A = float(self.A_input.text())
                B = float(self.B_input.text())
                C = float(self.C_input.text())
                params["A"] = A
                params["B"] = B
                params["C"] = C
            elif self.deform_type == "Rectangular Scaling":
                params = {
                    "scale_x": float(self.scale_x_input.text()),
                    "scale_y": float(self.scale_y_input.text()),
                    "core_ratio": float(self.core_ratio_input.text())
                }
            return params
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid parameter: {str(e)}")
            return None

class CustomShapeMenu(QMenu):
    """自定义形状的子模式菜单（未修改，保持原有逻辑）"""
    def __init__(self, parent, canvas_interaction):
        super().__init__("Custom Shape Mode", parent)
        self.canvas_interaction = canvas_interaction
        
        self.line_action = QAction("Line", self)
        self.curve_action = QAction("Curve", self)

        
        self.line_action.triggered.connect(self.set_line_mode)
        self.curve_action.triggered.connect(self.set_curve_mode)

        
        self.addAction(self.line_action)
        self.addAction(self.curve_action)

        
    def set_line_mode(self):
        self.canvas_interaction.custom_mode = "line"
        if hasattr(self.canvas_interaction.main_window, 'type1_widget'):
            self.canvas_interaction.main_window.type1_widget.update_status(
                "Custom (Line) mode: Click to add points, double-click to close"
            )
        
    def set_curve_mode(self):
        self.canvas_interaction.custom_mode = "curve"
        # 同时更新主窗口的状态提示
        if hasattr(self.canvas_interaction.main_window, 'type1_widget'):
            self.canvas_interaction.main_window.type1_widget.update_status(
                "Custom (Curve) mode: Click to add control points, double-click to close"
            )
        

class Type1CanvasInteraction:
    """类型①：画布交互工具（修复双击闭合问题）"""
    def __init__(self, ax, main_window):
        self.ax = ax  # 关联的matplotlib坐标轴
        self.main_window = main_window  # 主窗口引用
        self.is_selecting = False       # 是否处于选择状态
        self.region_type = None         # 区域类型（circle/square/ellipse/triangle/custom）
        self.selected_points = []       # 已选择的点集（用于三角形/自定义）
        self.selected_region = None     # 最终确定的区域参数
        self.temp_patch = None          # 临时预览的图形
        self.preview_line = None        # 临时预览线（用于顶点连线）
        self.custom_mode = "line"       # 自定义形状模式（line/curve），默认line模式

    def _catmull_rom_spline(self, points, num_points_per_segment=20):
        """生成Catmull-Rom样条曲线，确保经过每一个控制点"""
        if len(points) < 2:
            return points
        
        # 如果只有2个点，直接返回直线
        if len(points) == 2:
            return points
        
        curve = []
        
        # 添加第一个点
        curve.append(points[0])
        
        for i in range(len(points) - 1):
            # 获取当前段的前后控制点
            p0 = points[max(i - 1, 0)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(i + 2, len(points) - 1)]
            
            # 生成当前段的曲线点
            for t in np.linspace(0, 1, num_points_per_segment):
                if t == 0:
                    continue  # 避免重复点
                
                # Catmull-Rom样条公式
                t2 = t * t
                t3 = t2 * t
                
                x = 0.5 * ((2 * p1[0]) +
                        (-p0[0] + p2[0]) * t +
                        (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                        (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
                
                y = 0.5 * ((2 * p1[1]) +
                        (-p0[1] + p2[1]) * t +
                        (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                        (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
                
                curve.append((x, y))
        
        # 添加最后一个点
        curve.append(points[-1])
        
        return curve
    
    def _update_curve_preview(self, current_point=None):
        """更新曲线预览 - 增强版本"""
        if len(self.selected_points) < 1:
            return
            
        # 生成曲线
        if current_point and len(self.selected_points) >= 1:
            # 预览时包含当前鼠标位置
            preview_points = self.selected_points + [current_point]
        else:
            # 最终绘制时只用已选点
            preview_points = self.selected_points
            
        if len(preview_points) >= 2:
            curve_points = self._catmull_rom_spline(preview_points)
            
            # 绘制曲线
            if self.preview_line:
                self.preview_line.remove()
                
            x_curve, y_curve = zip(*curve_points)
            self.preview_line = self.ax.plot(x_curve, y_curve, 'r-', linewidth=2, alpha=0.8)[0]
            
            # 清除多余的散点
            self._clear_excess_dots()
            
            # 重新绘制已确定的控制点
            if len(self.selected_points) > 0:
                self.ax.scatter([p[0] for p in self.selected_points], 
                            [p[1] for p in self.selected_points], 
                            c='red', s=50, zorder=5, alpha=0.6)
            
            self.ax.figure.canvas.draw_idle()
    def _clear_excess_dots(self):
        """只清除多余的散点，保留预览线和其他必要元素"""
        # 获取当前所有散点图
        collections_to_remove = []
        for collection in self.ax.collections:
            # 检查是否是红色控制点
            if (hasattr(collection, '_facecolors') and 
                len(collection._facecolors) > 0 and
                np.allclose(collection._facecolors[0], [1., 0., 0., 1.]) and
                collection.get_sizes()[0] >= 30):  # 控制点大小
                collections_to_remove.append(collection)
        
        # 移除临时控制点
        for collection in collections_to_remove:
            collection.remove()

    def start_selection(self, region_type, mode=None):
        """开始区域选择，支持可选的模式参数"""
        self.is_selecting = True
        self.region_type = region_type
        self.selected_points = []
        self.selected_region = None
        self.clear_temp_graphics()
        
        # 对于自定义形状，设置模式
        if region_type == "custom":
            if mode is not None:
                self.custom_mode = mode
            # 确保custom_mode有默认值
            elif not self.custom_mode:
                self.custom_mode = "line"  # 默认使用line模式

    def clear_temp_graphics(self):
        """清除临时图形元素，但保留已确定的控制点"""
        # 清除临时图形
        if self.temp_patch:
            try:
                self.temp_patch.remove()
            except:
                pass
            self.temp_patch = None
            
        # 清除预览线
        if self.preview_line:
            try:
                self.preview_line.remove()
            except:
                pass
            self.preview_line = None
            
        # 清除其他临时散点（不是已确定的控制点）
        collections_to_remove = []
        for collection in self.ax.collections:
            # 保留已确定的控制点（大小>=30且红色）
            if (hasattr(collection, '_sizes') and 
                len(collection._sizes) > 0 and
                collection._sizes[0] >= 30 and
                hasattr(collection, '_facecolors') and
                len(collection._facecolors) > 0 and
                np.allclose(collection._facecolors[0], [1., 0., 0., 1.])):
                continue  # 跳过已确定的控制点
            else:
                collections_to_remove.append(collection)
        
        for collection in collections_to_remove:
            try:
                collection.remove()
            except:
                pass
                
        # 清除所有临时线条（包括虚线）
        lines_to_remove = []
        for line in self.ax.lines:
            # 检查是否是虚线（临时线）
            if (hasattr(line, 'get_linestyle') and 
                line.get_linestyle() in ['--', ':', '-.']):
                lines_to_remove.append(line)
        
        for line in lines_to_remove:
            try:
                line.remove()
            except:
                pass
        
        self.ax.figure.canvas.draw_idle()



    def update_preview(self, event):
        """更新预览 - 修复曲线模式"""
        if len(self.selected_points) == 0 or event.xdata is None or event.ydata is None:
            return
            
        # 曲线模式：使用Catmull-Rom样条曲线预览
        if self.region_type == "custom" and self.custom_mode == "curve":
            current_point = (event.xdata, event.ydata)
            self._update_curve_preview(current_point)
        else:
            # 其他模式保持原有逻辑
            if self.preview_line:
                self.preview_line.remove()
            x = [self.selected_points[-1][0], event.xdata]
            y = [self.selected_points[-1][1], event.ydata]
            self.preview_line = self.ax.plot(x, y, 'r--', linewidth=1, alpha=0.7)[0]
            self.ax.figure.canvas.draw_idle()

    def on_mouse_press(self, event):
        """鼠标按下事件 - 修复曲线模式"""
        if event.button != 1:
            return
        if event.xdata is not None and event.ydata is not None:
            self.selected_points.append((event.xdata, event.ydata))
            
            # 立即显示点击的点
            if self.region_type == "custom":
                # 对于Custom类型，传递当前选择的模式
                if self.custom_mode == "curve":
                    self._update_curve_preview()
                else:
                    self.ax.scatter(event.xdata, event.ydata, c='red', s=30, zorder=5)
                self.ax.figure.canvas.draw_idle()
            elif self.region_type == "triangle":
                # 三角形也显示点击的点
                self.ax.scatter(event.xdata, event.ydata, c='red', s=30, zorder=5)
                self.ax.figure.canvas.draw_idle()
            
            

    def on_mouse_move(self, event):
        """鼠标移动事件 - 为所有形状添加预览，修复椭圆选区"""
        if not self.is_selecting or not self.selected_points:
            return
            
        # 基础形状的预览（圆形、正方形、椭圆）
        if self.region_type in ["circle", "square", "ellipse"] and len(self.selected_points) == 1:
            start_x, start_y = self.selected_points[0]
            current_x, current_y = event.xdata, event.ydata
            if current_x is None or current_y is None:
                return
                
            # 清除之前的预览图形
            if self.temp_patch:
                self.temp_patch.remove()
                self.temp_patch = None
                
            if self.region_type == "circle":
                radius = np.hypot(current_x - start_x, current_y - start_y)
                self.temp_patch = patches.Circle(
                    (start_x, start_y), radius,
                    fill=False, edgecolor='red', linestyle='--', linewidth=2
                )
                self.selected_region = {
                    'type': 'circle', 'center': (start_x, start_y), 'radius': radius,
                    'transition_width': 1.0
                }
                
                # 添加基础尺寸参数
                if hasattr(self.main_window, 'base_params') and self.main_window.base_params:
                    self.selected_region['base_length'] = self.main_window.base_params['length']
                    self.selected_region['base_width'] = self.main_window.base_params['width']
                    
            elif self.region_type == "square":
                min_x, max_x = min(start_x, current_x), max(start_x, current_x)
                min_y, max_y = min(start_y, current_y), max(start_y, current_y)
                side_length = max(max_x - min_x, max_y - min_y)
                center_x, center_y = (min_x + max_x)/2, (min_y + max_y)/2
                self.temp_patch = patches.Rectangle(
                    (center_x - side_length/2, center_y - side_length/2),
                    side_length, side_length,
                    fill=False, edgecolor='red', linestyle='--', linewidth=2
                )
                self.selected_region = {
                    'type': 'square', 'center': (center_x, center_y), 'side_length': side_length,
                    'width': side_length, 'height': side_length,   # 新增
                    'transition_width': 1.0
                }
                
                # 添加基础尺寸参数
                if hasattr(self.main_window, 'base_params') and self.main_window.base_params:
                    self.selected_region['base_length'] = self.main_window.base_params['length']
                    self.selected_region['base_width'] = self.main_window.base_params['width']
                    
            elif self.region_type == "ellipse":
                semi_major = abs(current_x - start_x)
                semi_minor = abs(current_y - start_y)
                self.temp_patch = patches.Ellipse(
                    (start_x, start_y), 2*semi_major, 2*semi_minor,
                    fill=False, edgecolor='red', linestyle='--', linewidth=2
                )
                self.selected_region = {
                    'type': 'ellipse', 'center': (start_x, start_y),
                    'semi_major': semi_major, 'semi_minor': semi_minor,
                    'transition_width': 1.0
                }
                
                # 添加基础尺寸参数
                if hasattr(self.main_window, 'base_params') and self.main_window.base_params:
                    self.selected_region['base_length'] = self.main_window.base_params['length']
                    self.selected_region['base_width'] = self.main_window.base_params['width']
            
            # 添加临时预览图形到坐标轴
            if self.temp_patch:
                self.ax.add_patch(self.temp_patch)
                self.ax.figure.canvas.draw_idle()
                
            return
            
        # 三角形和自定义形状的预览
        if self.region_type in ["triangle", "custom"] and len(self.selected_points) > 0:
            if event.xdata is None or event.ydata is None:
                return
                
            # 清除之前的预览线
            if self.preview_line:
                self.preview_line.remove()
                self.preview_line = None
                
            # 对于曲线模式的自定义形状，使用特殊的预览
            if self.region_type == "custom" and self.custom_mode == "curve":
                # 生成包含当前鼠标位置的曲线预览
                current_point = (event.xdata, event.ydata)
                preview_points = self.selected_points + [current_point]
                
                if len(preview_points) >= 2:
                    # 生成Catmull-Rom样条曲线
                    curve_points = self._catmull_rom_spline(preview_points)
                    
                    # 绘制曲线
                    if self.preview_line:
                        self.preview_line.remove()
                        
                    x_curve, y_curve = zip(*curve_points)
                    self.preview_line = self.ax.plot(x_curve, y_curve, 'r-', linewidth=2, alpha=0.8)[0]
                    
                    # 清除多余的散点，只保留已确定的控制点
                    self._clear_excess_dots()
                    
                    # 重新绘制已确定的控制点
                    if len(self.selected_points) > 0:
                        self.ax.scatter([p[0] for p in self.selected_points], 
                                    [p[1] for p in self.selected_points], 
                                    c='red', s=50, zorder=5, alpha=0.6)
                    
                    self.ax.figure.canvas.draw_idle()
                    return
            
            # 对于直线模式的三角形和自定义形状，绘制直线连接预览
            # 绘制已有点之间的连接线
            if len(self.selected_points) > 1:
                for i in range(len(self.selected_points)-1):
                    x = [self.selected_points[i][0], self.selected_points[i+1][0]]
                    y = [self.selected_points[i][1], self.selected_points[i+1][1]]
                    self.ax.plot(x, y, 'r--', linewidth=1, alpha=0.7)
            
            # 从最后一个点到当前鼠标位置的预览线
            last_point = self.selected_points[-1]
            current_point = (event.xdata, event.ydata)
            x = [last_point[0], current_point[0]]
            y = [last_point[1], current_point[1]]
            
            self.preview_line = self.ax.plot(x, y, 'r--', linewidth=1, alpha=0.7)[0]
            self.ax.figure.canvas.draw_idle()

    def on_mouse_release(self, event):
        """鼠标释放事件 - 适配区域闭合"""
        if event.inaxes == self.ax and self.is_selecting:
            # 基础形状（圆形、正方形、椭圆）在鼠标释放时完成选择
            if self.region_type in ["circle", "square", "ellipse"] and self.selected_region:
                self.finalize_selection()
                return True
                

    def _on_double_click(self, event):
        """双击事件 - 修复三角形和自定义选区"""
        if event.button != 1 or not event.dblclick:
            return
        
        # 🔴 修复：检查region_type是否为None
        if not self.region_type:
            return
        
        # 🔴 修复：同时处理三角形和自定义选区
        if self.is_selecting and self.region_type in ["triangle", "custom"]:
            if len(self.selected_points) >= 3:
                # 在直线模式下，连接最后一个点和第一个点
                if self.region_type == "triangle" or (self.region_type == "custom" and self.custom_mode == "line"):
                    first_point = self.selected_points[0]
                    last_point = self.selected_points[-1]
                    if (abs(first_point[0] - last_point[0]) > 0.1 or 
                        abs(first_point[1] - last_point[1]) > 0.1):
                        close_x = [last_point[0], first_point[0]]
                        close_y = [last_point[1], first_point[1]]
                        close_line = self.ax.plot(close_x, close_y, 'r--', linewidth=2, alpha=0.8)[0]
                        self.ax.figure.canvas.draw_idle()
                
                # 完成选区
                self.finalize_selection()
                
                # 🔴 修复：检查是否成功完成了选区
                if not self.selected_region:
                    return
                    
                # 更新状态
                if hasattr(self.main_window, 'type1_widget'):
                    self.main_window.type1_widget.disable_confirm_btn(False)
                    # 🔴 修复：再次检查region_type
                    if self.region_type:
                        self.main_window.type1_widget.update_status(f"Selected {self.region_type.capitalize()} region")
                    else:
                        self.main_window.type1_widget.update_status("Selection failed")
                
                # 🔴 关键：确保主窗口的selected_region被更新
                if self.main_window and self.selected_region:
                    self.main_window.type1_selected_region = self.selected_region
                    self.main_window.update_buttons_state()
            else:
                QMessageBox.warning(
                    self.main_window,
                    "Invalid Selection",
                    f"Need at least 3 points for {self.region_type.capitalize()}"
                )
    def finalize_selection(self):
        """完成选择 - 确保所有选区都有正确参数，支持所有形状"""
        print(f"DEBUG: finalize_selection called, region_type={self.region_type}")
        
        # 先检查是否真的有选择
        if not self.selected_points and self.region_type in ["triangle", "custom"]:
            print(f"DEBUG: No points selected for {self.region_type}")
            self.clear_temp_graphics()
            self.is_selecting = False
            return
        
        # 验证区域
        if not self.is_valid_region():
            print(f"DEBUG: Region validation failed for {self.region_type}")
            QMessageBox.warning(
                self.main_window,
                "Invalid Selection",
                f"{self.region_type.capitalize()} selection failed. Please try again."
            )
            self.clear_selection()
            return
        """完成选择 - 确保所有选区都有正确参数，支持所有形状"""
        if not self.is_valid_region():
            self.clear_temp_graphics()
            self.is_selecting = False
            return
            
        # 🔴 处理不同类型的选区
        if self.region_type == "triangle":
            # 确保有3个点
            if len(self.selected_points) == 3:
                vertices = self.selected_points
                center_x = sum(p[0] for p in vertices) / len(vertices)
                center_y = sum(p[1] for p in vertices) / len(vertices)
                
                self.selected_region = {
                    'type': 'triangle',
                    'vertices': vertices,
                    'center': (center_x, center_y),
                    'transition_width': 1.0
                }
                
                # 添加基础尺寸参数
                if hasattr(self.main_window, 'base_params') and self.main_window.base_params:
                    self.selected_region['base_length'] = self.main_window.base_params['length']
                    self.selected_region['base_width'] = self.main_window.base_params['width']
        
        elif self.region_type == "custom":
            vertices = self.selected_points
            
            if self.custom_mode == "curve" and len(vertices) >= 2:
                # 曲线模式：生成最终的曲线点作为顶点
                curve_points = self._catmull_rom_spline(vertices)
                
                # 确保曲线闭合
                if len(curve_points) >= 2 and len(vertices) >= 3:
                    closing_points = self._catmull_rom_spline([vertices[-1], vertices[0]], num_points_per_segment=10)
                    curve_points.extend(closing_points[1:])
                
                vertices = curve_points
            
            center_x = sum(p[0] for p in vertices) / len(vertices)
            center_y = sum(p[1] for p in vertices) / len(vertices)
            
            self.selected_region = {
                'type': 'custom',
                'vertices': vertices,
                'center': (center_x, center_y),
                'transition_width': 1.0
            }
            
            # 添加基础尺寸参数
            if hasattr(self.main_window, 'base_params') and self.main_window.base_params:
                self.selected_region['base_length'] = self.main_window.base_params['length']
                self.selected_region['base_width'] = self.main_window.base_params['width']
        
        # 🔴 对于基础形状（圆形、正方形、椭圆），selected_region已经在on_mouse_move中设置好了
        
        # 绘制最终的选区边界（红色实线）
        self.draw_final_region()
        
        # 更新状态
        self.is_selecting = False
        self.ax.figure.canvas.draw_idle()
        
        # 🔴 关键：通知主窗口选区已完成
        if self.main_window and hasattr(self.main_window, 'update_buttons_state'):
            # 确保选区传递给主窗口
            self.main_window.type1_selected_region = self.selected_region
            
            # 更新类型①控件的状态
            if hasattr(self.main_window, 'type1_widget'):
                self.main_window.type1_widget.disable_confirm_btn(False)
                self.main_window.type1_widget.update_status(f"Selected {self.region_type.capitalize()} region")
            
            # 更新所有按钮状态
            self.main_window.update_buttons_state()
        
    def is_valid_region(self):
        if self.region_type == "circle":
            return self.selected_region['radius'] > 1
        elif self.region_type == "square":
            return self.selected_region['side_length'] > 1
        elif self.region_type == "ellipse":
            return self.selected_region['semi_major'] > 0.5 and self.selected_region['semi_minor'] > 0.5
        elif self.region_type == "triangle":
            print(f"DEBUG triangle validation: points={len(self.selected_points)}, needs 3")
            return len(self.selected_points) == 3
        elif self.region_type == "custom":
            print(f"DEBUG custom validation: {len(self.selected_points)} points")
            return len(self.selected_points) >= 3
        return False

    def draw_final_region(self):
        """绘制最终选区 - 支持所有形状"""
        # 清除临时图形，包括预览线
        self.clear_temp_graphics()
        
        if not self.selected_region:
            return
            
        region_type = self.selected_region.get('type', '').lower()
        
        # 绘制圆形选区
        if region_type == 'circle':
            center = self.selected_region['center']
            radius = self.selected_region['radius']
            self.temp_patch = patches.Circle(
                center, radius,
                fill=False, edgecolor='red', linewidth=2
            )
            self.ax.add_patch(self.temp_patch)
            
        # 绘制正方形选区
        elif region_type == 'square':
            center = self.selected_region['center']
            side_length = self.selected_region['side_length']
            half_side = side_length / 2
            self.temp_patch = patches.Rectangle(
                (center[0] - half_side, center[1] - half_side),
                side_length, side_length,
                fill=False, edgecolor='red', linewidth=2
            )
            self.ax.add_patch(self.temp_patch)
            
        # 绘制椭圆选区
        elif region_type == 'ellipse':
            center = self.selected_region['center']
            semi_major = self.selected_region.get('semi_major', 0)
            semi_minor = self.selected_region.get('semi_minor', 0)
            if semi_major > 0 and semi_minor > 0:
                self.temp_patch = patches.Ellipse(
                    center, 2*semi_major, 2*semi_minor,
                    fill=False, edgecolor='red', linewidth=2
                )
                self.ax.add_patch(self.temp_patch)
                
        # 🔴 修复：绘制三角形选区
        elif region_type == 'triangle':
            vertices = self.selected_region.get('vertices', [])
            if len(vertices) == 3:
                # 闭合三角形：添加第一个点到最后
                closed_vertices = vertices + [vertices[0]]
                x, y = zip(*closed_vertices)
                
                # 🔴 使用红色实线绘制
                self.temp_patch = self.ax.plot(x, y, 'r-', linewidth=2)[0]
                
                # 显示顶点
                self.ax.scatter([p[0] for p in vertices], 
                            [p[1] for p in vertices], 
                            c='red', s=40, zorder=5, alpha=0.8)
                
        # 🔴 修复：绘制自定义选区
        elif region_type == 'custom':
            vertices = self.selected_region.get('vertices', [])
            if len(vertices) >= 3:
                # 对于曲线模式的自定义形状，使用曲线
                if self.custom_mode == "curve" and len(vertices) > 10:  # 曲线模式下顶点较多
                    x, y = zip(*vertices)
                    self.temp_patch = self.ax.plot(x, y, 'r-', linewidth=2)[0]
                else:
                    # 直线模式：闭合多边形
                    closed_vertices = vertices + [vertices[0]]
                    x, y = zip(*closed_vertices)
                    self.temp_patch = self.ax.plot(x, y, 'r-', linewidth=2)[0]
                
                # 显示控制点（如果点不是太多）
                if len(vertices) < 20:
                    self.ax.scatter([p[0] for p in self.selected_points], 
                                [p[1] for p in self.selected_points], 
                                c='red', s=30, zorder=5, alpha=0.6)
        
        self.ax.figure.canvas.draw_idle()
    def clear_selection(self):
        """清除当前选择的状态"""
        self.is_selecting = False
        self.selected_points = []
        self.selected_region = None
        self.region_type = None
        self.custom_mode = None
        
        # 清除所有临时图形，包括预览线
        self.clear_temp_graphics()
            
        # 清除所有散点（包括已确定的控制点）
        if hasattr(self, 'ax') and self.ax:
            collections_to_remove = []
            for collection in self.ax.collections:
                try:
                    # 清除所有红色散点（控制点）
                    facecolors = collection.get_facecolor()
                    if len(facecolors) > 0 and len(facecolors[0]) >= 3:
                        if facecolors[0][0] > 0.9 and facecolors[0][1] < 0.1 and facecolors[0][2] < 0.1:
                            collections_to_remove.append(collection)
                except:
                    pass
            
            for collection in collections_to_remove:
                try:
                    collection.remove()
                except:
                    pass
            
            # 清除所有红色线条
            lines_to_remove = []
            for line in self.ax.lines:
                try:
                    color = line.get_color()
                    if color in ['red', 'r', '#ff0000']:
                        lines_to_remove.append(line)
                except:
                    pass
            
            for line in lines_to_remove:
                try:
                    line.remove()
                except:
                    pass
            
            # 清除所有红色边框的patches
            patches_to_remove = []
            for patch in self.ax.patches:
                try:
                    edgecolor = patch.get_edgecolor()
                    if len(edgecolor) >= 3:
                        if edgecolor[0] > 0.9 and edgecolor[1] < 0.1 and edgecolor[2] < 0.1:
                            patches_to_remove.append(patch)
                except:
                    pass
            
            for patch in patches_to_remove:
                try:
                    patch.remove()
                except:
                    pass
        
        # 重绘画布
        if hasattr(self, 'ax') and hasattr(self.ax, 'figure'):
            self.ax.figure.canvas.draw_idle()
        
    def update_status(self, message):
        if hasattr(self.main_window, 'type1_widget'):
            self.main_window.type1_widget.update_status(message)

class RegionDeformer:
    """区域变形工具类（修复自定义区域的正弦变形问题）"""
    # -------------------------- 新增：Twist变形所需辅助方法 --------------------------
    @staticmethod
    def _point_to_segment_distance(px, py, x1, y1, x2, y2):
        """计算点到线段的最短距离（适配所有多边形/三角形）"""
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return np.hypot(px - x1, py - y1)
        # 投影参数t（限制在0~1，确保投影在线段上）
        t = ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy** 2)
        t = max(0.0, min(1.0, t))
        # 计算投影点坐标
        projx = x1 + t * dx
        projy = y1 + t * dy
        return np.hypot(px - projx, py - projy)

    @staticmethod
    def _polygon_max_incircle_radius(vertices, center):
        """计算多边形的"最大内接圆半径"（用于归一化距离）"""
        cx, cy = center
        max_r = 0.0
        n = len(vertices)
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i+1) % n]
            # 中心到每条边的距离
            d = RegionDeformer._point_to_segment_distance(cx, cy, x1, y1, x2, y2)
            if d > max_r:
                max_r = d
        # 边界情况：若max_r过小，用多边形的最小边长一半替代
        if max_r <= 1e-6:
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            max_r = 0.5 * min(max(xs)-min(xs), max(ys)-min(ys))
        return max_r

    @staticmethod
    def _shape_distance_ratio(x, y, region):
        """计算点在区域内的归一化距离t（t≤1：区域内，t>1：区域外）"""
        cx, cy = region["center"]
        dx, dy = x - cx, y - cy
        typ = region["type"].lower()

        # 圆形：t = 点到中心距离 / 半径
        if typ == "circle":
            r = region["radius"]
            if r == 0:
                return 1.1
            return np.hypot(dx, dy) / r

        # 正方形：需要检查参数名
        # 正方形
        if typ == "square":
            # 优先使用顶点（旋转矩形）
            if "vertices" in region:
                verts = region["vertices"]
                path = Path(verts)
                pt = np.array([x, y])
                inside = path.contains_point(pt)
                if not inside:
                    return 1.1
                # 计算点到区域中心的最大距离（归一化用）
                max_dist = 0.0
                for vx, vy in verts:
                    dist = np.hypot(vx - cx, vy - cy)
                    if dist > max_dist:
                        max_dist = dist
                if max_dist <= 1e-6:
                    return 1.1
                current_dist = np.hypot(dx, dy)
                return current_dist / max_dist
            else:
                # 兼容旧数据：轴对齐
                side_length = region.get("side_length")
                if side_length is None:
                    if "size" in region:
                        side_length = region["size"]
                    else:
                        return 1.1
                half_side = side_length / 2.0
                nx = abs(dx) / half_side if half_side > 0 else 1.1
                ny = abs(dy) / half_side if half_side > 0 else 1.1
                return max(nx, ny)
        # 在 _shape_distance_ratio 中，在 square 分支之后添加：
        elif typ == "rectangle":
            if "vertices" in region:
                verts = region["vertices"]
                path = Path(verts)
                pt = np.array([x, y])
                inside = path.contains_point(pt)
                if not inside:
                    return 1.1
                # 计算点到区域中心的最大距离
                max_dist = 0.0
                for vx, vy in verts:
                    dist = np.hypot(vx - cx, vy - cy)
                    if dist > max_dist:
                        max_dist = dist
                if max_dist <= 1e-6:
                    return 1.1
                current_dist = np.hypot(dx, dy)
                return current_dist / max_dist
            else:
                # 轴对齐矩形
                width = region.get("width", 0)
                height = region.get("height", 0)
                half_w = width / 2
                half_h = height / 2
                nx = abs(dx) / half_w if half_w > 0 else 1.1
                ny = abs(dy) / half_h if half_h > 0 else 1.1
                return max(nx, ny)
        # 椭圆：t = 点到中心的归一化椭圆距离
        if typ == "ellipse":
            # 检查参数名
            semi_major = region.get("semi_major")
            semi_minor = region.get("semi_minor")
            
            if not semi_major or not semi_minor:
                # 尝试其他参数名
                if "major_axis" in region and "minor_axis" in region:
                    semi_major = region["major_axis"] / 2.0
                    semi_minor = region["minor_axis"] / 2.0
                else:
                    return 1.1
            
            return np.sqrt((dx / semi_major) ** 2 + (dy / semi_minor) ** 2)

        # 三角形/自定义多边形
        if typ in ["triangle", "custom"]:
            verts = region["vertices"]
            path = Path(verts)
            pt = np.array([x, y])
            inside = path.contains_point(pt)
            
            if not inside:
                return 1.1
                
            # 计算点到区域中心的最大距离（归一化用）
            max_dist = 0.0
            for vx, vy in verts:
                dist = np.hypot(vx - cx, vy - cy)
                if dist > max_dist:
                    max_dist = dist
            
            if max_dist <= 1e-6:
                return 1.1
                
            # 计算当前点到中心的距离
            current_dist = np.hypot(dx, dy)
            return current_dist / max_dist

        return 1.1  # 未知类型，返回区域外

    @staticmethod
    def _apply_rectangular_scaling(points, mask, region, params):
        cx, cy = region['center']
        width = region['width']
        height = region['height']
        angle = region.get('angle', 0)  # 获取旋转角度
        scale_x = params['scale_x']
        scale_y = params['scale_y']
        core_ratio = params['core_ratio']

        core_width = width * core_ratio
        core_height = height * core_ratio
        core_half_w = core_width / 2
        core_half_h = core_height / 2
        red_half_w = width / 2
        red_half_h = height / 2
        trans_width_x = red_half_w - core_half_w
        trans_width_y = red_half_h - core_half_h

        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        deformed = points.copy()
        for i in range(len(points)):
            if not mask[i]:
                continue
            x, y = points[i]
            # 转换到局部坐标系（矩形旋转至轴对齐）
            dx = x - cx
            dy = y - cy
            local_x = dx * cos_a + dy * sin_a
            local_y = -dx * sin_a + dy * cos_a

            if abs(local_x) > red_half_w or abs(local_y) > red_half_h:
                continue

            # 计算变形强度（与轴对齐版本相同）
            in_core = (abs(local_x) <= core_half_w) and (abs(local_y) <= core_half_h)
            if in_core:
                strength = 1.0
            else:
                if local_x < -core_half_w:
                    dist_x = -core_half_w - local_x
                    strength_x = 1 - dist_x / trans_width_x if trans_width_x > 0 else 0
                elif local_x > core_half_w:
                    dist_x = local_x - core_half_w
                    strength_x = 1 - dist_x / trans_width_x if trans_width_x > 0 else 0
                else:
                    strength_x = 1.0
                if local_y < -core_half_h:
                    dist_y = -core_half_h - local_y
                    strength_y = 1 - dist_y / trans_width_y if trans_width_y > 0 else 0
                elif local_y > core_half_h:
                    dist_y = local_y - core_half_h
                    strength_y = 1 - dist_y / trans_width_y if trans_width_y > 0 else 0
                else:
                    strength_y = 1.0
                strength = min(strength_x, strength_y)

            def smooth_factor(core_factor, s):
                return core_factor + (1 - core_factor) * (1 - s**3)
            final_scale_x = smooth_factor(scale_x, strength)
            final_scale_y = smooth_factor(scale_y, strength)

            # 局部坐标系中缩放
            new_local_x = local_x * final_scale_x
            new_local_y = local_y * final_scale_y

            # 边界裁剪
            new_local_x = max(-red_half_w, min(red_half_w, new_local_x))
            new_local_y = max(-red_half_h, min(red_half_h, new_local_y))

            # 变换回全局坐标系
            new_x = cx + new_local_x * cos_a - new_local_y * sin_a
            new_y = cy + new_local_x * sin_a + new_local_y * cos_a

            deformed[i] = (round(new_x, 3), round(new_y, 3))

        return deformed
    # -------------------------- 核心入口：区域变形调度 --------------------------
    @staticmethod
    def deform_region(points, region, params):
        """原入口逻辑不变，仅调整Sine参数传递"""
        points_np = np.array(points)
        deformed = points_np.copy()
        region_mask = RegionDeformer._point_in_region(points_np, region)
        deform_type = params.get('type', 'Scaling')
        
        if deform_type == "Scaling":
            deformed = RegionDeformer._apply_expansion(
                points_np, region_mask, region, 
                params.get('Factor', 1.2),
                params.get('Transition Width (mm)', 1.0),
                params   # 新增：传递完整 params 字典
            )
        elif deform_type == "Sine":
            # 注意：Sine变形不再使用Transition Width参数
            deformed = RegionDeformer._apply_sine(
                points_np, region_mask, region,
                params.get('Amplitude', 0.6),
                params.get('Frequency', 0.2),
                params.get('Transition Ratio', 0.2),
                region.get('transition_width', 1.0)  # 使用区域本身的transition_width
            )
        elif deform_type == "Twist":
            deformed = RegionDeformer._apply_twist(
                points_np, region_mask, region,
                params.get('Strength', 0.35),
                params.get('Transition Width (mm)', 1.0)
            )
        elif deform_type == "Polar Wave":
            A = params.get('A', 0.1)
            B = params.get('B', 0.08)
            C = params.get('C', 2.0)
            deformed = RegionDeformer._apply_polar_wave(
                points_np, region_mask, region, A, B, C
            )
        elif deform_type == "Rectangular Scaling":
            deformed = RegionDeformer._apply_rectangular_scaling(
                points_np, region_mask, region, params
            )
        return [tuple(point) for point in deformed]
    
    # -------------------------- 保留原辅助方法（Expansion/Sine用） --------------------------
    @staticmethod
    def _point_in_region(points, region):
        """判断点在区域内（支持所有形状，包括矩形）"""
        region_type = region.get('type')
        
        if region_type in ["triangle", "custom"]:
            path = Path(region['vertices'])
            return path.contains_points(points)
        elif region_type == 'circle':
            center = np.array(region['center'])
            radii = np.linalg.norm(points - center, axis=1)
            return radii <= region['radius'] + region.get('transition_width', 1.0)
        elif region_type == 'rectangle':
            # 优先使用顶点判断（支持旋转矩形）
            if 'vertices' in region:
                path = Path(region['vertices'])
                return path.contains_points(points)
            else:
                # 兼容无顶点的情况（轴对齐矩形）
                cx, cy = region.get('center', (0, 0))
                if 'width' in region and 'height' in region:
                    half_w = region['width'] / 2
                    half_h = region['height'] / 2
                elif 'side_length' in region:
                    half_w = region['side_length'] / 2
                    half_h = half_w
                else:
                    return np.zeros(len(points), dtype=bool)
                transition = region.get('transition_width', 1.0)
                in_x = (points[:, 0] >= cx - half_w - transition) & \
                    (points[:, 0] <= cx + half_w + transition)
                in_y = (points[:, 1] >= cy - half_h - transition) & \
                    (points[:, 1] <= cy + half_h + transition)
                return in_x & in_y
        elif region_type == 'square':
            # 正方形（可能来自模块3）
            if 'vertices' in region:
                path = Path(region['vertices'])
                return path.contains_points(points)
            else:
                cx, cy = region['center']
                half_side = region['side_length'] / 2
                transition = region.get('transition_width', 1.0)
                in_x = (points[:, 0] >= cx - half_side - transition) & \
                    (points[:, 0] <= cx + half_side + transition)
                in_y = (points[:, 1] >= cy - half_side - transition) & \
                    (points[:, 1] <= cy + half_side + transition)
                return in_x & in_y
        elif region_type == 'ellipse':
            center = np.array(region['center'])
            h = region['semi_major'] + region.get('transition_width', 1.0)
            v = region['semi_minor'] + region.get('transition_width', 1.0)
            dx = points[:, 0] - center[0]
            dy = points[:, 1] - center[1]
            return (dx**2 / h**2 + dy**2 / v**2) <= 1
            
        return np.zeros(len(points), dtype=bool)
    
    @staticmethod
    def _get_region_strength(points, region):
        """原强度计算（仅Expansion用，未修改）"""
        region_type = region.get('type')
        transition = region.get('transition_width', 1.0)
        center = np.array(region['center'])
        
        if transition <= 0:
            return np.ones(len(points))
            
        if region_type in ["triangle", "custom"]:
            distances = np.linalg.norm(points - center, axis=1)
            vertices = np.array(region['vertices'])
            max_dist_to_center = np.max(np.linalg.norm(vertices - center, axis=1))
            distances = max_dist_to_center - distances
        elif region_type == 'circle':
            distances = region['radius'] - np.linalg.norm(points - center, axis=1)
        elif region_type == 'square':
            cx, cy = center
            half_side = region['side_length'] / 2
            dx = np.maximum(cx - half_side - points[:, 0], 
                           points[:, 0] - (cx + half_side))
            dy = np.maximum(cy - half_side - points[:, 1], 
                           points[:, 1] - (cy + half_side))
            distances = -np.maximum(dx, dy, np.zeros_like(dx))
        elif region_type == 'ellipse':
            h = region['semi_major']
            v = region['semi_minor']
            dx = points[:, 0] - center[0]
            dy = points[:, 1] - center[1]
            ellipse_value = (dx**2 / h**2 + dy**2 / v**2) - 1
            distances = -ellipse_value * min(h, v)
        else:
            return np.ones(len(points))
            
        strength = np.clip(distances / transition, 0, 1)
        return strength
    
    # -------------------------- 保留原Expansion/Sine变形逻辑 --------------------------
    @staticmethod
    def _apply_expansion(points, mask, region, factor, transition, deform_params=None):
        """展开变形，支持多种过渡函数"""
        if deform_params is None:
            deform_params = {}
        
        # 获取过渡类型和参数
        trans_type = deform_params.get("Transition Type", "Default (1 - t^2.5)^2")
        if trans_type == "Late Steep":
            k = deform_params.get("k", 0.5)
            n = deform_params.get("n", 2)
        
        # 变形强度（因为变形公式是 1 + strength，所以 factor-1）
        strength = factor - 1
        
        deformed = points.copy()
        cx, cy = region['center']
        base_width = region.get('base_width', 25.0)
        base_length = region.get('base_length', 31.4159)
        
        for i in range(len(points)):
            if not mask[i]:
                continue
            
            x, y = points[i]
            
            # 边界点不变形
            if (np.isclose(x, 0, atol=1e-6) or 
                np.isclose(x, base_width, atol=1e-6) or 
                np.isclose(y, 0, atol=1e-6) or 
                np.isclose(y, -base_length, atol=1e-6)):
                continue
            
            # 计算归一化距离 t (0~1)
            t = RegionDeformer._shape_distance_ratio(x, y, region)
            
            if t <= 1.0:
                # 根据过渡类型计算权重
                if trans_type == "Default (1 - t^2.5)^2":
                    transition_weight = (1 - t**2.5) ** 2
                elif trans_type == "Cosine":
                    transition_weight = 0.5 * (1 + np.cos(np.pi * t))
                elif trans_type == "Late Steep":
                    if t <= k:
                        transition_weight = 1.0
                    else:
                        t_norm = (t - k) / (1 - k) if k < 1 else 1.0
                        transition_weight = 1 - (t_norm ** n)
                else:
                    transition_weight = (1 - t**2.5) ** 2  # 回退
                
                weight = strength * transition_weight
                dx = x - cx
                dy = y - cy
                new_x = x + dx * weight
                new_y = y + dy * weight
                deformed[i] = [round(new_x, 3), round(new_y, 3)]
        
        return deformed
    
    @staticmethod
    def _apply_circle_expansion_center_algorithm(points, mask, region, factor):
        """应用示例代码中中心圆形的膨胀算法"""
        deformed = points.copy()
        cx, cy = region['center']
        radius = region['radius']
        
        # 获取边界参数
        base_width = region.get('base_width', 25.0)
        base_length = region.get('base_length', 31.4159)
        
        # 变形强度直接使用factor（对应示例代码中的strength）
        strength = factor
        
        for i in range(len(points)):
            if not mask[i]:
                continue
                
            x, y = points[i]
            
            # 检查是否为边界点
            is_border_point = (
                np.isclose(x, 0, atol=1e-6) or 
                np.isclose(x, base_width, atol=1e-6) or 
                np.isclose(y, 0, atol=1e-6) or 
                np.isclose(y, -base_length, atol=1e-6)
            )
            
            if is_border_point:
                continue  # 边界点不变形
                
            dx = x - cx
            dy = y - cy
            distance = np.hypot(dx, dy)
            
            # 计算点到圆心的距离
            if distance <= radius:
                # 使用中心圆形的变形公式
                t = distance / radius
                # 中心圆形的过渡函数：(1 - t^2.5)^2
                transition_weight = (1 - t**2.5) ** 2
                weight = strength * transition_weight
                
                # 加法变形公式（与示例代码完全一致）
                new_x = x + dx * weight
                new_y = y + dy * weight
                
                # 四舍五入到小数点后3位
                deformed[i] = [round(new_x, 3), round(new_y, 3)]
        
        return deformed
    @staticmethod
    def _apply_sine(points, mask, region, amplitude, frequency, transition_ratio, transition_width):
        """正弦变形（修复自定义区域问题）"""
        # 注意：transition_width参数仍然保留，但将从其他地方获取
        
        deformed = points.copy()
        region_type = region.get('type')
        center = np.array(region['center'])
        min_y = -region.get('base_length', 31.4159)
        max_y = 0.0

        for i in range(len(points)):
            if not mask[i]:
                continue
            
            x, y = points[i]
            strength = RegionDeformer._calculate_sine_strength(x, y, region, transition_ratio)
            
            if strength > 0:
                y_offset = amplitude * strength * np.sin(frequency * x * 2 * np.pi)
                y_warped = y + y_offset
                deformed[i, 1] = max(min_y, min(max_y, y_warped))

        return deformed
    
    @staticmethod
    def _calculate_sine_strength(x, y, region, transition_ratio):
        """Sine变形强度计算 - 修复三角形和自定义区域的过渡比问题"""
        region_type = region.get('type')
        strength = 0.0

        if region_type == 'circle':
            cx, cy = region['center']
            radius = region['radius']
            dist = np.hypot(x - cx, y - cy)
            core_radius = radius * (1 - transition_ratio)
            if dist <= core_radius:
                strength = 1.0
            elif dist <= radius:
                strength = ((radius - dist) / (radius - core_radius)) ** 3
            else:
                strength = 0.0
                
        elif region_type == 'square':
            cx, cy = region['center']
            side_length = region['side_length']
            half_side = side_length / 2
            
            # 计算点到四条边的距离
            dist_to_edge_x = min(x - (cx - half_side), (cx + half_side) - x)
            dist_to_edge_y = min(y - (cy - half_side), (cy + half_side) - y)
            min_dist = min(dist_to_edge_x, dist_to_edge_y)
            
            # 过渡区域宽度
            transition_width = side_length * transition_ratio
            
            if min_dist >= transition_width:
                strength = 1.0
            elif min_dist >= 0:
                strength = (min_dist / transition_width) ** 3
            else:
                strength = 0.0
        elif region_type == 'rectangle':
            cx, cy = region['center']
            width = region['width']
            height = region['height']
            half_w = width / 2
            half_h = height / 2

            # 计算点到四条边的距离
            dist_to_edge_x = min(x - (cx - half_w), (cx + half_w) - x)
            dist_to_edge_y = min(y - (cy - half_h), (cy + half_h) - y)
            min_dist = min(dist_to_edge_x, dist_to_edge_y)

            # 过渡区域宽度（使用矩形最小边长乘以比例）
            transition_width = min(width, height) * transition_ratio

            if min_dist >= transition_width:
                strength = 1.0
            elif min_dist >= 0:
                strength = (min_dist / transition_width) ** 3
            else:
                strength = 0.0
        elif region_type == 'ellipse':
            cx, cy = region['center']
            semi_major = region['semi_major']
            semi_minor = region['semi_minor']
            
            # 计算归一化椭圆距离
            norm_dist = ((x - cx)**2 / (semi_major**2)) + ((y - cy)**2 / (semi_minor**2))
            
            # 核心区域阈值
            core_threshold = (1 - transition_ratio) ** 2
            
            if norm_dist <= core_threshold:
                strength = 1.0
            elif norm_dist <= 1.0:
                # 使用平滑的过渡函数
                t = (np.sqrt(norm_dist) - (1 - transition_ratio)) / transition_ratio
                strength = (1 - t) ** 3
            else:
                strength = 0.0
                
        elif region_type in ["triangle", "custom"]:
            vertices = region['vertices']
            
            # 首先检查点是否在多边形内
            path = Path(vertices)
            inside = path.contains_point((x, y))
            
            if not inside:
                return 0.0
                
            # 计算点到各边的最短距离
            min_dist = float('inf')
            n = len(vertices)
            for i in range(n):
                x1, y1 = vertices[i]
                x2, y2 = vertices[(i+1) % n]
                
                # 计算点到线段的距离
                line_length_squared = (x2 - x1)**2 + (y2 - y1)**2
                if line_length_squared == 0:
                    # 如果线段长度为0，计算点到点的距离
                    dist = np.hypot(x - x1, y - y1)
                else:
                    # 计算投影参数
                    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_squared))
                    # 计算投影点
                    proj_x = x1 + t * (x2 - x1)
                    proj_y = y1 + t * (y2 - y1)
                    # 计算距离
                    dist = np.hypot(x - proj_x, y - proj_y)
                    
                if dist < min_dist:
                    min_dist = dist
            
            # 🔴 修复：重新计算多边形的内接圆半径
            # 首先计算多边形的中心（我们已经有了region['center']）
            center_x, center_y = region['center']
            
            # 计算中心点到各边的最短距离（即内接圆半径）
            center_min_dist = float('inf')
            for i in range(n):
                x1, y1 = vertices[i]
                x2, y2 = vertices[(i+1) % n]
                
                # 计算中心点到线段的距离
                line_length_squared = (x2 - x1)**2 + (y2 - y1)**2
                if line_length_squared == 0:
                    dist_to_center = np.hypot(center_x - x1, center_y - y1)
                else:
                    t = max(0, min(1, ((center_x - x1) * (x2 - x1) + (center_y - y1) * (y2 - y1)) / line_length_squared))
                    proj_x = x1 + t * (x2 - x1)
                    proj_y = y1 + t * (y2 - y1)
                    dist_to_center = np.hypot(center_x - proj_x, center_y - proj_y)
                
                if dist_to_center < center_min_dist:
                    center_min_dist = dist_to_center
            
            # 🔴 关键修复：使用与其他形状一致的逻辑
            # transition_width = 内接圆半径 * transition_ratio
            transition_width = center_min_dist * transition_ratio
            
            if min_dist >= transition_width:
                strength = 1.0
            elif min_dist >= 0:
                # 使用平滑的过渡函数
                strength = (min_dist / transition_width) ** 3
            else:
                strength = 0.0

        return strength
    
    # -------------------------- 修改4：重写Twist变形逻辑 --------------------------
    @staticmethod
    def _apply_twist(points, mask, region, strength, transition):
        """Twist变形逻辑（基于Strength，中心→边缘平滑扭曲，包含过渡区域）"""
        deformed = points.copy()
        cx, cy = region["center"]  # 区域中心（旋转中心）
        
        # 获取区域的基本尺寸
        base_width = region.get('base_width', 25.0)
        base_length = region.get('base_length', 31.4159)
        
        for i in range(len(points)):
            if not mask[i]:
                continue
                
            x, y = points[i]
            
            # 跳过边界点
            if (np.isclose(x, 0, atol=1e-6) or 
                np.isclose(x, base_width, atol=1e-6) or 
                np.isclose(y, 0, atol=1e-6) or 
                np.isclose(y, -base_length, atol=1e-6)):
                continue
            
            # 计算点在区域内的归一化距离t
            t = RegionDeformer._shape_distance_ratio(x, y, region)
            
            # 定义过渡区域范围（transition以mm为单位）
            # 当transition=0时，只有t<=1.0的区域变形
            # 当transition>0时，t在1.0到1.0+transition_factor范围内有逐渐衰减的变形
            transition_factor = min(transition * 0.05, 0.5)  # 限制最大过渡区域
            
            if t <= 1.0 + transition_factor:
                dx = x - cx
                dy = y - cy
                r = np.hypot(dx, dy)
                angle = np.arctan2(dy, dx)
                
                if t <= 1.0:
                    # 核心区域：完全变形
                    weight = 1.0
                    # 计算扭曲角度：中心处最大，边缘处减小
                    twist_angle = strength * 2.0 * np.pi * (1.0 - t)
                    # 平滑权重
                    smooth_weight = (1.0 - t**3)**2
                else:
                    # 过渡区域：变形逐渐衰减
                    # 计算过渡权重（从1线性衰减到0）
                    weight = (1.0 + transition_factor - t) / transition_factor
                    # 过渡区域的扭曲角度较小
                    twist_angle = strength * 2.0 * np.pi * 0.1
                    # 平滑权重也较小
                    smooth_weight = weight * 0.5
                
                # 应用变形
                new_angle = angle + twist_angle * smooth_weight
                new_x = cx + r * np.cos(new_angle)
                new_y = cy + r * np.sin(new_angle)
                deformed[i] = [round(new_x, 6), round(new_y, 6)]

        return deformed

    @staticmethod
    def _apply_polar_wave(points, mask, region, A, B, C):
        """Polar Wave 变形 - 基于第4模块算法移植"""
        deformed = points.copy()
        region_type = region.get('type', '').lower()
        
        if region_type == 'circle':
            cx, cy = region['center']
            radius = region['radius']
            
            for i in range(len(points)):
                if not mask[i]:
                    continue
                
                x, y = points[i]
                dx = x - cx
                dy = y - cy
                r = np.hypot(dx, dy)
                
                if r <= radius:
                    # 极坐标波动计算
                    wave_term = A * np.cos(C * r) * np.exp(-B * r)
                    r_deformed = r * (1 + wave_term)
                    
                    # 计算角度
                    theta = np.arctan2(dy, dx)
                    
                    # 转换回笛卡尔坐标
                    x_deformed = cx + r_deformed * np.cos(theta)
                    y_deformed = cy + r_deformed * np.sin(theta)
                    
                    deformed[i] = [round(x_deformed, 3), round(y_deformed, 3)]
                    
        elif region_type == 'square':
            cx, cy = region['center']
            half_side = region['side_length'] / 2
            
            for i in range(len(points)):
                if not mask[i]:
                    continue
                
                x, y = points[i]
                
                # 检查点是否在正方形内
                if (cx - half_side <= x <= cx + half_side and 
                    cy - half_side <= y <= cy + half_side):
                    
                    dx = x - cx
                    dy = y - cy
                    r = np.hypot(dx, dy)
                    
                    # 极坐标波动计算
                    wave_term = A * np.cos(C * r) * np.exp(-B * r)
                    r_deformed = r * (1 + wave_term)
                    
                    # 计算角度
                    theta = np.arctan2(dy, dx)
                    
                    # 转换回笛卡尔坐标
                    x_deformed = cx + r_deformed * np.cos(theta)
                    y_deformed = cy + r_deformed * np.sin(theta)
                    
                    deformed[i] = [round(x_deformed, 3), round(y_deformed, 3)]
                    
        elif region_type == 'ellipse':
            cx, cy = region['center']
            a = region['semi_major']
            b = region['semi_minor']
            
            for i in range(len(points)):
                if not mask[i]:
                    continue
                
                x, y = points[i]
                dx = x - cx
                dy = y - cy
                
                # 检查点是否在椭圆内
                if (dx**2 / a**2 + dy**2 / b**2) <= 1:
                    r = np.hypot(dx, dy)
                    
                    # 极坐标波动计算
                    wave_term = A * np.cos(C * r) * np.exp(-B * r)
                    r_deformed = r * (1 + wave_term)
                    
                    # 计算角度
                    theta = np.arctan2(dy, dx)
                    
                    # 转换回笛卡尔坐标
                    x_deformed = cx + r_deformed * np.cos(theta)
                    y_deformed = cy + r_deformed * np.sin(theta)
                    
                    deformed[i] = [round(x_deformed, 3), round(y_deformed, 3)]
                    
        elif region_type in ['triangle', 'custom']:
            vertices = region.get('vertices', [])
            if len(vertices) < 3:
                return deformed
                
            # 创建 matplotlib Path 用于精确点包容检测
            path = Path(vertices)
            cx = sum(v[0] for v in vertices) / len(vertices)
            cy = sum(v[1] for v in vertices) / len(vertices)
            
            for i in range(len(points)):
                if not mask[i]:
                    continue
                
                x, y = points[i]
                
                if path.contains_point((x, y)):
                    dx = x - cx
                    dy = y - cy
                    r = np.hypot(dx, dy)
                    
                    # ✅ 直接使用实际距离 r，与第4模块完全相同
                    wave_term = A * np.cos(C * r) * np.exp(-B * r)
                    r_deformed = r * (1 + wave_term)
                    
                    theta = np.arctan2(dy, dx)
                    x_deformed = cx + r_deformed * np.cos(theta)
                    y_deformed = cy + r_deformed * np.sin(theta)
                    
                    # ✅ 不检查是否仍在区域内，与第4模块保持一致
                    deformed[i] = [round(x_deformed, 3), round(y_deformed, 3)]
        
        return deformed