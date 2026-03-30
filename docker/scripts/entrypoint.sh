#!/bin/bash

# Настройка окружения для текущей сессии
export PATH=/opt/ros/jazzy/bin:$PATH
source /opt/ros/jazzy/setup.bash

# Source workspace если есть
if [ -d /jazzy_ws/install ]; then
    for f in $(find /jazzy_ws/install -name "local_setup.bash" -type f 2>/dev/null | sort); do
        source $f 2>/dev/null
    done
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISTRO=jazzy

# Создаем .bashrc для всех последующих входов
cat > /root/.bashrc << 'INNEREOF'
# ROS 2 environment
export PATH=/opt/ros/jazzy/bin:$PATH
source /opt/ros/jazzy/setup.bash

# Source workspace if exists
if [ -d /jazzy_ws/install ]; then
    for f in $(find /jazzy_ws/install -name "local_setup.bash" -type f 2>/dev/null | sort); do
        source $f 2>/dev/null
    done
fi

# ROS 2 variables
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISTRO=jazzy

# Aliases
alias ros-launch='cd /workspace/projects && ros2 launch isaac_ros_vda5050_client_bringup isaac_ros_vda5050_client_nav2.launch.py init_pose_x:=-2.0 init_pose_yaw:=3.14159 mqtt_host_name:=185.55.57.82'
alias ros-topics='ros2 topic list'
alias ros-odom='ros2 topic echo /chassis/odom --once'
alias ros-clock='ros2 topic echo /clock --once'

# Prompt
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
INNEREOF

echo ""
echo "========================================="
echo "ROS 2 Jazzy environment is ready"
echo "========================================="
echo "ROS_DOMAIN_ID: $ROS_DOMAIN_ID"
echo "RMW_IMPLEMENTATION: $RMW_IMPLEMENTATION"
echo ""
echo "Available commands:"
echo "  ros2 topic list    - list all topics"
echo "  ros-topics         - alias for topic list"
echo "  ros-odom           - show odometry data"
echo "  ros-launch         - launch VDA5050 client"
echo ""
echo "To start working, just type: ros2 topic list"
echo "========================================="
echo ""

# Запускаем bash с интерактивной оболочкой
exec /bin/bash -l
