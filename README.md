# Документация: Платформа управления роем роботов с AI-оркестрацией


## План работ:

- [] Сконструировать из готовой среды и робота симуляцию на Nvidia Isaac + Ros2, запустить симуляцию и проверить работу.
- [] Развернуть ros-msp-server для взаимодействия с роботом через клиента. Протестировать взаимодействие cli вызов заготовленной команды (вызов тула) -> проксирование через msp-server -> отображение заданного движения робота в симуляции.
- [] Развертывание vllm локальной модели qwen с tool calling -> разработка простого агента (open-agents-sdk) для автоматизации движения работа через текстовые запросы.
- [] Разработать простую реализацию базы данных и фронтенда для сессий, пользователей -> передача  текстового запроса через ui.
- [] Сконфигурировать симуляцию с несколькими роботами и добавить оркестратор агентов, управление роем роботов.
- [] Масштабирование системы и добавление новых субагентских макросистем nvidia-search-video-summarisation.
- [] Субагент поиска информации по истории видеоконтента.
- [] Субагент алертинга в реальном времени.
- [] Субагент qa по видео и изображениям.
- [] Субагент суммаризации долгих видео.


## Sourses

- [x] [vLLM Server](https://github.com/vllm-project/vllm)
- [x] [Ros2](https://github.com/ros2)
- [x] [Redis](https://redis.readthedocs.io/en/stable/index.html)
- [x] [RabbitMQ](https://www.rabbitmq.com/tutorials/tutorial-one-python)
- [x] [PostgreSQL](https://www.geeksforgeeks.org/python/sqlalchemy-tutorial-in-python/)
- [x] [Minio](https://docs.min.io/enterprise/aistor-object-store/developers/sdk/python/)
- [x] [Lerobot](https://github.com/huggingface/lerobot)
- [x] [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- [x] [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)
- [x] [RosMspServer](https://github.com/robotmcp/ros-mcp-server.git)
- [x] [RosMspClient](https://github.com/robotmcp/robotmcp_client.git)
- [x] [NVIDIA Isaac ROS](https://nvidia-isaac-ros.github.io/getting_started/index.html#system-requirements)
- [x] [NVIDIA Isaac ROS Repositories and Packages](https://nvidia-isaac-ros.github.io/repositories_and_packages/index.html)
- [x] [Multiple Robot ROS Navigation](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/ros_tutorials/tutorial_ros_multi_navigation.html)
- [x] [Nvidia Vss Agent](https://docs.nvidia.com/vss/3.1.0/quickstart.html)
- [x] [Nvidia Agent Workflows](https://docs.nvidia.com/vss/latest/adding-workflows.html)
- [x] [video-search-and-summarization](https://github.com/NVIDIA-AI-Blueprints/video-search-and-summarization/tree/main)