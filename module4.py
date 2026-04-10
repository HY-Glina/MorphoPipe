import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Ellipse, Polygon
from matplotlib.widgets import Button
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint, LineString
from shapely.affinity import rotate, translate
import math

# 添加组合数计算函数
try:
    from math import comb
except ImportError:
    # 对于Python < 3.8，自己实现comb函数
    from math import factorial
    def comb(n, k):
        return factorial(n) // (factorial(k) * factorial(n - k))

class Module4RegionSelector:
    def __init__(self, ax, params, callback=None, parent=None):
        # ---------------- 基础参数 ----------------
        self.ax = ax
        self.params = params
        self.callback = callback
        self.parent = parent  # 新增：保存父窗口引用
        self.length = params.get('length', 31.4159)
        self.upper_bound = 0
        self.lower_bound = -self.length

        # ---------------- 区域状态变量 ----------------
        self.region_type = None
        self.original_region = None
        self.associated_regions = []
        self.all_regions = []

        # ---------------- 交互状态变量 ----------------
        self.is_drawing = False
        self.draw_start_point = None
        self.is_dragging = False
        self.is_rotating = False
        self.is_interacting = False
        self.drag_offset = (0, 0)
        self.rotate_start_angle = 0
        self.current_angle = 0
        
        # ---------------- 自定义选区相关变量 ----------------
        self.selected_points = []       # 已选择的点集（用于自定义选区）
        self.temp_patch = None          # 临时预览的图形
        self.preview_line = None        # 临时预览线（用于顶点连线）
        self.custom_mode = 'line'       # 自定义形状模式（line/curve）
        self.is_custom_selecting = False # 是否处于自定义选区模式

        # ---------------- 图形元素 ----------------
        self.region_patch = None
        self.rotate_handle = None
        self.associated_patches = []

        # ---------------- 原始尺寸记录 ----------------
        self.original_width = None
        self.original_height = None
        self.original_major_axis = None
        self.original_minor_axis = None

        # ---------------- 初始化界面元素 ----------------
        self._bind_mouse_events()
        # 不再在这里添加确认按钮，而是在主窗口中添加
        self._init_reference_lines()
        self.canvas = ax.figure.canvas
        self._confirm_enabled = False
        
        # 新增：存储按钮引用
        self.confirm_btn = None

    # ==================================================
    # 🟢 绑定事件
    # ==================================================
    def _bind_mouse_events(self):
        self.ax.figure.canvas.mpl_connect('button_press_event', self.on_mouse_press)
        self.ax.figure.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.ax.figure.canvas.mpl_connect('button_release_event', self.on_mouse_release)
        self.ax.figure.canvas.mpl_connect('button_press_event', self._on_double_click)

    # ==================================================
    # 🟢 添加确认按钮
    # ==================================================
    def _add_confirm_button(self):
        """添加确认按钮，并绑定点击事件"""
        self.confirm_ax = self.ax.figure.add_axes([0.8, 0.01, 0.15, 0.05])
        self.confirm_btn = Button(self.confirm_ax, 'Confirm (disabled)')
        self.confirm_btn.on_clicked(self._on_button_click)
        self._confirm_enabled = False

    def _update_confirm_button_label(self):
        """更新按钮文字（适配PyQt按钮）"""
        if self.confirm_btn:
            label = 'Confirm & Generate Regions' if self._confirm_enabled else 'Confirm (disabled)'
            self.confirm_btn.setText(label)  # 使用setText方法设置按钮文本
            self.confirm_btn.setEnabled(self._confirm_enabled)  # 使用setEnabled方法设置按钮状态
        


    def on_confirm_button_clicked(self):
        """PyQt按钮点击事件"""
        print("Module4: confirm button clicked (handler entered)")
        
        # 安全检查：确保按钮可用且没有区域正在交互
        if not self._confirm_enabled:
            print("Module4: Button disabled, ignoring click.")
            return
            
        if self.original_region is None:
            print("Module4: No region drawn yet.")
            return
            
        if self.is_interacting:
            print("Module4: Still interacting, please finish current operation first.")
            return
        
        self.generate_associated_regions()

    # ==================================================
    # 🟢 参考线
    # ==================================================
    def _init_reference_lines(self):
        """初始化参考线（修复版本：不重置坐标轴范围）"""
        try:
            # 保存当前坐标轴范围
            x_min, x_max = self.ax.get_xlim()
            y_min, y_max = self.ax.get_ylim()
            
            # 清除可能存在的旧参考线
            for line in self.ax.lines[:]:
                if hasattr(line, 'get_label') and line.get_label() in ['upper_bound', 'lower_bound']:
                    line.remove()
            
            # 绘制参考线
            self.ax.axhline(y=self.upper_bound, color='red', linestyle='--', alpha=0.7, label='upper_bound')
            self.ax.axhline(y=self.lower_bound, color='blue', linestyle='--', alpha=0.7, label='lower_bound')
            
            # 恢复之前的坐标轴范围
            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(y_min, y_max)
            self.ax.set_aspect('equal')
        except Exception as e:
            print(f"Reference lines initialization error: {e}")

    # ==================================================
    # 🟢 形状类型选择
    # ==================================================
    def set_region_type(self, region_type, custom_mode=None):
        """设置当前区域类型，并重置所有交互、按钮与鼠标状态
        Args:
            region_type: 区域类型
            custom_mode: 可选的自定义模式，如果不提供则使用当前模式或默认
        """
        valid_types = ['circle', 'rectangle', 'ellipse', 'custom']
        if region_type not in valid_types:
            raise ValueError(f"Invalid region type! Only supports {valid_types}")

        # --- 1️⃣ 清除旧补丁与状态 ---
        self._clear_all_patches()
        self.is_drawing = False
        self.is_dragging = False
        self.is_rotating = False
        self.is_interacting = False
        self.current_angle = 0
        self.is_custom_selecting = False
        self.selected_points = []

        # --- 2️⃣ 彻底释放所有鼠标捕获和锁定 ---
        self._force_release_all_locks()

        # --- 3️⃣ 设置新类型并更新按钮状态 ---
        self.region_type = region_type
        print(f"Module4: Region type set → {region_type}")

        if region_type == 'custom':
            self.is_custom_selecting = True
            # 🔴 修复：使用传入的custom_mode，否则使用当前值，否则使用默认值
            if custom_mode is not None:
                self.custom_mode = custom_mode
            elif not hasattr(self, 'custom_mode'):
                self.custom_mode = 'line'  # 默认值
            # 如果custom_mode为None但已有custom_mode属性，则保持当前值
            
            print(f"Module4: Custom mode is → {self.custom_mode}")

        self._confirm_enabled = False
        # 不再调用 _add_confirm_button()，而是更新PyQt按钮状态
        self._update_confirm_button_label()

        # --- 4️⃣ 重新绑定鼠标事件 ---
        self._bind_mouse_events()

        # --- 5️⃣ 强制刷新画布 ---
        try:
            self.canvas.draw_idle()
        except Exception:
            pass

    def set_custom_mode(self, mode):
        """设置自定义选区模式"""
        if mode in ['line', 'curve']:
            self.custom_mode = mode
            print(f"Module4.set_custom_mode: 模式设置为 → {mode}")
            
            # 清除当前选择，重新开始
            self._clear_all_patches()
            self.selected_points = []
            self.is_custom_selecting = True
            
            # 🔴 新增：更新状态显示（如果有父窗口引用）
            if hasattr(self, 'parent') and self.parent:
                if mode == 'curve':
                    self.parent.module4_status.setText(f"Status: Curve mode - click to add control points")
                else:
                    self.parent.module4_status.setText(f"Status: Line mode - click to add points, double-click to close")
            
            # 如果是曲线模式，还需要重置一些特定状态
            if mode == 'curve':
                print("已切换到曲线模式")
    # ==================================================
    # 🟢 鼠标交互事件
    # ==================================================
    def on_mouse_press(self, event):
        if event.inaxes != self.ax or event.button != 1:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        self.is_interacting = True

        # 自定义选区模式 - 添加点
        if self.region_type == 'custom' and self.is_custom_selecting:
            self.selected_points.append((x, y))
            self.ax.scatter(x, y, c='red', s=30, zorder=5)
            self.ax.figure.canvas.draw_idle()
            return

        # 绘制模式 - 开始绘制新区域
        if self.original_region is None:
            if self.region_type == 'custom':
                # custom 类型：进入点累积模式
                self.is_custom_selecting = True
                self.selected_points = [(x, y)]
                self.ax.scatter(x, y, c='red', s=30, zorder=5)
                self.ax.figure.canvas.draw_idle()
            else:
                self.start_drawing((x, y))
            return

        # 交互模式 - 检查点击位置
        click_point = ShapelyPoint(x, y)

        # 1. 检查是否点击了旋转控制点
        if self.region_type in ['rectangle', 'ellipse', 'custom'] and self.is_point_in_rotate_handle((x, y)):
            self.is_rotating = True
            self.is_dragging = False
            if hasattr(self.original_region, 'centroid'):
                region_centroid = self.original_region.centroid
                self.rotate_start_angle = math.atan2(y - region_centroid.y, x - region_centroid.x)
            return

        # 2. 检查是否点击了区域内部
        if self.is_point_in_region((x, y)):
            self.is_dragging = True
            self.is_rotating = False
            if hasattr(self.original_region, 'centroid'):
                region_centroid = self.original_region.centroid
                self.drag_offset = (x - region_centroid.x, y - region_centroid.y)
            return

        # 3. 其他情况：清除当前选择，开始新绘制
        self._clear_all_patches()
        if self.region_type == 'custom':
            self.is_custom_selecting = True
            self.selected_points = [(x, y)]
            self.ax.scatter(x, y, c='red', s=30, zorder=5)
            self.ax.figure.canvas.draw_idle()
        else:
            self.start_drawing((x, y))
    def _clear_scatter_points(self):
        """移除所有红色控制点（散点）"""
        for collection in self.ax.collections[:]:
            try:
                colors = collection.get_facecolor()
                if len(colors) > 0 and len(colors[0]) >= 3:
                    # 判断是否为红色 (R>0.9, G<0.1, B<0.1)
                    if colors[0][0] > 0.9 and colors[0][1] < 0.1 and colors[0][2] < 0.1:
                        collection.remove()
            except Exception:
                pass
        self.ax.figure.canvas.draw_idle()
    def on_mouse_move(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        x, y = event.xdata, event.ydata

        # 避免微小鼠标抖动
        if hasattr(self, '_last_mouse_pos'):
            last_x, last_y = self._last_mouse_pos
            if abs(x - last_x) < 0.1 and abs(y - last_y) < 0.1:
                return
        self._last_mouse_pos = (x, y)

        # 自定义选区预览
        if self.region_type == 'custom' and self.is_custom_selecting and self.selected_points:
            self._update_custom_preview((x, y))
            return

        if self.is_drawing:
            self._update_drawing((x, y))
        elif self.is_dragging and self.original_region and hasattr(self.original_region, 'centroid'):
            self._handle_drag_movement(x, y)
        elif self.is_rotating and self.original_region and hasattr(self.original_region, 'centroid'):
            self._handle_rotation_movement(x, y)
        # 注意：已移除多余的旋转处理代码

    def _handle_drag_movement(self, x, y):
        """处理拖拽移动，支持自定义曲线区域"""
        try:
            region_centroid = self.original_region.centroid
            dx = x - region_centroid.x - self.drag_offset[0]
            dy = y - region_centroid.y - self.drag_offset[1]

            if abs(dx) < 0.01 and abs(dy) < 0.01:
                return  # 微小移动忽略

            if self.region_type == 'custom':
                # 平移所有控制点
                self.selected_points = [(px + dx, py + dy) for px, py in self.selected_points]

                # 根据模式重新生成最终多边形
                if self.custom_mode == 'curve' and len(self.selected_points) >= 2:
                    curve_points = self._catmull_rom_spline(self.selected_points)
                    if len(self.selected_points) >= 3:  # 闭合曲线
                        closing = self._catmull_rom_spline([self.selected_points[-1], self.selected_points[0]], 10)
                        curve_points.extend(closing[1:])
                    try:
                        self.original_region = ShapelyPolygon(curve_points)
                    except Exception as e:
                        print(f"Curve creation failed, fallback to convex hull: {e}")
                        self.original_region = ShapelyPolygon(self.selected_points).convex_hull
                else:
                    self.original_region = ShapelyPolygon(self.selected_points)

                # 更新图形显示
                self._update_custom_patch()
                print(f"Dragged custom region, dx={dx:.2f}, dy={dy:.2f}")

            else:
                # 非自定义区域（矩形/椭圆/圆形）
                self.original_region = translate(self.original_region, dx, dy)
                self._update_patch_position()

        except Exception as e:
            print(f"Error in _handle_drag_movement: {e}")

    def _handle_rotation_movement(self, x, y):
        """处理旋转，支持自定义曲线区域及矩形/椭圆"""
        try:
            region_centroid = self.original_region.centroid
            current_angle_rad = math.atan2(y - region_centroid.y, x - region_centroid.x)
            delta_angle = math.degrees(current_angle_rad - self.rotate_start_angle)

            if abs(delta_angle) < 0.5:
                return  # 微小旋转忽略

            if self.region_type == 'custom':
                # 自定义区域的旋转逻辑（保持不变）
                angle_rad = math.radians(delta_angle)
                cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
                cx, cy = region_centroid.x, region_centroid.y

                new_points = []
                for px, py in self.selected_points:
                    dx = px - cx
                    dy = py - cy
                    dx_rot = dx * cos_a - dy * sin_a
                    dy_rot = dx * sin_a + dy * cos_a
                    new_points.append((cx + dx_rot, cy + dy_rot))
                self.selected_points = new_points

                # 根据模式重新生成最终多边形
                if self.custom_mode == 'curve' and len(self.selected_points) >= 2:
                    curve_points = self._catmull_rom_spline(self.selected_points)
                    if len(self.selected_points) >= 3:
                        closing = self._catmull_rom_spline([self.selected_points[-1], self.selected_points[0]], 10)
                        curve_points.extend(closing[1:])
                    try:
                        self.original_region = ShapelyPolygon(curve_points)
                    except Exception:
                        self.original_region = ShapelyPolygon(self.selected_points).convex_hull
                else:
                    self.original_region = ShapelyPolygon(self.selected_points)

                self._update_custom_patch()
                print(f"Rotated custom region, angle={self.current_angle:.2f}°")

            elif self.region_type == 'rectangle':
                # 矩形旋转：手动重建顶点，避免 Shapely 误差
                self.current_angle = (self.current_angle + delta_angle) % 360
                # 获取当前中心（从区域质心获得，可能略有误差，但手动重建可消除累积误差）
                cx, cy = region_centroid.x, region_centroid.y
                half_w = self.original_width / 2
                half_h = self.original_height / 2
                angle_rad = math.radians(self.current_angle)
                cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
                # 未旋转的四个角（相对于中心）
                local_vertices = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)]
                rotated_vertices = []
                for dx, dy in local_vertices:
                    x_rot = dx * cos_a - dy * sin_a
                    y_rot = dx * sin_a + dy * cos_a
                    rotated_vertices.append((cx + x_rot, cy + y_rot))
                # 更新 Shapely 多边形
                self.original_region = ShapelyPolygon(rotated_vertices)
                # 更新 matplotlib patch
                if self.region_patch:
                    self.region_patch.set_xy(rotated_vertices)
                # 更新旋转控制点位置
                self._update_rotate_handle_position()
                print(f"Rotated rectangle, angle={self.current_angle:.2f}°")

            else:
                # 椭圆等其他形状继续使用 Shapely rotate
                self.original_region = rotate(
                    self.original_region, delta_angle,
                    origin=region_centroid, use_radians=False
                )
                self._update_patch_position()
                self.current_angle = (self.current_angle + delta_angle) % 360   # 新增：更新累积角度
                self._update_patch_position()

            self.rotate_start_angle = current_angle_rad
            self.ax.figure.canvas.draw_idle()

        except Exception as e:
            print(f"Error in _handle_rotation_movement: {e}")
    def _update_rotate_handle_position(self):
        """更新旋转控制点的位置"""
        if not self.original_region or not self.rotate_handle:
            return
        
        try:
            region_centroid = self.original_region.centroid
            
            if self.region_type == 'rectangle':
                # 在矩形上方显示旋转控制点
                bounds = self.original_region.bounds
                handle_y = bounds[3] + 5  # 矩形顶部上方5个单位
                handle_x = (bounds[0] + bounds[2]) / 2  # 矩形中心X
                self.rotate_handle.center = (handle_x, handle_y)
            elif self.region_type == 'ellipse':
                # 在椭圆上方显示旋转控制点
                bounds = self.original_region.bounds
                handle_y = bounds[3] + 5
                handle_x = region_centroid.x
                self.rotate_handle.center = (handle_x, handle_y)
            elif self.region_type == 'custom':
                # 在自定义区域上方显示旋转控制点
                if self.selected_points:
                    y_coords = [p[1] for p in self.selected_points]
                    x_coords = [p[0] for p in self.selected_points]
                    max_y = max(y_coords)
                    center_x = sum(x_coords) / len(x_coords)
                    self.rotate_handle.center = (center_x, max_y + 5)
                    
        except Exception as e:
            print(f"Module4: Error updating rotate handle: {e}")
    def on_mouse_release(self, event):
        if self.is_dragging and self.original_region and hasattr(self.original_region, 'centroid'):
            # 输出最终位置
            centroid = self.original_region.centroid
            print(f"Module4: Drag finished. Final position: ({centroid.x:.2f}, {centroid.y:.2f})")
        
        if self.is_rotating and self.original_region and hasattr(self.original_region, 'centroid'):
            # 输出最终角度
            print(f"Module4: Rotation finished. Final angle: {self.current_angle:.2f}°")
        
        self.is_drawing = False
        self.is_dragging = False
        self.is_rotating = False
        self.is_interacting = False

        if self.original_region is not None:
            self._confirm_enabled = True
        else:
            self._confirm_enabled = False
            
        # 确保更新按钮状态
        self._update_confirm_button_label()

    def _on_double_click(self, event):
        """处理双击事件 - 闭合自定义选区"""
        if event.button != 1 or not event.dblclick:
            return
            
        if (self.region_type == 'custom' and self.is_custom_selecting and 
            len(self.selected_points) >= 3):
            self._finalize_custom_selection()
            
    # ==================================================
    # 🟢 自定义选区逻辑
    # ==================================================
    def _catmull_rom_spline(self, points, num_points_per_segment=20):
        """生成Catmull-Rom样条曲线，确保经过每一个控制点"""
        if len(points) < 2:
            return points

        if len(points) == 2:
            return points

        curve = []
        curve.append(points[0])  # 起点

        for i in range(len(points) - 1):
            p0 = points[max(i - 1, 0)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(i + 2, len(points) - 1)]

            for t in np.linspace(0, 1, num_points_per_segment):
                if t == 0:
                    continue

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

                # 检查数值有效性
                if not (np.isfinite(x) and np.isfinite(y)):
                    print(f"Warning: Invalid point generated at t={t}, using control point instead")
                    # 使用 p2 作为备选点
                    x, y = p2
                curve.append((x, y))

        # 终点
        curve.append(points[-1])
        return curve

    def _update_custom_preview(self, current_point=None):
        """更新自定义选区预览"""
        if len(self.selected_points) < 2:
            return
            
        if self.custom_mode == 'curve':
            # 曲线模式：使用Catmull-Rom样条
            if current_point and len(self.selected_points) >= 2:
                preview_points = self.selected_points + [current_point]
            else:
                preview_points = self.selected_points
                
            if len(preview_points) >= 2:
                curve_points = self._catmull_rom_spline(preview_points)
                
                # 绘制曲线
                if self.preview_line:
                    self.preview_line.remove()
                    
                x_curve, y_curve = zip(*curve_points)
                self.preview_line = self.ax.plot(x_curve, y_curve, 'g-', linewidth=2, alpha=0.8)[0]
        else:
            # 直线模式：连接各点
            if self.preview_line:
                self.preview_line.remove()
                
            if len(self.selected_points) > 0 and current_point:
                # 绘制已有点之间的连线
                if len(self.selected_points) > 1:
                    x_lines = []
                    y_lines = []
                    for i in range(len(self.selected_points) - 1):
                        x_lines.extend([self.selected_points[i][0], self.selected_points[i+1][0], None])
                        y_lines.extend([self.selected_points[i][1], self.selected_points[i+1][1], None])
                    
                    # 添加当前点到最后一个点的连线
                    x_lines.extend([self.selected_points[-1][0], current_point[0], None])
                    y_lines.extend([self.selected_points[-1][1], current_point[1], None])
                    
                    self.preview_line = self.ax.plot(x_lines, y_lines, 'g--', linewidth=1, alpha=0.7)[0]
        
        self.ax.figure.canvas.draw_idle()

    def _finalize_custom_selection(self):
        """完成自定义选区（添加旋转控制点）"""
        if len(self.selected_points) < 3:
            print(f"Module4: Need at least 3 points for custom region, got {len(self.selected_points)}")
            return

        vertices = self.selected_points

        # 生成最终的多边形坐标
        polygon_coords = None
        if self.custom_mode == 'curve' and len(vertices) >= 2:
            # 曲线模式：生成Catmull-Rom样条曲线点
            curve_points = self._catmull_rom_spline(vertices)

            # 确保曲线闭合：连接首尾点
            if len(curve_points) >= 2 and len(vertices) >= 3:
                closing_points = self._catmull_rom_spline([vertices[-1], vertices[0]], num_points_per_segment=10)
                # 避免重复添加起点（curve_points已经包含起点）
                curve_points.extend(closing_points[1:])  # 添加除起点外的点

            polygon_coords = curve_points
        else:
            polygon_coords = vertices

        # 验证坐标有效性
        if not polygon_coords or len(polygon_coords) < 3:
            print("Module4: Not enough valid points to create polygon")
            return

        # 尝试创建 Shapely 多边形
        try:
            self.original_region = ShapelyPolygon(polygon_coords)
            if not self.original_region.is_valid:
                print("Module4: Created polygon is invalid, falling back to convex hull")
                self.original_region = self.original_region.convex_hull
        except Exception as e:
            print(f"Module4: Error creating Shapely polygon: {e}")
            # 尝试使用原始顶点创建凸包作为备选
            try:
                self.original_region = ShapelyPolygon(vertices).convex_hull
            except Exception as e2:
                print(f"Module4: Convex hull fallback also failed: {e2}")
                return

        # 移除旧的 region_patch（如果存在）
        if self.region_patch:
            self.region_patch.remove()
            self.region_patch = None

        # 创建 matplotlib 多边形补丁
        try:
            if hasattr(self.original_region, 'exterior'):
                coords = list(self.original_region.exterior.coords)
            else:
                coords = polygon_coords

            self.region_patch = Polygon(
                coords,
                fill=False,
                edgecolor='green',
                linewidth=2,
                label='Original'
            )
            self.ax.add_patch(self.region_patch)
        except Exception as e:
            print(f"Module4: Failed to create matplotlib patch: {e}")
            return

        # 添加旋转控制点
        self._add_rotate_handle()

        # 如果直线模式，显示控制点散点
        if self.custom_mode == 'line':
            self.ax.scatter([p[0] for p in vertices],
                            [p[1] for p in vertices],
                            c='red', s=30, zorder=5)

        # 清除预览线
        if self.preview_line:
            self.preview_line.remove()
            self.preview_line = None
        self._clear_scatter_points()
        # ====== 新增完成标志 ======
        self.selection_finalized = True
        # 更新状态
        self.is_custom_selecting = False
        self._confirm_enabled = True
        self._update_confirm_button_label()

        # 强制重绘
        self.ax.figure.canvas.draw_idle()

        print(f"Module4: Custom region created with {len(vertices)} control points")
    # ==================================================
    # 🟢 绘制逻辑
    # ==================================================
    def start_drawing(self, start_point):
        self._clear_all_patches()
        self.is_drawing = True
        self.draw_start_point = start_point
        self._update_drawing(start_point)

    def _update_drawing(self, current_point):
            # 对于 custom 类型，不应该使用此方法绘制，直接返回
        if self.region_type == 'custom':
            return

        if not (self.is_drawing and self.draw_start_point and self.region_type):
            return
        start_x, start_y = self.draw_start_point
        curr_x, curr_y = current_point
        center = ((start_x + curr_x) / 2, (start_y + curr_y) / 2)
        self._safe_remove_patch(self.region_patch)
        self._safe_remove_patch(self.rotate_handle)

        if self.region_type == 'circle':
            radius = math.hypot(curr_x - start_x, curr_y - start_y) / 2
            self.original_radius = radius  # 🔴 保存半径
            self.original_region = ShapelyPoint(center).buffer(radius)
            self.region_patch = Circle(center, radius, fill=False, edgecolor='green', linewidth=2, label='Original')
            self.rotate_handle = None
            self.original_major_axis = None
            self.original_minor_axis = None

        elif self.region_type == 'rectangle':
            width = abs(curr_x - start_x)
            height = abs(curr_y - start_y)
            self.original_width = width
            self.original_height = height
            half_w, half_h = width / 2, height / 2
            rect_coords = [
                (center[0] - half_w, center[1] - half_h),
                (center[0] + half_w, center[1] - half_h),
                (center[0] + half_w, center[1] + half_h),
                (center[0] - half_w, center[1] + half_h)
            ]
            self.original_region = ShapelyPolygon(rect_coords)
            # 使用 Polygon 替代 Rectangle
            self.region_patch = Polygon(
                rect_coords,
                fill=False, edgecolor='green', linewidth=2, label='Original'
            )
            self.rotate_handle = Circle(
                (center[0], center[1] + half_h + 3), 1, fill=True, color='orange', alpha=0.8, label='Rotate'
            )

        elif self.region_type == 'ellipse':
            major_axis = abs(curr_x - start_x)
            minor_axis = abs(curr_y - start_y)
            self.original_major_axis = major_axis
            self.original_minor_axis = minor_axis
            half_major = major_axis / 2
            half_minor = minor_axis / 2
            ellipse_coords = [
                (center[0] - half_major, center[1] - half_minor),
                (center[0] + half_major, center[1] - half_minor),
                (center[0] + half_major, center[1] + half_minor),
                (center[0] - half_major, center[1] + half_minor)
            ]
            self.original_region = ShapelyPolygon(ellipse_coords)
            self.region_patch = Ellipse(center, major_axis, minor_axis, angle=0,
                                        fill=False, edgecolor='green', linewidth=2, label='Original')
            self.rotate_handle = Circle(
                (center[0], center[1] + (minor_axis / 2) + 3), 1,
                fill=True, color='orange', alpha=0.8, label='Rotate'
            )

        self.ax.add_patch(self.region_patch)
        if self.rotate_handle:
            self.ax.add_patch(self.rotate_handle)
        self._update_legend()
        self.ax.figure.canvas.draw_idle()
        # 新增：绘制完成后更新按钮状态
        if self.original_region is not None:
            self._confirm_enabled = True
            self._update_confirm_button_label()

    # ==================================================
    # 🟢 逻辑与绘图辅助函数
    # ==================================================
    def _safe_remove_patch(self, patch):
        if patch is not None and hasattr(patch, 'axes') and patch.axes == self.ax:
            try:
                patch.remove()
            except Exception:
                pass
                
    def set_qt_button(self, button):
        """设置PyQt按钮引用"""
        self.confirm_btn = button
        self._update_confirm_button_label()  # 初始化按钮状态

    def _update_patch_position(self):
        """更新图形位置（仅矩形改用多边形更新，椭圆保持原样）"""
        if self.region_type == 'custom':
            return  # 自定义区域由 _update_custom_patch 处理
        if not self.original_region:
            return
        
        try:
            if self.region_type == 'circle':
                if self.region_patch:
                    self.region_patch.center = (self.original_region.centroid.x, self.original_region.centroid.y)
            elif self.region_type == 'ellipse':
                if self.region_patch:
                    self.region_patch.center = (self.original_region.centroid.x, self.original_region.centroid.y)
                    self.region_patch.angle = self.current_angle  # 保留椭圆角度更新
            elif self.region_type == 'rectangle':
                if self.region_patch and hasattr(self.original_region, 'exterior'):
                    coords = list(self.original_region.exterior.coords)
                    self.region_patch.set_xy(coords)
            
            self._update_rotate_handle_position()
            self.ax.figure.canvas.draw_idle()
        except Exception as e:
            print(f"Module4: Error updating patch position: {e}")

    def _update_patch_rotation(self):
        if self.region_type in ['rectangle', 'ellipse']:
            self.region_patch.angle = self.current_angle
        self.ax.figure.canvas.draw_idle()
    def _update_custom_patch(self):
        """更新自定义区域的图形显示"""
        # 移除旧的区域图形
        if self.region_patch:
            self.region_patch.remove()
            self.region_patch = None
        
        # 重新创建多边形补丁
        if len(self.selected_points) >= 3:
            self.region_patch = Polygon(self.selected_points, fill=False, edgecolor='green', linewidth=2, label='Original')
            self.ax.add_patch(self.region_patch)
        
        # 更新旋转控制点位置
        if self.rotate_handle:
            self.rotate_handle.remove()
            self.rotate_handle = None
        
        # 添加旋转控制点
        self._add_rotate_handle()
        
        # 强制重绘画布
        self.ax.figure.canvas.draw()
    def _update_custom_patch(self):
        """更新自定义区域的图形显示"""
        print(f"Module4: Updating custom patch with {len(self.selected_points)} points")
        
        # 强制清除所有相关图形元素
        if self.region_patch:
            try:
                self.region_patch.remove()
            except:
                pass
            self.region_patch = None
        
        if self.rotate_handle:
            try:
                self.rotate_handle.remove()
            except:
                pass
            self.rotate_handle = None
        
        # 清除所有相关的集合（散点）
        for collection in self.ax.collections[:]:
            try:
                collection.remove()
            except:
                pass
        
        # 重新创建多边形补丁
        if len(self.selected_points) >= 3:
            try:
                # 如果是曲线模式，使用曲线点绘制平滑曲线
                if self.custom_mode == 'curve' and len(self.selected_points) >= 2:
                    # 生成曲线点
                    curve_points = self._catmull_rom_spline(self.selected_points)
                    
                    # 确保曲线闭合
                    if len(curve_points) >= 2 and len(self.selected_points) >= 3:
                        closing_points = self._catmull_rom_spline([self.selected_points[-1], self.selected_points[0]], num_points_per_segment=10)
                        curve_points.extend(closing_points[1:])  # 避免重复点
                    
                    # 使用曲线点创建多边形
                    self.region_patch = Polygon(curve_points, fill=False, edgecolor='green', linewidth=2, label='Original')
                    print(f"Module4: Created curved polygon with {len(curve_points)} vertices")
                else:
                    # 直线模式，直接使用控制点
                    self.region_patch = Polygon(self.selected_points, fill=False, edgecolor='green', linewidth=2, label='Original')
                    print(f"Module4: Created straight polygon with {len(self.selected_points)} vertices")
                
                self.ax.add_patch(self.region_patch)
            except Exception as e:
                print(f"Module4: Error creating polygon: {e}")
        
        # 重新添加旋转控制点
        self._add_rotate_handle()

        
        # 强制重绘画布
        try:
            self.ax.figure.canvas.draw_idle()
            self.ax.figure.canvas.flush_events()
            print("Module4: Canvas updated")
        except Exception as e:
            print(f"Module4: Error updating canvas: {e}")

    def _add_rotate_handle(self):
        """为自定义区域添加旋转控制点"""
        if self.rotate_handle:
            self.rotate_handle.remove()
        
        # 计算自定义区域的边界框
        if self.region_type == 'custom' and self.selected_points:
            min_x = min(v[0] for v in self.selected_points)
            max_x = max(v[0] for v in self.selected_points)
            min_y = min(v[1] for v in self.selected_points)
            max_y = max(v[1] for v in self.selected_points)
            
            # 在区域上方添加旋转控制点
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            handle_y = max_y + 5  # 在区域上方5个单位
            
            self.rotate_handle = Circle((center_x, handle_y), 1, fill=True, color='orange', alpha=0.8, label='Rotate')
            self.ax.add_patch(self.rotate_handle)
    def _update_legend(self):
        handles, labels = self.ax.get_legend_handles_labels()
        if handles and labels:
            self.ax.legend(handles, labels, loc='upper right', fontsize=8)
        else:
            if self.ax.get_legend():
                self.ax.get_legend().remove()

    def _force_release_all_locks(self):
        """强制释放所有matplotlib锁定和鼠标捕获"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
            
        try:
            # 方法1: 断开所有事件连接
            self.canvas.mpl_disconnect('button_press_event')
            self.canvas.mpl_disconnect('motion_notify_event') 
            self.canvas.mpl_disconnect('button_release_event')
            
            # 方法2: 释放所有axes的鼠标捕获
            for ax in list(self.canvas.figure.axes):
                try:
                    self.canvas.release_mouse(ax)
                except Exception:
                    pass
            
            # 方法3: 安全释放widgetlock（不访问内部属性）
            if hasattr(self.canvas, 'widgetlock'):
                # 尝试释放已知可能被锁定的对象
                objects_to_release = [self, self.ax, self.confirm_btn, self.canvas]
                for obj in objects_to_release:
                    try:
                        self.canvas.widgetlock.release(obj)
                    except Exception:
                        pass
            
            # 方法4: 通过刷新画布重置状态
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Module4: lock release failed → {e}")
    def _get_region_id(self, region):
        """为区域生成唯一标识符"""
        # 使用区域的边界框和面积作为标识符
        bounds = region.bounds
        area = region.area
        # 将边界框和面积转换为字符串作为唯一标识
        return f"{bounds[0]:.3f}_{bounds[1]:.3f}_{bounds[2]:.3f}_{bounds[3]:.3f}_{area:.3f}"
    
    def _region_intersects_base_pattern(self, region):
        """检查区域是否与基础图案有交集（简化版本）"""
        # 获取当前画布的边界
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        
        # 创建表示画布边界的多边形
        canvas_bounds = ShapelyPolygon([
            (x_min, y_min), (x_max, y_min), 
            (x_max, y_max), (x_min, y_max)
        ])
        
        # 检查区域是否与画布边界相交
        return region.intersects(canvas_bounds)
    # ==================================================
    # 🟢 几何与生成逻辑
    # ==================================================
    def is_point_in_region(self, point):
        if not (self.original_region and isinstance(point, tuple) and len(point) == 2):
            return False
        
        # 自定义区域使用Shapely的contains方法
        if self.region_type == 'custom':
            return self.original_region.contains(ShapelyPoint(point))
        
        # 其他区域类型的处理
        if self.region_type == 'ellipse' and self.original_major_axis and self.original_minor_axis:
            x, y = point
            cx, cy = self.original_region.centroid.x, self.original_region.centroid.y
            a = self.original_major_axis / 2
            b = self.original_minor_axis / 2
            if a == 0 or b == 0:
                return False
            return ((x - cx)**2 / a**2) + ((y - cy)**2 / b**2) <= 1.1
        
        return self.original_region.contains(ShapelyPoint(point))

    def is_point_in_rotate_handle(self, point):
        if not self.rotate_handle:
            return False
        
        # 对于自定义区域，确保旋转控制点存在
        if self.region_type == 'custom' and not self.rotate_handle:
            return False
            
        handle_center = self.rotate_handle.center
        distance = math.hypot(point[0] - handle_center[0], point[1] - handle_center[1])
        return distance <= (getattr(self.rotate_handle, 'radius', 1) + 0.5)

    def check_boundary_intersection(self, region):
        x_min, x_max = self.ax.get_xlim()
        upper = LineString([(x_min, self.upper_bound), (x_max, self.upper_bound)])
        lower = LineString([(x_min, self.lower_bound), (x_max, self.lower_bound)])
        return region.intersects(upper), region.intersects(lower)

    def generate_associated_regions(self, event=None):
    # 对矩形进行精确重建，消除浮点误差
        if not self.original_region:
            print("Module4: Please draw a region first!")
            return

        # 清除之前的关联区域，但保留原始区域
        for patch in list(self.associated_patches):
            self._safe_remove_patch(patch)
        self.associated_regions = []
        self.associated_patches = []

        # 使用递归方法生成所有关联区域
        processed_regions = set()  # 用于避免重复处理相同区域
        regions_to_process = [(self.original_region, 0)]  # (区域, 层级)
        
        while regions_to_process:
            current_region, level = regions_to_process.pop(0)
            
            # 为当前区域生成唯一标识（基于边界框和类型）
            region_id = self._get_region_id(current_region)
            if region_id in processed_regions:
                continue
                
            processed_regions.add(region_id)
            
            # 检查当前区域与边界的相交情况
            upper, lower = self.check_boundary_intersection(current_region)
            
            # 根据相交情况生成新的关联区域
            if upper:
                down_region = translate(current_region, 0, -self.length)
                down_id = self._get_region_id(down_region)
                
                if down_id not in processed_regions:
                    # 检查新区域是否与基础图案有交集
                    if self._region_intersects_base_pattern(down_region):
                        self._add_associated_patch(down_region, 'blue', f'Downward_L{level}')
                        regions_to_process.append((down_region, level + 1))
                        print(f"Module4: Added downward region at level {level}")
            
            if lower:
                up_region = translate(current_region, 0, self.length)
                up_id = self._get_region_id(up_region)
                
                if up_id not in processed_regions:
                    # 检查新区域是否与基础图案有交集
                    if self._region_intersects_base_pattern(up_region):
                        self._add_associated_patch(up_region, 'purple', f'Upward_L{level}')
                        regions_to_process.append((up_region, level + 1))
                        print(f"Module4: Added upward region at level {level}")
            
            # 设置最大递归深度，防止无限循环
            if level > 10:  # 最大10层递归
                print(f"Module4: Reached maximum recursion depth ({level})")
                break

        # 更新所有区域列表
        self.all_regions = [self.original_region] + [r[0] for r in self.associated_regions]
        print(f"Module4: Generated {len(self.all_regions)} regions (including original).")
        
        # 确保原始区域仍然显示
        if self.region_patch and self.region_patch not in self.ax.patches:
            self.ax.add_patch(self.region_patch)
        
        if self.callback:
            regions_info = self.get_regions_info()
            print(f"Module4: Sending {len(regions_info) if regions_info else 0} regions to callback")
            self.callback(regions_info)
        
        self.ax.figure.canvas.draw_idle()

    def _add_associated_patch(self, region, color, label):
        if not isinstance(region, (ShapelyPolygon, ShapelyPoint)):
            print(f"Module4: Invalid region type: {type(region)}")
            return

        try:
            # 不再需要单独获取 centroid，因为将使用多边形顶点
            if self.region_type == 'circle':
                # 圆形仍可用 Circle（没有旋转问题）
                radius = math.sqrt(region.area / math.pi)
                centroid = (region.centroid.x, region.centroid.y)
                patch = Circle(centroid, radius, fill=False, edgecolor=color,
                            linestyle='--', linewidth=1.5, alpha=0.8, label=label)
            elif self.region_type in ['rectangle', 'ellipse', 'custom']:
                # 矩形、椭圆、自定义选区统一使用 Polygon 补丁
                vertices = list(region.exterior.coords)
                patch = Polygon(vertices, fill=False, edgecolor=color,
                                linestyle='--', linewidth=1.5, alpha=0.8, label=label)
            else:
                # 其他情况（如未来可能添加的形状）也回退到多边形
                vertices = list(region.exterior.coords)
                patch = Polygon(vertices, fill=False, edgecolor=color,
                                linestyle='--', linewidth=1.5, alpha=0.8, label=label)

            self.ax.add_patch(patch)
            self.associated_patches.append(patch)
            self.associated_regions.append((region, patch))
            self._update_legend()
            print(f"Module4: Added {label} patch for {self.region_type}")
        except Exception as e:
            print(f"Module4: Error adding associated patch: {e}")

    def get_regions_info(self):
        if not self.all_regions:
            return None
        info_list = []
        for i, region in enumerate(self.all_regions):
            c = region.centroid
            info = {
                'id': i,
                'type': self.region_type,
                'centroid': (round(c.x, 3), round(c.y, 3)),
                'length': self.length
            }
            
            if self.region_type == 'circle':
                # 🔴 添加半径信息
                if hasattr(self, 'original_radius'):
                    info['radius'] = self.original_radius
                else:
                    # 计算圆形半径（从区域面积推算）
                    info['radius'] = round(math.sqrt(region.area / math.pi), 3)
                
            elif self.region_type == 'rectangle':
                info['width'] = self.original_width
                info['height'] = self.original_height
                info['angle'] = round(self.current_angle, 2)
                # 添加顶点信息
                if hasattr(region, 'exterior'):
                    vertices = list(region.exterior.coords)
                    # 移除重复的末尾点（多边形闭合点）
                    if len(vertices) > 1 and vertices[0] == vertices[-1]:
                        vertices = vertices[:-1]
                    info['vertices'] = vertices
                
            elif self.region_type == 'ellipse':
                info['major_axis'] = self.original_major_axis
                info['minor_axis'] = self.original_minor_axis
                info['angle'] = round(self.current_angle, 2)
                
            elif self.region_type == 'custom':
                if hasattr(region, 'exterior'):
                    vertices = list(region.exterior.coords)
                    if len(vertices) > 1 and vertices[0] == vertices[-1]:
                        vertices = vertices[:-1]
                    info['vertices'] = vertices
                elif hasattr(region, '__iter__'):
                    info['vertices'] = list(region)
                else:
                    info['vertices'] = self.selected_points.copy()
                    
            info_list.append(info)
        return info_list
    def _clear_all_patches(self):
        """清除所有图形元素"""
        # 清除主要图形
        if self.region_patch:
            try:
                self.region_patch.remove()
            except:
                pass
            self.region_patch = None
        
        if self.rotate_handle:
            try:
                self.rotate_handle.remove()
            except:
                pass
            self.rotate_handle = None
        
        # 清除关联区域
        for p in list(self.associated_patches):
            try:
                p.remove()
            except:
                pass
        self.associated_patches = []
        
        # 清除原始区域和关联区域数据
        self.original_region = None
        self.associated_regions = []
        self.all_regions = []
        
        # 清除自定义选区数据
        self.selected_points = []
        self.is_custom_selecting = False
        
        # 清除预览线
        if self.preview_line:
            try:
                self.preview_line.remove()
            except:
                pass
            self.preview_line = None
        
        # 清除所有散点
        if hasattr(self, 'ax') and self.ax:
            for collection in self.ax.collections[:]:
                try:
                    collection.remove()
                except:
                    pass
        
        # 更新按钮状态
        self._confirm_enabled = False
        self._update_confirm_button_label()
        
        # 更新图例
        self._update_legend()

    def reset_completely(self):
        """完全重置选择器状态"""
        self._clear_all_patches()
        self.selection_finalized = False
        # 重置所有状态变量
        self.region_type = None
        self.original_region = None
        self.associated_regions = []
        self.all_regions = []
        
        self.is_drawing = False
        self.draw_start_point = None
        self.is_dragging = False
        self.is_rotating = False
        self.is_interacting = False
        self.drag_offset = (0, 0)
        self.rotate_start_angle = 0
        self.current_angle = 0
        
        # 自定义选区相关变量
        self.selected_points = []
        self.temp_patch = None
        self.preview_line = None
        self.custom_mode = 'line'
        self.is_custom_selecting = False
        
        # 图形元素
        self.region_patch = None
        self.rotate_handle = None
        self.associated_patches = []
        
        # 原始尺寸记录
        self.original_width = None
        self.original_height = None
        self.original_major_axis = None
        self.original_minor_axis = None
        
        # 按钮状态
        self._confirm_enabled = False
        self._update_confirm_button_label()
        
        # 🔴 新增：清除画布上的所有相关图形元素（不仅仅是自己的）
        if hasattr(self, 'ax') and self.ax:
            # 清除所有绿色的图形
            for patch in self.ax.patches[:]:
                try:
                    if hasattr(patch, 'get_edgecolor'):
                        edgecolor = patch.get_edgecolor()
                        if len(edgecolor) >= 3:
                            # 绿色边框 (0, 1, 0)
                            if edgecolor[0] < 0.1 and edgecolor[1] > 0.9 and edgecolor[2] < 0.1:
                                patch.remove()
                except Exception:
                    pass
            
            # 清除所有橙色填充
            for patch in self.ax.patches[:]:
                try:
                    if hasattr(patch, 'get_facecolor'):
                        facecolor = patch.get_facecolor()
                        if len(facecolor) >= 3:
                            # 橙色填充 (1, 0.65, 0)
                            if facecolor[0] > 0.9 and facecolor[1] > 0.6 and facecolor[1] < 0.7 and facecolor[2] < 0.1:
                                patch.remove()
                except Exception:
                    pass
            
            # 清除所有虚线边框
            for patch in self.ax.patches[:]:
                try:
                    if hasattr(patch, 'get_linestyle'):
                        linestyle = patch.get_linestyle()
                        if linestyle == '--':
                            patch.remove()
                except Exception:
                    pass
            
            # 清除绿色线条
            for line in self.ax.lines[:]:
                try:
                    color = line.get_color()
                    if color in ['green', 'g']:
                        line.remove()
                except Exception:
                    pass
            
            # 清除红色控制点
            for collection in self.ax.collections[:]:
                try:
                    colors = collection.get_facecolor()
                    if len(colors) > 0 and len(colors[0]) >= 3:
                        # 红色 (1, 0, 0)
                        if colors[0][0] > 0.9 and colors[0][1] < 0.1 and colors[0][2] < 0.1:
                            collection.remove()
                except Exception:
                    pass
            
            # 重新初始化参考线
            self._init_reference_lines()
            
            # 重绘画布
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()

    def safe_reset(self):
        """安全重置，避免鼠标锁定冲突"""
        # 先清除所有图形
        self._clear_all_patches()
        
        # 重置所有状态变量
        self.region_type = None
        self.original_region = None
        self.associated_regions = []
        self.all_regions = []
        
        self.is_drawing = False
        self.draw_start_point = None
        self.is_dragging = False
        self.is_rotating = False
        self.is_interacting = False
        self.drag_offset = (0, 0)
        self.rotate_start_angle = 0
        self.current_angle = 0
        
        # 重置图形元素引用
        self.region_patch = None
        self.rotate_handle = None
        self.associated_patches = []
        
        # 重置原始尺寸
        self.original_width = None
        self.original_height = None
        self.original_major_axis = None
        self.original_minor_axis = None
        
        # 重置按钮状态
        self._confirm_enabled = False
        
        # 清除画布并重新初始化
        if hasattr(self, 'ax') and self.ax:
            # 保存当前视图限制
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            # 清除并重新初始化
            self.ax.clear()
            self._init_reference_lines()
            
            # 恢复视图限制
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        
        # 更新按钮标签
        self._update_confirm_button_label()
        
        # 重绘画布
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.draw_idle()