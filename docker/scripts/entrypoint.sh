#!/bin/bash

# Fast DDS configuration for ROS 2
# Create Fast DDS profile for better ROS 2 communication
cat > /tmp/fastdds_profiles.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
    <transport_descriptors>
        <transport_descriptor>
            <transport_id>UDPv4</transport_id>
            <type>UDPv4</type>
        </transport_descriptor>
    </transport_descriptors>
    <participant profile_name="default_participant" is_default_profile="true">
        <rtps>
            <builtin>
                <discovery_config>
                    <discoveryProtocol>SERVER</discoveryProtocol>
                    <discoveryServersList>
                        <RemoteServer prefix="44.53.00.5f.45.50.52.4f.53.49.4d.41">
                            <metatrafficUnicastLocatorList>
                                <locator>
                                    <udpv4>
                                        <address>127.0.0.1</address>
                                        <port>11811</port>
                                    </udpv4>
                                </locator>
                            </metatrafficUnicastLocatorList>
                        </RemoteServer>
                    </discoveryServersList>
                </discovery_config>
            </builtin>
        </rtps>
    </participant>
</profiles>
EOF

export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/fastdds_profiles.xml

# Setup ROS 2 environment
export PATH=/opt/ros/jazzy/bin:$PATH
source /opt/ros/jazzy/setup.bash

# Source workspace if exists
if [ -d /jazzy_ws/install ]; then
    echo "Sourcing workspace from /jazzy_ws..."
    source /jazzy_ws/install/setup.bash 2>/dev/null || true
    # Also try local_setup if setup.bash fails
    if [ $? -ne 0 ]; then
        source /jazzy_ws/install/local_setup.bash 2>/dev/null || true
    fi
fi

export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISTRO=jazzy

# Create .bashrc for all subsequent logins
cat > /root/.bashrc << 'INNEREOF'
# ROS 2 environment
export PATH=/opt/ros/jazzy/bin:$PATH
source /opt/ros/jazzy/setup.bash

# Source workspace if exists
if [ -d /jazzy_ws/install ]; then
    source /jazzy_ws/install/setup.bash 2>/dev/null || source /jazzy_ws/install/local_setup.bash 2>/dev/null
fi

# ROS 2 variables
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DISTRO=jazzy

# Fast DDS configuration
export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/fastdds_profiles.xml

# Aliases
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
echo "FASTRTPS_DEFAULT_PROFILES_FILE: $FASTRTPS_DEFAULT_PROFILES_FILE"
echo ""
echo "Workspace: /jazzy_ws"
if [ -d /jazzy_ws/install ]; then
    echo "✓ Workspace sourced"
else
    echo "⚠ Workspace not found at /jazzy_ws/install"
fi
echo ""
echo "Available commands:"
echo "  ros2 topic list    - list all topics"
echo "  ros-topics         - alias for topic list"
echo "  ros-odom           - show odometry data"
echo ""
echo "To start working, just type: ros2 topic list"
echo "========================================="
echo ""

# Execute the command passed to docker run or start bash
if [ $# -eq 0 ]; then
    exec /bin/bash -l
else
    exec "$@"
fi