#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import Pose2D
from nav_msgs.msg import Odometry
from rclpy.node import Node


def quaternion_to_yaw(x, y, z, w):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class OdomPose2DPublisher(Node):
    def __init__(self):
        super().__init__("odom_pose2d_publisher")
        self.publisher = self.create_publisher(Pose2D, "/odom_pose2d", 10)
        self.subscription = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10,
        )

    def odom_callback(self, odom_msg):
        pose = odom_msg.pose.pose
        orientation = pose.orientation

        pose2d_msg = Pose2D()
        pose2d_msg.x = pose.position.x
        pose2d_msg.y = pose.position.y
        pose2d_msg.theta = quaternion_to_yaw(
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        )

        self.publisher.publish(pose2d_msg)


def main(args=None):
    rclpy.init(args=args)
    node = OdomPose2DPublisher()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
