"""
现代化界面演示脚本
运行此文件查看新的界面布局效果
Windows版本 - 移除了Unix shebang行
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from modern_main_window import ModernMainWindow

def main():
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = ModernMainWindow()
    window.show()
    
    # 确保窗口显示在最前面
    window.raise_()
    window.activateWindow()
    
    print("现代化界面演示已启动")
    print("功能特性：")
    print("- 现代化卡片式布局")
    print("- 浮动撤销按钮（右上角）") 
    print("- 步骤指示器")
    print("- 标签页组织功能")
    print("- 专业的配色方案")
    print("- 响应式设计")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()