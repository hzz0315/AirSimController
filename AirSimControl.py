import socket
import threading
from airsim import CarClient, CarControls
import airsim
from Command import AirSimCommand, CommandType, PropertyType, DriveMode


class AirSimUDPController:
    def __init__(self, udp_ip='', udp_port=8089):
        # AirSim客户端设置 ,在连接时再进行创建对象
        self.client = None
        self.airsim_connected = False
        # self.client.confirmConnection()
        # self.client.enableApiControl(True)

        # 控制器
        self.car_controls = CarControls()
        self.drive_mode = DriveMode.MANUAL  # 默认手动模式
        self.command_parser = AirSimCommand() # 创建一个命令的对象

        # UDP服务器设置
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.sock = None
        self.is_running = False#表示udp是否在运行

        # 控制参数 默认值
        self.throttle = 0.3
        self.brake = 0.8
        self.steering = 0.2


        # 初始化车辆状态
        self.update_vehicle_state()

    def connect_airsim(self, ip, port):
        """连接AirSim服务器"""
        if not self.airsim_connected:
            try:
                self.client = CarClient(ip=ip, port=int(port))
                self.client.confirmConnection()
                self.client.enableApiControl(True)
                self.airsim_connected = True
                return True
            except Exception as e:
                print(f"连接AirSim失败: {e}")
                return False
        return True

    def disconnect_airsim(self):
        """断开AirSim连接"""
        if self.airsim_connected and self.client:
            try:
                self.client.enableApiControl(False)
                self.client = None
                self.airsim_connected = False
                return True
            except Exception as e:
                print(f"断开AirSim连接失败: {e}")
                return False
        return True



    # def create_carcontroller(self):
    #     self.car_controls = CarControls()
    #     return self.car_controls



    def update_vehicle_state(self):
        """更新车辆状态信息"""
        if not self.airsim_connected or not self.client:
            return

        self.car_state = self.client.getCarState()
        self.car_current_speed = self.car_state.speed
        position = self.car_state.kinematics_estimated.position # 使用局部变量保证过渡车辆的位置状态。
        self.car_xposition = position.x_val
        self.car_yposition = position.y_val
        self.car_zposition = position.z_val

    def handle_command(self, command, addr=None):
        """处理接收到的命令"""
        if not self.airsim_connected:
            if addr:
                self._send_response("AirSim未连接", addr)
            return

        parsed = self.command_parser.parse_command(command)
        if not parsed:
            print(f"未知命令: {command}")
            if addr:
                self._send_response(f"未知命令: {command}", addr)
            return

        command_type = parsed[0]

        if command_type == CommandType.CONTROL:
            # 控制命令处理
            if self.drive_mode == DriveMode.MANUAL:
                control_cmd = parsed[1]
                self.car_controls = self.command_parser.execute_control(control_cmd, self.car_controls)
                self.client.setCarControls(self.car_controls)
                response = f"执行控制命令: {control_cmd}"

        elif command_type == CommandType.SET:
            # 设置命令处理
            prop_type, value = parsed[1], parsed[2]
            self.car_controls = self.command_parser.execute_set_command(prop_type, value, self.car_controls)
            self.client.setCarControls(self.car_controls)
            response = f"设置{prop_type.value}为: {value}"

        elif command_type == CommandType.GET:
            # 获取状态命令处理
            self.update_vehicle_state()
            prop_type = parsed[1]
            if prop_type == PropertyType.SPEED:
                response = f"当前速度: {self.car_current_speed} m/s"
            elif prop_type == PropertyType.POSITION:
                response = f"当前位置: X={self.car_xposition:.2f}, Y={self.car_yposition:.2f}, Z={self.car_zposition:.2f}"
            elif prop_type == PropertyType.ALL:
                response = (
                    "车辆状态:\n"
                    f"速度: {self.car_current_speed} m/s\n"
                    f"位置: X={self.car_xposition:.2f}, Y={self.car_yposition:.2f}, Z={self.car_zposition:.2f}\n"
                    f"油门: {self.car_controls.throttle:.2f}, 刹车: {self.car_controls.brake:.2f}, 转向: {self.car_controls.steering:.2f}"
                )

        elif command_type == CommandType.MODE:
            # 切换驾驶模式
            mode = parsed[1]
            self.drive_mode = mode
            response = f"切换驾驶模式为: {'手动' if mode == DriveMode.MANUAL else '自动'}"

        print(response)
        if addr:
            self._send_response(response, addr)
    # 自动驾驶模式接口


    # 向客户端发送响应信息
    def _send_response(self, message, addr):
        """通过UDP发送响应消息
        :param message: 要发送的消息
        :param addr: 客户端地址(ip, port)
        """
        try:
            self.sock.sendto(message.encode('utf-8'), addr)
        except Exception as e:
            print(f"发送UDP响应失败: {e}")

    def udp_listener(self):
        """监听UDP消息"""
        print(f"UDP服务器已启动 {self.udp_ip}:{self.udp_port}")
        while self.is_running:
            try:
                data, addr = self.sock.recvfrom(1024) #获取客户端的ip地址
                command = data.decode('utf-8')
                # 将客户端地址传递给handle_command
                self.handle_command(command, addr)
            except Exception as e:
                print(f"接收UDP数据错误: {e}")
                # 这里可以添加自动驾驶的初始化代码

    def start(self):
        """启动UDP监听线程"""
        self.thread = threading.Thread(target=self.udp_listener, daemon=True)
        self.thread.start()

    def stop(self):
        """停止控制器"""
        self.is_running = False
        self.sock.close()
        self.client.enableApiControl(False)
        print("控制器已停止")

    def start_udp_server(self):
        """启动UDP服务器"""
        if not self.is_running:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.udp_ip, self.udp_port))
            self.is_running = True
            return True
        return False

    def stop_udp_server(self):
        """停止UDP服务器"""
        if self.is_running:
            self.sock.close()
            self.sock = None
            self.is_running = False
            return True
        return False


# if __name__ == "__main__":
#     # 用户输入udp ip地址和端口号
#     ip = input("请输入本地服务器的ip地址：\n")
#     port = input("请输入本地服务器的端口号：\n")
#     #可以加校验
#     controller = AirSimUDPController(ip,port)
#     try:
#         controller.start()
#         print("AirSim UDP控制器运行中. 按Ctrl+C停止.")
#         while True:
#             pass
#     except KeyboardInterrupt:
#         controller.stop()