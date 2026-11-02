
#!/usr/bin/env python3

import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from my_robot_interfaces.action import Rotate


def yaw_from_quaternion(q):
    """Get the robot's yaw angle in radians."""
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    )


def angle_difference(current, previous):
    """Calculate a small angle change, accounting for angle wrapping."""
    return math.atan2(
        math.sin(current - previous),
        math.cos(current - previous)
    )


class RotateServer(Node):

    def __init__(self):
        super().__init__("rotate_server")

        self.declare_parameter("turn_speed", 0.5)

        self.yaw = None

        group = ReentrantCallbackGroup()

        self.cmd_vel = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.create_subscription(
            Odometry,
            "/odom",
            self.on_odom,
            10,
            callback_group=group
        )

        self.action_server = ActionServer(
            self,
            Rotate,
            "/rotate",
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            cancel_callback=self.on_cancel,
            callback_group=group
        )

    def on_odom(self, msg):
        self.yaw = yaw_from_quaternion(
            msg.pose.pose.orientation
        )

    def on_goal(self, goal_request):
        if goal_request.angle == 0.0 or self.yaw is None:
            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    def on_cancel(self, goal_handle):
        return CancelResponse.ACCEPT

    def execute(self, goal_handle):
        target_angle = goal_handle.request.angle

        previous_yaw = self.yaw
        turned = 0.0

        turn_speed = self.get_parameter("turn_speed").value

        direction = 1.0 if target_angle > 0 else -1.0

        twist = Twist()
        twist.angular.z = direction * turn_speed

        feedback = Rotate.Feedback()
        result = Rotate.Result()

        self.get_logger().info(
            f"Rotating by {target_angle:.2f} radians"
        )

        try:
            while rclpy.ok():

                if goal_handle.is_cancel_requested:
                    self.cmd_vel.publish(Twist())
                    goal_handle.canceled()

                    result.turned = turned

                    self.get_logger().info(
                        f"Rotation canceled at {turned:.2f} radians"
                    )

                    return result

                if self.yaw is None:
                    time.sleep(0.1)
                    continue

                current_yaw = self.yaw

                turned += angle_difference(
                    current_yaw,
                    previous_yaw
                )

                previous_yaw = current_yaw

                feedback.turned = turned
                goal_handle.publish_feedback(feedback)

                if direction * turned >= abs(target_angle):
                    break

                self.cmd_vel.publish(twist)

                time.sleep(0.1)

            self.cmd_vel.publish(Twist())

            result.turned = turned
            goal_handle.succeed()

            self.get_logger().info(
                f"Rotation completed: {turned:.2f} radians"
            )

            return result

        finally:
            self.cmd_vel.publish(Twist())


def main(args=None):
    rclpy.init(args=args)

    node = RotateServer()

    try:
        executor = MultiThreadedExecutor()
        executor.add_node(node)
        executor.spin()

    except (KeyboardInterrupt, ExternalShutdownException):
        pass

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
