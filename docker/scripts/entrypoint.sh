#!/bin/bash
set -e

export PATH=/opt/ros/jazzy/bin:$PATH
source /opt/ros/jazzy/setup.bash

export ROS_DISTRO=${ROS_DISTRO:-jazzy}
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}
export ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY:-0}

PROFILE_FROM_ENV="${FASTRTPS_DEFAULT_PROFILES_FILE:-}"
PROFILE_FROM_WORKSPACE="/jazzy_ws/fastdds.xml"
PROFILE_FALLBACK="/tmp/fastdds_profiles.xml"

if [ -n "$PROFILE_FROM_ENV" ] && [ -f "$PROFILE_FROM_ENV" ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$PROFILE_FROM_ENV"
elif [ -f "$PROFILE_FROM_WORKSPACE" ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$PROFILE_FROM_WORKSPACE"
else
    cat > "$PROFILE_FALLBACK" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors>
    <transport_descriptor>
      <transport_id>UdpTransport</transport_id>
      <type>UDPv4</type>
    </transport_descriptor>
  </transport_descriptors>
  <participant profile_name="udp_transport_profile" is_default_profile="true">
    <rtps>
      <userTransports>
        <transport_id>UdpTransport</transport_id>
      </userTransports>
      <useBuiltinTransports>false</useBuiltinTransports>
    </rtps>
  </participant>
</profiles>
XML
    export FASTRTPS_DEFAULT_PROFILES_FILE="$PROFILE_FALLBACK"
fi

if [ -f /jazzy_ws/install/setup.bash ]; then
    source /jazzy_ws/install/setup.bash
elif [ -f /jazzy_ws/install/local_setup.bash ]; then
    source /jazzy_ws/install/local_setup.bash
fi

cat > /root/.bashrc <<EOF_BASHRC
export PATH=/opt/ros/jazzy/bin:\$PATH
source /opt/ros/jazzy/setup.bash
if [ -f /jazzy_ws/install/setup.bash ]; then
  source /jazzy_ws/install/setup.bash
elif [ -f /jazzy_ws/install/local_setup.bash ]; then
  source /jazzy_ws/install/local_setup.bash
fi
export ROS_DISTRO=${ROS_DISTRO}
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}
export ROS_LOCALHOST_ONLY=${ROS_LOCALHOST_ONLY}
export FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE}
alias ros-topics='ros2 topic list'
alias ros-odom='ros2 topic echo /chassis/odom --once'
alias ros-clock='ros2 topic echo /clock --once'
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
EOF_BASHRC

echo "ROS_DISTRO=$ROS_DISTRO"
echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
echo "ROS_LOCALHOST_ONLY=$ROS_LOCALHOST_ONLY"
echo "FASTRTPS_DEFAULT_PROFILES_FILE=$FASTRTPS_DEFAULT_PROFILES_FILE"

if [ $# -eq 0 ]; then
    exec /bin/bash -l
else
    exec "$@"
fi
