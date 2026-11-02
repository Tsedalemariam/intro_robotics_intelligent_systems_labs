#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from lab_interfaces.action import DriveDistance
from my_robot_interfaces.action import Rotate


class SquareDriver(Node):

    def __init__(self):
        super().__init__("square_driver")

        self.declare_parameter("side_length", 0.5)

        self.odom_received = False

        self.odom_subscriber = self.create_subscription(
            Odometry,
            "/odom",
            self.odom_callback,
            10
        )

        self.drive_client = ActionClient(
            self,
            DriveDistance,
            "/drive_distance"
        )

        self.rotate_client = ActionClient(
            self,
            Rotate,
            "/rotate"
        )

        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

    def odom_callback(self, msg):
        self.odom_received = True

    def wait_for_odometry(self):
        self.get_logger().info("Waiting for robot odometry...")

        while rclpy.ok() and not self.odom_received:
            rclpy.spin_once(self, timeout_sec=0.1)

        if self.odom_received:
            self.get_logger().info("Robot odometry received.")

    def stop_robot(self):
        self.cmd_vel_publisher.publish(Twist())

    def drive_side(self, side_number, side_length):
        self.get_logger().info(
            f"Driving side {side_number}: {side_length:.2f} m"
        )

        goal = DriveDistance.Goal()
        goal.distance = side_length

        self.drive_client.wait_for_server()

        future = self.drive_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(
                f"Drive goal rejected on side {side_number}"
            )
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result()

        if (
            result.status != GoalStatus.STATUS_SUCCEEDED
            or not result.result.reached
        ):
            self.get_logger().error(
                f"Drive failed on side {side_number}. "
                f"Travelled: {result.result.travelled:.2f} m"
            )
            return False

        self.get_logger().info(f"Side {side_number} completed")
        return True

    def rotate_corner(self, side_number):
        self.get_logger().info(
            f"Rotating after side {side_number}"
        )

        goal = Rotate.Goal()
        goal.angle = math.pi / 2.0

        self.rotate_client.wait_for_server()

        future = self.rotate_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(
                f"Rotation rejected after side {side_number}"
            )
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result()

        if result.status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(
                f"Rotation failed after side {side_number}"
            )
            return False

        self.get_logger().info(
            f"Corner after side {side_number} completed"
        )
        return True


def main(args=None):
    rclpy.init(args=args)
    node = SquareDriver()

    try:
        node.wait_for_odometry()

        if not node.odom_received:
            node.get_logger().error(
                "No odometry received. Cannot start square."
            )
            return

        side_length = node.get_parameter("side_length").value

        for side in range(1, 5):

            if not node.drive_side(side, side_length):
                node.stop_robot()
                break

            if not node.rotate_corner(side):
                node.stop_robot()
                break

        else:
            node.get_logger().info(
                "Square completed successfully!"
            )

    except KeyboardInterrupt:
        node.stop_robot()

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
