import numpy as np
import math 
# 周期性变形函数模板定义
PERIODIC_FUNCTION_TEMPLATES = {
    1: {
        "name": "①",
        "expression": {
            "both": "x' = x + A·sin(ωBx)·sin(ωCy); y' = y + A'·cos(ωB'x)·cos(ωC'y)",
            "axial": "x' = x; y' = y + A'·cos(ωB'x)·cos(ωC'y)",
            "circumferential": "x' = x + A·sin(ωBx)·sin(ωCy); y' = y"
        },
        "params_default": {
            "A": 0.8, "A_prime": 0.666, "B": 1.0, "B_prime": 1.0,
            "C": 1.0, "C_prime": 1.0, "D": 0.0,
            "periodic_n": 2,
            "period_direction": "length"
        },
        "compute_func": lambda x, y, omega, params: (
            x + params["A"] * np.sin(omega * params["B"] * x) * np.sin(omega * params["C"] * y),
            y + params["A_prime"] * np.cos(omega * params["B_prime"] * x) * np.cos(omega * params["C_prime"] * y)
        )
    },
    2: {
        "name": "②",
        "expression": {
            "both": "x' = x + A·sin(ωBx)·cos(ωCy); y' = y + A'·cos(ωB'x)·sin(ωC'y)",
            "axial": "x' = x; y' = y + A'·cos(ωB'x)·sin(ωC'y)",
            "circumferential": "x' = x + A·sin(ωBx)·cos(ωCy); y' = y"
        },
        "params_default": {
            "A": 1.0, "A_prime": 1.5, "B": 1.0, "B_prime": 1.0,
            "C": 1.0, "C_prime": 1.0, "D": 0.0,
            "periodic_n": 2,
            "period_direction": "length"
        },
        "compute_func": lambda x, y, omega, params: (
            x + params["A"] * np.sin(omega * params["B"] * x) * np.cos(omega * params["C"] * y),
            y + params["A_prime"] * np.cos(omega * params["B_prime"] * x) * np.sin(omega * params["C_prime"] * y)
        )
    },
    3: {
        "name": "③",
        "expression": {
            "both": "x' = x + A·sin(ωBx)·(0.1+0.1cos(ωCy)); y' = y + A'·sin(ωB'x)·sin(ωC'y)",
            "axial": "x' = x; y' = y + A'·sin(ωB'x)·sin(ωC'y)",
            "circumferential": "x' = x + A·sin(ωBx)·(0.1+0.1cos(ωCy)); y' = y"
        },
        "params_default": {
            "A": 1.2, "A_prime": 1.2, "B": 1.0, "B_prime": 2.0,
            "C": 1.0, "C_prime": 1.0, "D": 0.0,
            "periodic_n": 3,
            "period_direction": "length"
        },
        "compute_func": lambda x, y, omega, params: (
            x + params["A"] * np.sin(omega * params["B"] * x) * (0.1 + 0.1 * np.cos(omega * params["C"] * y)),
            y + params["A_prime"] * np.sin(omega * params["B_prime"] * x) * np.sin(omega * params["C_prime"] * y)
        )
    },
    4: {
        "name": "④",
        "expression": {
            "both": "x' = x + A·sin(ωBx)·cos²(ωCy+Dπ); y' = y + A'·cos(ωB'x+Dπ)·sin(ωC'y)",
            "axial": "x' = x; y' = y + A'·cos(ωB'x+Dπ)·sin(ωC'y)",
            "circumferential": "x' = x + A·sin(ωBx)·cos²(ωCy+Dπ); y' = y"
        },
        "params_default": {
            "A": 0.5, "A_prime": 0.5, "B": 1.0, "B_prime": 1.0,
            "C": 1.0, "C_prime": 1.0, "D": 0.5,
            "periodic_n": 2,
            "period_direction": "width"
        },
        "compute_func": lambda x, y, omega, params: (
            x + params["A"] * np.sin(omega * params["B"] * x) * np.power(np.cos(omega * params["C"] * y + params["D"] * np.pi), 2),
            y + params["A_prime"] * np.cos(omega * params["B_prime"] * x + params["D"] * np.pi) * np.sin(omega * params["C_prime"] * y)
        )
    },
    5: {
        "name": "⑤",
        "expression": {
            "both": "x' = x + A·sin(ωBx); y' = y + A'·sin(ωB'y)",
            "axial": "x' = x; y' = y + A'·sin(ωB'y)",
            "circumferential": "x' = x + A·sin(ωBx); y' = y"
        },
        "params_default": {
            "A": 0.5, "A_prime": 0.5, "B": 1.2, "B_prime": 1.2,
            "C": 0.0, "C_prime": 0.0, "D": 0.0,
            "periodic_n": 4,
            "period_direction": "length"
        },
        "compute_func": lambda x, y, omega, params: (
            x + params["A"] * np.sin(omega * params["B"] * x),
            y + params["A_prime"] * np.sin(omega * params["B_prime"] * y)
        )
    },   # ← 模板5结束，加逗号
    6: {
        "name": "⑥",
        "expression": {
            "both": "x' = x - A·sin(2π·f·x/W)·(1 - ((x - xs)/(W-xs))²)  (x≥xs); y' = y",
            "axial": "x' = x - A·sin(2π·f·x/W)·(1 - ((x - xs)/(W-xs))²)  (x≥xs); y' = y",
            "circumferential": "x' = x - A·sin(2π·f·x/W)·(1 - ((x - xs)/(W-xs))²)  (x≥xs); y' = y"
        },
        "params_default": {
            "wave_amplitude (A)": 10.0,
            "wave_frequency (f)": 0.3,
            "boundary_strength": 0.0,
            "x_start_decay (xs)": 0.0,
            "periodic_n": 1,
            "period_direction": "width"
        },
        "compute_func": lambda x, y, omega, params: (
            (lambda A, f, B, xs, W, x0, y0: (
                (lambda wave_val: (
                    (lambda decay_val: (
                        (lambda raw_offset: (
                            (lambda temp_x: (
                                (lambda over_min, over_max: (
                                    x0 + (raw_offset - over_min - over_max * B)
                                ))(
                                    min(0, temp_x),
                                    max(0, temp_x - W)
                                )
                            ))(
                                x0 + raw_offset
                            )
                        ))(
                            -wave_val * decay_val
                        )
                    ))(
                        1.0 if x0 < xs else (
                            1.0 - ((x0 - xs) / (W - xs))**2 if xs < W else 0.0
                        )
                    )
                ))(
                    A * np.sin(2 * np.pi * f * x0 / W) if W != 0 else 0
                )
            ))(
                params["wave_amplitude (A)"],
                params["wave_frequency (f)"],
                params["boundary_strength"],
                params["x_start_decay (xs)"],
                params["width"],
                x, y
            ),
            y
        )
    }  # ← 最后一个条目，不加逗号
}

def get_periodic_function_templates(deform_dimension):
    """获取函数模板列表（带表达式）"""
    templates = []
    for tid, template in PERIODIC_FUNCTION_TEMPLATES.items():
        expr = template["expression"][deform_dimension]
        templates.append((tid, f"{template['name']} ({expr})"))
    return templates

def deform_type4_periodic(base_points, params):
    """
    类型④周期性变形实现
    
    参数:
        base_points: 基础点集列表，每个点为(x, y)元组
        params: 变形参数字典，包含必要的变形配置
        
    返回:
        deformed_points: 变形后的点集
        info: 变形相关信息
    """
    # 参数验证
    required_keys = ["deform_dimension", "func_mode", "length", "width", "periodic_n", "period_direction"]
    for key in required_keys:
        if key not in params:
            raise ValueError(f"Missing required parameter: '{key}'")
    
    deform_dim = params["deform_dimension"]
    func_mode = params["func_mode"]
    period_direction = params["period_direction"]
    base_length = params[period_direction]
    periodic_n = params["periodic_n"]
    omega = (2 * periodic_n * np.pi) / base_length

    # 预设函数模式
    if func_mode == "preset":
        template_id = params["func_template_id"]
        template = PERIODIC_FUNCTION_TEMPLATES[template_id]
        final_params = template["params_default"].copy()
        # 将 params 中所有非周期/模式相关的参数都添加到 final_params
        for key, value in params.items():
            if key not in ["periodic_n", "period_direction", "func_mode", "func_template_id", "deform_dimension"]:
                final_params[key] = value
        
        compute_func = template["compute_func"]
        deformed_points = []
        
        for x, y in base_points:
            x_def_both, y_def_both = compute_func(x, y, omega, final_params)
            
            if deform_dim == "axial":
                x_def, y_def = x, y_def_both
            elif deform_dim == "circumferential":
                x_def, y_def = x_def_both, y
            else:
                x_def, y_def = x_def_both, y_def_both
            
            deformed_points.append((round(x_def, 3), round(y_def, 3)))
    
        # 自定义函数模式
    else:  # 自定义函数模式
        x_expr = params["x_def_expr"]
        y_expr = params["y_def_expr"]
        
        # 构建安全求值环境
        allowed_vars = {
            "x": 0, "y": 0,
            "omega": omega,
            "pi": math.pi,
            "e": math.e,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "exp": math.exp,
            "log": math.log,
            "log10": math.log10,
            "sqrt": math.sqrt,
            "abs": abs,
            "pow": pow
        }
        deformed_points = []
        
        for x, y in base_points:
            allowed_vars["x"], allowed_vars["y"] = x, y
            try:
                # 使用 eval 计算表达式
                x_def_raw = eval(x_expr, {"__builtins__": {}}, allowed_vars)
                y_def_raw = eval(y_expr, {"__builtins__": {}}, allowed_vars)
            except Exception as e:
                raise ValueError(f"Custom function error: {str(e)}")
            
            if deform_dim == "axial":
                x_def, y_def = x, y_def_raw
            elif deform_dim == "circumferential":
                x_def, y_def = x_def_raw, y
            else:
                x_def, y_def = x_def_raw, y_def_raw
            
            deformed_points.append((round(x_def, 3), round(y_def, 3)))
    
    return deformed_points, {"type": "periodic", "parameters": params}
