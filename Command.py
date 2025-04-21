from enum import Enum, auto
import json


class CommandType(Enum):
    """指令类型枚举"""
    SET = auto() # 用于设置车辆的属性 1
    GET = auto() # 用于获取车辆的状态信息 2
    CONTROL = auto() # 用于手动模式的车辆的行为 3
    MODE = auto() # 用于控制驾驶模式 4


class PropertyType(Enum):
    """属性类型枚举"""
    THROTTLE = "throttle"
    BRAKE = "brake"
    STEERING = "steering"
    SPEED = "speed"
    POSITION = "position"
    ALL = "all"


class DriveMode(Enum):
    """驾驶模式枚举"""
    MANUAL = "m"
    AUTONOMOUS = "a"


class AirSimCommand:
    """AirSim UDP指令类"""

    #使用字典来存储命令。

    def __init__(self):
        self.commands = {
            'w': ('前进', self._forward),
            's': ('后退', self._backward),
            'a': ('左转', self._left),
            'd': ('右转', self._right),
            'stop': ('停止', self._stop)
        }

    def parse_command(self, raw_command):
        """
        解析原始命令
        :param raw_command: 原始命令字符串
        :return: (command_type, property_type, value) 或 (control_command,) //通过返回的元组来实现控制。
        """
        command = raw_command.lower().strip() # 不让其区分大小写 去除空白字符
        # 空命令处理
        if not command:
            return None

        # 行进指令 (w, a, s, d)
        if command in self.commands:
            return (CommandType.CONTROL, command)

        # 停止指令
        if command == "stop":
            return (CommandType.CONTROL, command)

        # 设置指令 (set throttle:0.5) 命令要有空格，格式： 指令类型 属性：值
        if command.startswith("set "):
            parts = command[4:].split(":") # 将属性和值分开保存到数组中。
            if len(parts) == 2:
                prop = parts[0].strip()
                value = parts[1].strip()
                try:
                    prop_type = PropertyType(prop)
                    value = float(value)
                    return (CommandType.SET, prop_type, value)
                except ValueError:
                    return None
            return None

        # 获取指令 (get speed) 命令要有空格，格式：指令类型 属性值
        if command.startswith("get "):
            prop = command[4:].strip() # 将 属性转成字符串
            try:
                prop_type = PropertyType(prop)
                return (CommandType.GET, prop_type)
            except ValueError:
                return None

        # 切换驾驶模式 (c m / c a)
        if command.startswith("c "):
            mode = command[2:].strip()
            try:
                mode_type = DriveMode(mode)
                return (CommandType.MODE, mode_type)
            except ValueError:
                return None

        return None

    def execute_set_command(self, prop_type, value, controls):
        """
        执行设置命令
        :param prop_type: PropertyType 枚举值
        :param value: 要设置的值
        :param controls: CarControls 对象
        :return: 修改后的 CarControls 对象
        """
        if prop_type == PropertyType.THROTTLE:
            controls.throttle = float(value)
        elif prop_type == PropertyType.BRAKE:
            controls.brake = float(value)
        elif prop_type == PropertyType.STEERING:
            controls.steering = float(value)
        # Note: SPEED and POSITION might need different handling as they're not direct control inputs
        return controls

    # def create_command(self, command_type, *args):
    #     """
    #     创建可发送的命令字符串
    #     :param command_type: CommandType 枚举值
    #     :param args: 附加参数 用来接受任何数量的参数
    #     :return: 可发送的命令字符串
    #     """
    #     if command_type == CommandType.CONTROL:
    #         return args[0]  # 直接返回控制命令 (w, a, s, d)
    #
    #     if command_type == CommandType.SET:
    #         prop_type, value = args # 第二个参数为属性， 第三个参数为属性的值
    #         return f"set {prop_type.value}:{value}"
    #
    #     if command_type == CommandType.GET:
    #         prop_type = args[0]
    #         return f"get {prop_type.value}"
    #
    #     if command_type == CommandType.MODE:
    #         mode_type = args[0]
    #         return f"c {mode_type.value}"
    #
    #     return ""

    def _forward(self, controls):
        """前进命令处理"""
        controls.throttle = 0.2
        controls.brake = 0
        return controls

    def _backward(self, controls):
        """后退命令处理"""
        controls.throttle = -1
        controls.brake = 0
        return controls

    def _left(self, controls):
        """左转命令处理"""

        controls.steering = -0.5
        return controls

    def _right(self, controls):
        """右转命令处理"""

        controls.steering = 0.5
        return controls

    def _stop(self, controls):
        """停止命令处理"""
        controls.throttle = 0
        controls.brake = 1
        controls.steering = 0
        return controls

    def execute_control(self, command, controls):
        """
        执行控制命令
        :param command: 控制命令 (w, a, s, d, stop)
        :param controls: CarControls 对象
        :return: 修改后的 CarControls 对象
        """
        if command in self.commands:
            _, func = self.commands[command] # 获取元组中的方法传入
            return func(controls)
        elif command == "stop":
            return self._stop(controls)
        return controls