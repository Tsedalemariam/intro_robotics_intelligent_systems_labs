import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, Shutdown
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory("diffdrive_bot")

    robot_description = ParameterValue(
        Command([
            "xacro ",
            os.path.join(pkg_share, "urdf", "diffdrive_bot.urdf.xacro")
        ]),
        value_type=str,
    )

    gazebo_server = ExecuteProcess(
        cmd=[
            "gz", "sim", "-s", "-r",
            os.path.join(pkg_share, "worlds", "obstacles.sdf")
        ],
        name="gazebo_server",
        output="screen",
        on_exit=Shutdown(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{
            "robot_description": robot_description,
            "use_sim_time": True
        }],
        output="screen",
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[{
            "config_file": os.path.join(
                pkg_share, "config", "bridge.yaml"
            )
        }],
        output="screen",
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-world", "obstacles",
            "-topic", "robot_description",
            "-name", "diffdrive_bot",
            "-z", "0.05"
        ],
        output="screen",
    )

    return LaunchDescription([
        gazebo_server,
        robot_state_publisher,
        bridge,
        TimerAction(period=2.0, actions=[spawn]),
    ])
