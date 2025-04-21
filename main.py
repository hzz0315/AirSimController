import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QTimer
from airsim import CarControls ,CarClient
import airsim
from AirSimControllerui import Ui_MainWindow
from AirSimControl import AirSimUDPController, DriveMode
import threading


class AirSimController(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # 初始化变量
        self.udp_controller = None
        self.udp_connected = False
        self.airsim_connected = False

        # 设置默认值
        self.edit_serverip.setText("127.0.0.1")
        self.edit_serverport.setText("41451")
        self.edit_udpserverip.setText("10.20.108.138")
        self.edit_udpserverport.setText("8089")

        # 连接信号槽
        self.btn_connect.clicked.connect(self.connect_airsim)
        self.btn_udpstart.clicked.connect(self.connect_udp)
        self.btn_savefile.clicked.connect(self.save_file)
        self.cbx_drivetype.currentIndexChanged.connect(self.change_drive_mode)

        # 初始化UI状态
        self.update_ui_state()

        # 设置定时器更新车辆信息
        self.timer = QTimer(self)
        self.timer.start(100)  # 每100毫秒更新一次
        self.timer.timeout.connect(self.update_vehicle_info) # 每100毫秒更新启动一次timer 则触发发射一次timeout 的信号 更新一次车辆的信息。


        # 初始化键盘控制标签
        self.init_key_labels()

    def init_key_labels(self):
        """初始化键盘控制标签样式"""
        self.key_labels = {
            'w': self.lab_w,
            'a': self.lab_a,
            's': self.lab_s,
            'd': self.lab_d
        }

        for label in self.key_labels.values():
            label.setStyleSheet("background-color: white;")

    def connect_airsim(self):
        """连接/断开AirSim服务器"""
        try:
            if not self.airsim_connected:
                ip = self.edit_serverip.text()
                port = self.edit_serverport.text()

                # 如果有UDP控制器，通过它连接
                if self.udp_controller:
                    success = self.udp_controller.connect_airsim(ip, port)
                else:
                    # 如果没有UDP控制器，创建本地连接
                    self.client = CarClient(ip=ip, port=int(port))
                    self.client.confirmConnection()
                    self.client.enableApiControl(True)
                    success = True

                if success:
                    self.airsim_connected = True
                    self.btn_connect.setText("断开AirSim")
                    QMessageBox.information(self, "成功", "AirSim连接成功!")
            else:
                # 断开连接
                if self.udp_controller:
                    self.udp_controller.disconnect_airsim()
                elif hasattr(self, 'client'):
                    self.client.enableApiControl(False)
                    self.client = None

                self.airsim_connected = False
                self.btn_connect.setText("连接AirSim")
                QMessageBox.information(self, "成功", "AirSim已断开!")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接AirSim失败: {str(e)}")

        self.update_ui_state()

    def connect_udp(self):
        """连接/断开UDP服务器"""
        ip = self.edit_udpserverip.text()
        port = int(self.edit_udpserverport.text())

        try:
            if not self.udp_connected:
                # 创建新的UDP控制器
                self.udp_controller = AirSimUDPController(udp_ip=ip, udp_port=port)
                if self.airsim_connected:
                    # 如果AirSim已连接，保持连接状态
                    self.udp_controller.airsim_connected = True
                    self.udp_controller.client = self.client

                self.udp_controller.start_udp_server()
                # 启动监听线程
                self.udp_listener_thread = threading.Thread(target=self.udp_controller.udp_listener, daemon=True)
                self.udp_listener_thread.start()

                self.udp_connected = True
                self.btn_udpstart.setText("断开UDP")
                QMessageBox.information(self, "成功", "UDP服务器启动成功!")
            else:
                # 停止UDP服务器，但不影响AirSim连接
                if self.udp_controller:
                    self.udp_controller.stop_udp_server()
                    # 注意：这里不调用disconnect_airsim()，保持AirSim连接
                    self.udp_controller = None

                self.udp_connected = False
                self.btn_udpstart.setText("连接UDP")
                QMessageBox.information(self, "成功", "UDP服务器已停止!")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"UDP服务器操作失败: {str(e)}")
            if self.udp_controller:
                self.udp_controller.stop_udp_server()
                self.udp_controller = None
            self.udp_connected = False
            self.btn_udpstart.setText("连接UDP")

        self.update_ui_state()

    def change_drive_mode(self, index):
        """切换驾驶模式"""
        if not self.udp_connected or not self.udp_controller:
            return

        mode = DriveMode.MANUAL if index == 0 else DriveMode.AUTONOMOUS
        self.udp_controller.drive_mode = mode

        if mode == DriveMode.AUTONOMOUS:
            # 自动驾驶模式逻辑
            self.udp_controller.car_controls = CarControls()
            self.udp_controller.client.setCarControls(self.udp_controller.car_controls)
            QMessageBox.information(self, "提示", "已切换至自动驾驶模式")
        else:
            QMessageBox.information(self, "提示", "已切换至手动驾驶模式")

    def save_file(self):
        """保存文件"""
        file_path = self.edit_file.text()
        if not file_path:
            QMessageBox.warning(self, "警告", "请输入文件保存路径!")
            return

        try:
            # 这里添加保存文件的逻辑
            QMessageBox.information(self, "成功", f"文件已保存到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def update_vehicle_info(self):
        """更新车辆信息"""
        if not self.airsim_connected:
            # 清空显示
            self.lab_speed.setText("")
            self.lab_throttle.setText("")
            self.lab_brake.setText("")
            self.lab_steer.setText("")
            self.lab_x.setText("")
            self.lab_y.setText("")
            self.lab_z.setText("")
            return

        if self.udp_controller and self.udp_controller.airsim_connected:
            # 从UDP控制器获取信息
            self.udp_controller.update_vehicle_state()
            speed = self.udp_controller.car_current_speed
            controls = self.udp_controller.car_controls
            x = self.udp_controller.car_xposition
            y = self.udp_controller.car_yposition
            z = self.udp_controller.car_zposition
        elif hasattr(self, 'client'):
            # 从本地客户端获取信息
            car_state = self.client.getCarState()
            speed = car_state.speed
            position = car_state.kinematics_estimated.position
            x = position.x_val
            y = position.y_val
            z = position.z_val
            controls = self.client.getCarControls() if hasattr(self, 'client') else CarControls()
        else:
            return
        # 更新UI
        self.lab_speed.setText(f"{speed:.2f} m/s")
        self.lab_throttle.setText(f"{controls.throttle:.2f}")
        self.lab_brake.setText(f"{controls.brake:.2f}")
        self.lab_steer.setText(f"{controls.steering:.2f}")
        self.lab_x.setText(f"{x:.2f}")
        self.lab_y.setText(f"{y:.2f}")
        self.lab_z.setText(f"{z:.2f}")

    def update_ui_state(self):
        """根据连接状态更新UI界面中输入框和按钮的状态"""

        # AirSim连接状态
        self.edit_serverip.setEnabled(not self.airsim_connected)
        self.edit_serverport.setEnabled(not self.airsim_connected)
        self.btn_connect.setText("断开AirSim" if self.airsim_connected else "连接AirSim")

        # UDP连接状态
        udp_connected = self.udp_controller is not None and self.udp_controller.is_running
        self.edit_udpserverip.setEnabled(not udp_connected)
        self.edit_udpserverport.setEnabled(not udp_connected)
        self.btn_udpstart.setText("断开UDP" if udp_connected else "连接UDP")

        # 驾驶模式下拉框只在AirSim连接时启用
        self.cbx_drivetype.setEnabled(self.airsim_connected)

    def keyPressEvent(self, event):
        """键盘按下事件"""
        if not self.airsim_connected:
            return

        key = event.text().lower()
        if key in self.key_labels:
            self.key_labels[key].setStyleSheet("background-color: yellow;")

            # 如果有UDP控制器且已连接，通过UDP发送命令
            if self.udp_controller and self.udp_controller.is_running:
                if self.udp_controller.drive_mode == DriveMode.MANUAL:
                    self.udp_controller.handle_command(key)
            # 否则直接控制本地客户端
            elif hasattr(self, 'client'):
                controls = self.client.getCarControls()
                if key == 'w':
                    controls.throttle = 0.5
                    controls.brake = 0
                elif key == 's':
                    controls.throttle = -1
                    controls.brake = 0
                elif key == 'a':
                    controls.steering = -0.5
                elif key == 'd':
                    controls.steering = 0.5
                self.client.setCarControls(controls)

    def keyReleaseEvent(self, event):
        """键盘释放事件"""
        if not self.airsim_connected:
            return

        key = event.text().lower()
        if key in self.key_labels:
            self.key_labels[key].setStyleSheet("background-color: white;")

            # 停止控制
            if key in ['w', 's']:
                if self.udp_controller and self.udp_controller.is_running and self.udp_controller.drive_mode == DriveMode.MANUAL:
                    self.udp_controller.handle_command("stop")
                elif hasattr(self, 'client'):
                    controls = self.client.getCarControls()
                    controls.throttle = 0
                    controls.brake = 1
                    self.client.setCarControls(controls)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 先断开UDP连接
        if self.udp_connected and self.udp_controller:
            self.udp_controller.stop_udp_server()
            self.udp_controller = None

        # 再断开AirSim连接
        if self.airsim_connected:
            if hasattr(self, 'client'):
                self.client.enableApiControl(False)
                self.client = None
            self.airsim_connected = False

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AirSimController()
    controller.show()
    sys.exit(app.exec_())