import numpy as np
import math

class GCodeExporter:
    """G代码导出工具类"""
    
    @staticmethod
    def export_unfolded_path_to_txt(unfolded_points, output_file="unfolded_path.txt"):
        """
        将unfolded path导出为纯坐标文本格式
        
        参数:
            unfolded_points: unfold path坐标列表
            output_file: 输出文件名
        """
        if not unfolded_points:
            return False
            
        try:
            with open(output_file, 'w') as f:
                # 直接写入坐标，不添加注释
                for x, y in unfolded_points:
                    f.write(f"G1 X{x:.2f} Y{y:.2f} F180\n")
                    # f.write(f"{x:.2f}, {y:.2f}\n")
            print(f"Unfolded path coordinates exported to {output_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting coordinates: {str(e)}")
            return False
    
    @staticmethod
    def export_points_to_txt(points, output_file, file_type="absolute"):
        """
        导出点坐标到文本文件
        
        参数:
            points: 坐标点列表
            output_file: 输出文件名
            file_type: 文件类型 ("absolute" 或 "relative")
        """
        if not points:
            return False
            
        try:
            with open(output_file, 'w') as f:
                # 直接写入坐标，不添加注释
                for x, y in points:
                    f.write(f"{x:.2f}, {y:.2f}\n")
            
            print(f"{file_type.capitalize()} coordinates exported to {output_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting coordinates: {str(e)}")
            return False
    
    @staticmethod
    def resample_points(points, target_step=0.2):
        """对点进行均匀采样"""
        if len(points) < 2:
            return points
        
        # 计算累积距离
        distances = []
        for i in range(1, len(points)):
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            dist = np.sqrt(dx**2 + dy**2)
            distances.append(dist)
        
        cumulative_dist = [0.0]
        for d in distances:
            cumulative_dist.append(cumulative_dist[-1] + d)
        total_length = cumulative_dist[-1]
        
        if total_length < target_step:
            return [points[0], points[-1]]
        
        # 生成均匀间隔的目标距离
        target_dists = np.arange(0, total_length, target_step)
        if target_dists[-1] < total_length - 1e-6:
            target_dists = np.append(target_dists, total_length)
        
        # 线性插值
        resampled = []
        for dist in target_dists:
            idx = np.searchsorted(cumulative_dist, dist) - 1
            if idx < 0:
                resampled.append(points[0])
                continue
            if idx >= len(points) - 1:
                resampled.append(points[-1])
                continue
            
            t = (dist - cumulative_dist[idx]) / distances[idx]
            x = points[idx][0] + t * (points[idx+1][0] - points[idx][0])
            y = points[idx][1] + t * (points[idx+1][1] - points[idx][1])
            resampled.append((round(x, 3), round(y, 3)))
        
        return resampled
    
    @staticmethod
    def remove_close_points(points, min_distance=0.18):
        """移除距离过近的点"""
        if not points:
            return []
        filtered_points = [points[0]]
        for i in range(1, len(points)):
            last_point = filtered_points[-1]
            current_point = points[i]
            distance = np.linalg.norm(np.array(current_point) - np.array(last_point))
            if distance >= min_distance:
                filtered_points.append(current_point)
        return filtered_points