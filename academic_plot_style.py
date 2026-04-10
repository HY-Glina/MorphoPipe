import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

class AcademicPlotStyle:
    """学术论文绘图样式配置类"""
    
    # 学术标准配色方案 - 确保黑白打印清晰可辨
    COLORS = {
        # 主要数据颜色
        'primary_black': '#000000',      # 纯黑 - 主要线条和文字
        'primary_blue': '#1f77b4',       # 标准蓝 - 变形数据
        'primary_green': '#2ca02c',      # 标准绿 - 展开路径
        'primary_red': '#d62728',        # 标准红 - 重要边界和标记
        'primary_orange': '#ff7f0e',     # 标准橙 - 模块4区域
        
        # 辅助颜色
        'dark_gray': '#333333',          # 深灰 - 次要文字
        'medium_gray': '#666666',        # 中灰 - 坐标轴
        'light_gray': '#cccccc',         # 浅灰 - 网格线
        'very_light_gray': '#f0f0f0',    # 极浅灰 - 背景
        
        # 3D效果
        'white': '#ffffff',              # 纯白
        'background_gray': '#f8f8f8'     # 背景灰
    }
    
    @classmethod
    def setup_academic_style(cls):
        """设置学术论文专用绘图样式"""
        plt.rcParams.update({
            # 字体设置
            'font.family': 'serif',           # 衬线字体，学术标准
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
            'font.size': 10,                  # 基础字体大小
            'mathtext.fontset': 'stix',       # 数学字体
            
            # 坐标轴设置
            'axes.labelsize': 11,             # 坐标轴标签
            'axes.titlesize': 12,             # 子图标题
            'axes.linewidth': 0.8,            # 坐标轴线宽
            'axes.edgecolor': cls.COLORS['medium_gray'],
            'axes.labelcolor': cls.COLORS['primary_black'],
            
            # 刻度设置
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'xtick.color': cls.COLORS['medium_gray'],
            'ytick.color': cls.COLORS['medium_gray'],
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'xtick.major.width': 0.8,
            'ytick.major.width': 0.8,
            'xtick.minor.width': 0.6,
            'ytick.minor.width': 0.6,
            
            # 线条设置
            'lines.linewidth': 1.0,           # 数据线宽
            'lines.markersize': 4,            # 标记点大小
            'lines.markeredgewidth': 0.8,     # 标记边缘线宽
            
            # 网格设置
            'grid.color': cls.COLORS['light_gray'],
            'grid.linewidth': 0.5,
            'grid.alpha': 0.5,
            'grid.linestyle': '--',
            
            # 图例设置
            'legend.fontsize': 9,
            'legend.frameon': True,
            'legend.framealpha': 0.8,
            'legend.edgecolor': cls.COLORS['light_gray'],
            'legend.fancybox': False,
            'legend.loc': 'best',
            
            # 图形设置
            'figure.dpi': 300,                # 高分辨率适合出版
            'figure.titlesize': 13,
            'figure.titleweight': 'normal',
            
            # 保存设置
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.1,
            'savefig.transparent': False,
            
            # 其他设置
            'patch.linewidth': 0.8,
            'patch.edgecolor': cls.COLORS['primary_black'],
            'scatter.edgecolors': cls.COLORS['primary_black']
        })
    
    @classmethod
    def get_plot_config(cls, plot_type):
        """获取特定类型图表的配置"""
        configs = {
            'original': {
                'line_color': cls.COLORS['primary_black'],
                'line_width': 1.0,
                'line_alpha': 0.8,
                'grid_style': {'color': cls.COLORS['light_gray'], 'linestyle': '--', 'alpha': 0.3},
                'background_color': cls.COLORS['white'],
                'title': 'Original Pattern'
            },
            'deformed': {
                'line_color': cls.COLORS['primary_blue'],
                'line_width': 1.2,
                'line_alpha': 0.8,
                'region_boundary_color': cls.COLORS['primary_red'],
                'region_boundary_width': 1.5,
                'region_boundary_style': '--',
                'module4_boundary_color': cls.COLORS['primary_orange'],
                'module4_boundary_width': 1.5,
                'module4_boundary_style': '--',
                'control_point_color': cls.COLORS['primary_red'],
                'control_point_size': 40,
                'grid_style': {'color': cls.COLORS['light_gray'], 'linestyle': '--', 'alpha': 0.3},
                'background_color': cls.COLORS['white'],
                'title': 'Deformed Pattern'
            },
            'unfolded': {
                'line_color': cls.COLORS['primary_green'],
                'line_width': 1.0,
                'line_alpha': 0.8,
                'grid_style': {'color': cls.COLORS['very_light_gray'], 'linestyle': '-', 'alpha': 0.2},
                'background_color': cls.COLORS['white'],
                'title': 'Unfolded Path'
            },
            '3d_cylinder': {
                'scatter_color': cls.COLORS['primary_blue'],
                'scatter_size': 1.0,
                'scatter_alpha': 0.7,
                'background_color': cls.COLORS['background_gray'],
                'axis_color': cls.COLORS['medium_gray'],
                'title': '3D Cylindrical Projection'
            }
        }
        
        return configs.get(plot_type, {})
    
    @classmethod
    def apply_axis_style(cls, ax, plot_type):
        """应用坐标轴样式"""
        config = cls.get_plot_config(plot_type)
        
        # 设置背景色
        ax.set_facecolor(config.get('background_color', cls.COLORS['white']))
        
        # 设置网格
        grid_style = config.get('grid_style', {})
        ax.grid(True, **grid_style)
        
        # 设置标题样式
        title = config.get('title', '')
        if title:
            ax.set_title(title, fontsize=12, color=cls.COLORS['primary_black'], pad=10)
        
        # 设置坐标轴标签
        ax.set_xlabel(ax.get_xlabel(), fontsize=11, color=cls.COLORS['primary_black'])
        ax.set_ylabel(ax.get_ylabel(), fontsize=11, color=cls.COLORS['primary_black'])
        
        # 设置坐标轴颜色
        for spine in ax.spines.values():
            spine.set_color(cls.COLORS['medium_gray'])
            spine.set_linewidth(0.8)
        
        # 对于3D图特殊处理
        if hasattr(ax, 'set_zlabel'):
            ax.set_zlabel(ax.get_zlabel(), fontsize=11, color=cls.COLORS['primary_black'])
            # 3D坐标轴颜色
            ax.xaxis.pane.set_edgecolor(cls.COLORS['light_gray'])
            ax.yaxis.pane.set_edgecolor(cls.COLORS['light_gray'])
            ax.zaxis.pane.set_edgecolor(cls.COLORS['light_gray'])
            ax.xaxis.pane.set_facecolor(cls.COLORS['background_gray'])
            ax.yaxis.pane.set_facecolor(cls.COLORS['background_gray'])
            ax.zaxis.pane.set_facecolor(cls.COLORS['background_gray'])
            ax.xaxis.pane.set_alpha(0.8)
            ax.yaxis.pane.set_alpha(0.8)
            ax.zaxis.pane.set_alpha(0.8)
    
    @classmethod
    def create_custom_colormap(cls):
        """创建学术风格的色彩映射（用于3D图等）"""
        colors = [cls.COLORS['primary_blue'], cls.COLORS['primary_green'], cls.COLORS['primary_orange']]
        return LinearSegmentedColormap.from_list('academic_sequential', colors, N=256)
    
    @classmethod
    def get_color_cycle(cls):
        """获取学术色彩循环"""
        return [
            cls.COLORS['primary_blue'],
            cls.COLORS['primary_green'], 
            cls.COLORS['primary_red'],
            cls.COLORS['primary_orange'],
            cls.COLORS['primary_black']
        ]


# 便捷函数
def setup_academic_plots():
    """一键设置学术绘图样式"""
    AcademicPlotStyle.setup_academic_style()
    
    # 设置色彩循环
    plt.rcParams['axes.prop_cycle'] = mpl.cycler(color=AcademicPlotStyle.get_color_cycle())


def style_plot(ax, plot_type):
    """快速样式化坐标轴"""
    AcademicPlotStyle.apply_axis_style(ax, plot_type)


def get_academic_colors():
    """获取学术配色字典"""
    return AcademicPlotStyle.COLORS.copy()


# 初始化设置
setup_academic_plots()

# 导出常用配置
ACADEMIC_CONFIG = {
    'line_styles': {
        'solid': '-',
        'dashed': '--', 
        'dotted': ':',
        'dashdot': '-.'
    },
    'marker_styles': {
        'circle': 'o',
        'square': 's',
        'triangle': '^',
        'point': '.'
    },
    'font_sizes': {
        'title': 12,
        'axis_label': 11,
        'tick_label': 9,
        'legend': 9
    }
}


# 使用示例
if __name__ == "__main__":
    # 测试样式设置
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    # 应用样式到各个子图
    plot_types = ['original', 'deformed', 'unfolded', '3d_cylinder']
    for ax, plot_type in zip(axes.flat, plot_types):
        style_plot(ax, plot_type)
        ax.set_title(f"Academic Style: {plot_type.replace('_', ' ').title()}")
    
    plt.tight_layout()
    plt.savefig('academic_style_demo.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("学术绘图样式设置完成！")
    print("配色方案:", get_academic_colors())