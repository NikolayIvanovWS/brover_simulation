#!/usr/bin/env python3

import select
import sys
import termios
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HELP_TEXT = """
Keyboard control for BRover-E5

Moving:
  w / s : forward / backward
  a / d : turn left / turn right
  x     : stop

Speed:
  q / z : increase / decrease linear speed
  e / c : increase / decrease angular speed

Press Ctrl+C to exit.
"""


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__("keyboard_teleop")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.linear_speed = 0.25
        self.angular_speed = 0.8
        self.linear = 0.0
        self.angular = 0.0
        self.timer = self.create_timer(0.1, self.publish_twist)

    def publish_twist(self):
        msg = Twist()
        msg.linear.x = self.linear
        msg.angular.z = self.angular
        self.publisher.publish(msg)

    def stop(self):
        self.linear = 0.0
        self.angular = 0.0
        self.publish_twist()

    def handle_key(self, key):
        if key == "w":
            self.linear = self.linear_speed
            self.angular = 0.0
        elif key == "s":
            self.linear = -self.linear_speed
            self.angular = 0.0
        elif key == "a":
            self.linear = 0.0
            self.angular = self.angular_speed
        elif key == "d":
            self.linear = 0.0
            self.angular = -self.angular_speed
        elif key == "x" or key == " ":
            self.stop()
        elif key == "q":
            self.linear_speed = min(self.linear_speed + 0.05, 1.0)
            self.get_logger().info(f"Linear speed: {self.linear_speed:.2f} m/s")
        elif key == "z":
            self.linear_speed = max(self.linear_speed - 0.05, 0.05)
            self.get_logger().info(f"Linear speed: {self.linear_speed:.2f} m/s")
        elif key == "e":
            self.angular_speed = min(self.angular_speed + 0.1, 2.5)
            self.get_logger().info(f"Angular speed: {self.angular_speed:.2f} rad/s")
        elif key == "c":
            self.angular_speed = max(self.angular_speed - 0.1, 0.1)
            self.get_logger().info(f"Angular speed: {self.angular_speed:.2f} rad/s")


def read_key(timeout_sec=0.1):
    ready, _, _ = select.select([sys.stdin], [], [], timeout_sec)
    if ready:
        return sys.stdin.read(1)
    return None


def main(args=None):
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = KeyboardTeleop()

    print(HELP_TEXT)

    try:
        tty.setraw(sys.stdin.fileno())
        while rclpy.ok():
            key = read_key()
            if key == "\x03":
                break
            if key is not None:
                node.handle_key(key)
            rclpy.spin_once(node, timeout_sec=0.0)
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


if __name__ == "__main__":
    main()
