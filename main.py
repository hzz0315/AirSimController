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
        """连接AirSim服务器"""
        try:
            if not hasattr(self, 'airsim_connected') or not self.airsim_connected:
                # 在实际应用中，这里应该创建AirSim连接
                self.client = CarClient(ip=self.edit_serverip.text(), port=int(self.edit_serverport.text()))
                self.client.confirmConnection()
                self.client.enableApiControl(True)
                self.airsim_connected = True
                self.btn_connect.setText("断开连接")
                QMessageBox.information(self, "成功", "AirSim连接成功!")
            else:
                self.airsim_connected = False
                self.btn_connect.setText("连接")
                QMessageBox.information(self, "成功", "AirSim已断开!")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接AirSim失败: {str(e)}")

        self.update_ui_state()

    def connect_udp(self):
        """连接UDP服务器"""
        ip = self.edit_udpserverip.text()
        port = int(self.edit_udpserverport.text())

        try:
            if not self.udp_connected:
                self.udp_controller = AirSimUDPController(udp_ip=ip, udp_port=port)
                self.udp_controller.start()
                self.udp_connected = True
                self.btn_udpstart.setText("断开连接")
                QMessageBox.information(self, "成功", "UDP服务器启动成功!")
            else:
                self.udp_controller.stop()
                self.udp_controller = None
                self.udp_connected = False
                self.btn_udpstart.setText("连接")
                QMessageBox.information(self, "成功", "UDP服务器已停止!")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动UDP服务器失败: {str(e)}")

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
        if self.udp_controller and self.airsim_connected:
            # 更新车辆状态
            self.udp_controller.update_vehicle_state()

            # 更新速度
            speed = self.udp_controller.car_current_speed
            self.lab_speed.setText(f"{speed:.2f} m/s")

            # 更新油门、刹车、转向
            self.lab_throttle.setText(f"{self.udp_controller.car_controls.throttle:.2f}")
            self.lab_brake.setText(f"{self.udp_controller.car_controls.brake:.2f}")
            self.lab_steer.setText(f"{self.udp_controller.car_controls.steering:.2f}")

            # 更新位置
            self.lab_x.setText(f"{self.udp_controller.car_xposition:.2f}")
            self.lab_y.setText(f"{self.udp_controller.car_yposition:.2f}")
            self.lab_z.setText(f"{self.udp_controller.car_zposition:.2f}")

    def update_ui_state(self):
        """根据连接状态更新UI"""


        # AirSim连接状态
        self.edit_serverip.setEnabled(not self.airsim_connected)
        self.edit_serverport.setEnabled(not self.airsim_connected)
        self.btn_connect.setText("断开AirSim" if self.airsim_connected else "连接AirSim")

        # UDP连接状态
        self.edit_udpserverip.setEnabled(not self.udp_connected)
        self.edit_udpserverport.setEnabled(not self.udp_connected)
        self.btn_udpstart.setText("断开UDP" if self.udp_connected else "连接UDP")

        # 驾驶模式下拉框只在AirSim连接时启用
        self.cbx_drivetype.setEnabled(self.airsim_connected)

    def keyPressEvent(self, event):
        """键盘按下事件"""
        # 只需要检查AirSim连接状态，不检查UDP连接
        if self.airsim_connected and self.udp_controller:
            key = event.text().lower()
            if key in self.key_labels:
                self.key_labels[key].setStyleSheet("background-color: yellow;")
                if self.udp_controller.drive_mode == DriveMode.MANUAL:
                    self.udp_controller.handle_command(key)

    def keyReleaseEvent(self, event):
        """键盘释放事件"""
        if self.airsim_connected and self.udp_controller:

         key = event.text().lower()
         if key in self.key_labels:
            self.key_labels[key].setStyleSheet("background-color: white;")

            # 停止控制
            if key in ['w', 's'] and self.udp_controller.drive_mode == DriveMode.MANUAL:
                self.udp_controller.handle_command("stop")

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.udp_connected and self.udp_controller:
            self.udp_controller.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AirSimController()
    controller.show()
    sys.exit(app.exec_())