cd ./../mission_dispatch
docker run -it --network host -v ${PWD}/packages/utils/test_utils/mosquitto.sh:/mosquitto.sh -d eclipse-mosquitto:latest sh mosquitto.sh 1883 9001