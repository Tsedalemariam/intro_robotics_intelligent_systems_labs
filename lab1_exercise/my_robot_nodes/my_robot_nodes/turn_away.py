
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from lab_interfaces.msg import ObstacleInfo
from my_robot_interfaces.msg import RobotStatus
from my_robot_interfaces.srv import SetTurnSpeed
from std_srvs.srv import SetBool


class TurnAway(Node):

    def __init__(self):
        super().__init__("turn_away")

        # Parameters
        self.declare_parameter("forward_speed", 0.2)
        self.declare_parameter("turn_speed", 0.5)
        self.declare_parameter("max_turn_speed", 1.5)

        self.enabled = False

        # Publishers
        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10
        )

        self.status_publisher = self.create_publisher(
            RobotStatus,
            "/robot_status",
            10
        )

        # Subscriber
        self.obstacle_subscriber = self.create_subscription(
            ObstacleInfo,
            "/obstacle",
            self.obstacle_callback,
            10
        )

        # Services
        self.enable_service = self.create_service(
            SetBool,
            "/turn_away_enable",
            self.enable_callback
        )

        self.turn_speed_service = self.create_service(
            SetTurnSpeed,
            "/set_turn_speed",
            self.set_turn_speed_callback
        )

    def obstacle_callback(self, msg):
        twist = Twist()

        forward_speed = self.get_parameter("forward_speed").value
        turn_speed = self.get_parameter("turn_speed").value

        status = RobotStatus()
        status.obstacle_distance = msg.distance

        if not self.enabled:
            status.state = "stopped"

        elif msg.too_close:
            twist.linear.x = 0.0

            if msg.angle > 0:
                twist.angular.z = -turn_speed
            else:
                twist.angular.z = turn_speed

            status.state = "turning"

        else:
            twist.linear.x = forward_speed
            twist.angular.z = 0.0
            status.state = "forward"

        if self.enabled:
            self.cmd_vel_publisher.publish(twist)

        self.status_publisher.publish(status)

    def enable_callback(self, request, response):
        was_enabled = self.enabled
        self.enabled = request.data

        if was_enabled and not self.enabled:
            twist = Twist()
            self.cmd_vel_publisher.publish(twist)

        response.success = True

        if self.enabled:
            response.message = "Robot movement enabled"
        else:
            response.message = "Robot movement disabled"

        return response

    def set_turn_speed_callback(self, request, response):
        max_turn_speed = self.get_parameter("max_turn_speed").value

        if request.turn_speed <= 0 or request.turn_speed > max_turn_speed:
            response.success = False
            response.message = (
                f"Invalid speed. Enter a value greater than 0 "
                f"and no greater than {max_turn_speed}."
            )
        else:
            self.set_parameters([
                Parameter("turn_speed", value=request.turn_speed)
            ])

            response.success = True
            response.message = f"Turn speed updated to {request.turn_speed}"

        return response


def main(args=None):
    rclpy.init(args=args)
    node = TurnAway()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
