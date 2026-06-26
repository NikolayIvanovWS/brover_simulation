#!/usr/bin/env python3

import math

import rclpy
from sensor_msgs.msg import CameraInfo, Image, LaserScan
from rclpy.node import Node


class SensorTopicNormalizer(Node):
    def __init__(self):
        super().__init__("sensor_topic_normalizer")

        self.scan_publisher = self.create_publisher(LaserScan, "/scan", 10)
        self.image_publisher = self.create_publisher(Image, "/front_camera/image", 10)
        self.camera_info_publisher = self.create_publisher(
            CameraInfo,
            "/front_camera/camera_info",
            10,
        )

        self.scan_subscription = self.create_subscription(
            LaserScan,
            "/scan_raw",
            self.scan_callback,
            10,
        )
        self.image_subscription = self.create_subscription(
            Image,
            "/front_camera/image_raw",
            self.image_callback,
            10,
        )

        self.horizontal_fov = 1.047

    def scan_callback(self, msg):
        msg.header.frame_id = "lidar_link"
        self.scan_publisher.publish(msg)

    def image_callback(self, msg):
        msg.header.frame_id = "front_camera_link"
        self.image_publisher.publish(msg)
        self.camera_info_publisher.publish(self.make_camera_info(msg))

    def make_camera_info(self, image_msg):
        width = image_msg.width
        height = image_msg.height
        focal_length = width / (2.0 * math.tan(self.horizontal_fov / 2.0))
        center_x = (width - 1.0) / 2.0
        center_y = (height - 1.0) / 2.0

        msg = CameraInfo()
        msg.header = image_msg.header
        msg.width = width
        msg.height = height
        msg.distortion_model = "plumb_bob"
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        msg.k = [
            focal_length,
            0.0,
            center_x,
            0.0,
            focal_length,
            center_y,
            0.0,
            0.0,
            1.0,
        ]
        msg.r = [
            1.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]
        msg.p = [
            focal_length,
            0.0,
            center_x,
            0.0,
            0.0,
            focal_length,
            center_y,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
        ]
        return msg


def main(args=None):
    rclpy.init(args=args)
    node = SensorTopicNormalizer()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
