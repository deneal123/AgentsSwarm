#!/bin/bash
set -e

# ── ROS env ──
export ROS_DISTRO=${ROS_DISTRO:-jazzy}
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}

# ── 1. apt ROS — ros2launch, nav2, rosbridge ──
# Существует только если образ основан на osrf/ros или apt-установлен ROS
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
fi

# ── 2. Внутренняя сборка из исходников (Python 3.12) ──
if [ -f /workspace/jazzy_ws/install/setup.bash ]; then
    export PATH=/workspace/jazzy_ws/install/bin:$PATH
    source /workspace/jazzy_ws/install/local_setup.bash
fi

# ── 3. build_ws — isaac пакеты ──
if [ -f /workspace/build_ws/install/local_setup.bash ]; then
    source /workspace/build_ws/install/local_setup.bash
fi

# ── 4. Монтированный внешний воркспейс ──
if [ -f /jazzy_ws/install/local_setup.bash ]; then
    source /jazzy_ws/install/local_setup.bash
fi

# ── FastDDS профиль ──
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

# ── .bashrc для интерактивных терминалов ──
cat > /root/.bashrc <<EOF_BASHRC
if [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
fi
if [ -f /workspace/jazzy_ws/install/local_setup.bash ]; then
  export PATH=/workspace/jazzy_ws/install/bin:\$PATH
  source /workspace/jazzy_ws/install/local_setup.bash
fi
if [ -f /workspace/build_ws/install/local_setup.bash ]; then
  source /workspace/build_ws/install/local_setup.bash
fi
if [ -f /jazzy_ws/install/local_setup.bash ]; then
  source /jazzy_ws/install/local_setup.bash
fi
export ROS_DISTRO=${ROS_DISTRO}
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID}
export RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION}
export ROS_AUTOMATIC_DISCOVERY_RANGE=${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}
export FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE}
alias ros-topics='ros2 topic list'
alias ros-odom='ros2 topic echo /chassis/odom --once'
alias ros-clock='ros2 topic echo /clock --once'
alias ros-nodes='ros2 node list'
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
EOF_BASHRC

echo "========================================"
echo "ROS_DISTRO                     = $ROS_DISTRO"
echo "ROS_DOMAIN_ID                  = $ROS_DOMAIN_ID"
echo "RMW_IMPLEMENTATION             = $RMW_IMPLEMENTATION"
echo "ROS_AUTOMATIC_DISCOVERY_RANGE  = $ROS_AUTOMATIC_DISCOVERY_RANGE"
echo "FASTRTPS_DEFAULT_PROFILES_FILE = $FASTRTPS_DEFAULT_PROFILES_FILE"
echo "ros2 launch                    = $(command -v ros2 2>/dev/null || echo 'NOT FOUND')"
echo "========================================"

if [ $# -eq 0 ]; then
    exec /bin/bash -l
else
    exec "$@"
fi