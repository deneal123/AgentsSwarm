# Аннотация / Abstract

---

## На русском языке

Работа посвящена проектированию и реализации многоагентной робототехнической платформы AgentsSwarm, обеспечивающей кооперативное восприятие сцены группой мобильных роботов, стандартизованное управление флотом и высокоуровневую оркестрацию задач посредством больших языковых моделей.

**Цель работы** — создание интегрированного программного комплекса, в котором запрос пользователя на естественном языке транслируется в скоординированное выполнение миссий группой роботов через единый сквозной контур управления.

**Задачи:** анализ подходов к кооперативному восприятию и координации многороботных систем; разработка микросервисной архитектуры из восьми взаимосвязанных компонентов; реализация LLM-оркестратора на базе OpenAI Agents SDK с девятью специализированными агентами (Router, MissionPlanner, MapAnalyst, Navigation, Charging, Patrol, Inspection, FleetOps, SwarmCoordinator); глубокая доработка трёх MCP-серверов (Mission Control, Mission Dispatch, ROS MSP) с переходом на асинхронную модель вызовов; адаптация форков NVIDIA Mission Control и Mission Dispatch под протокол VDA5050; экспериментальная оптимизация VLA-модели SmolVLA для бортового инференса.

**Методология** основана на принципах облачной робототехники, событийно-ориентированной архитектуры и протокола Model Context Protocol. Эмпирическая база включает симуляцию флота мобильных роботов Carter в NVIDIA Isaac Sim (headless-режим, ROS 2 Jazzy, rosbridge WebSocket); развёртывание LLM-сервиса Qwen2.5-Instruct в режиме Data Parallel на двух узлах Tesla V100 (32 ГБ VRAM) через авторский vLLM-сервис; пайплайн дистилляции, прунинга и квантизации модели SmolVLA.

**Результаты:** реализованы восемь самостоятельных компонентов — Interface (React + FastAPI + Celery, 168 коммитов, v0.5.0), Orchestrator (FastAPI + Agents SDK, 56 коммитов, v0.5.6), vLLM Service (Data Parallel, v0.2.9), доработанные форки Mission Control и Mission Dispatch, настроенный ROS 2 workspace, три переработанных MCP-сервера. Пройдено 43 из 43 интеграционных тестов API оркестратора. Для модели SmolVLA достигнуто сжатие в 443 раза по числу параметров при сохранении более 90% точности (MSE +9,1%, R² −1,8%) и ускорении инференса в 25 раз (450 мс → 18 мс, RTX 4090).

---

## In English

This thesis presents the design and implementation of AgentsSwarm, a multi-agent robotic platform that enables cooperative scene perception among a group of mobile robots, standardised fleet management, and high-level task orchestration driven by large language models.

**The objective** is to build an integrated software system in which a natural-language user request is translated into coordinated multi-robot mission execution through a unified end-to-end control pipeline.

**Research tasks:** analysis of cooperative perception and multi-robot coordination approaches; design of a microservice architecture comprising eight interconnected components; development of an LLM orchestrator based on the OpenAI Agents SDK with nine specialised agents (Router, MissionPlanner, MapAnalyst, Navigation, Charging, Patrol, Inspection, FleetOps, SwarmCoordinator); deep rework of three MCP servers (Mission Control, Mission Dispatch, ROS MSP) with a full migration to asynchronous tool calls; adaptation of NVIDIA Mission Control and Mission Dispatch forks to the VDA5050 protocol; and experimental optimisation of the SmolVLA vision-language-action model for on-board inference.

**The methodology** is grounded in cloud-robotics principles, event-driven architecture, and the Model Context Protocol. The empirical base comprises simulation of a Carter robot fleet in NVIDIA Isaac Sim (headless mode, ROS 2 Jazzy, rosbridge WebSocket); deployment of a Qwen2.5-Instruct LLM service in Data Parallel mode across two Tesla V100 nodes (32 GB VRAM each) via a custom-built vLLM service; and a knowledge-distillation, pruning, and quantisation pipeline for SmolVLA.

**Results:** eight independent components were fully implemented — Interface (React + FastAPI + Celery, 168 commits, v0.5.0), Orchestrator (FastAPI + Agents SDK, 56 commits, v0.5.6), vLLM Service (Data Parallel, v0.2.9), reworked Mission Control and Mission Dispatch forks, a configured ROS 2 workspace, and three heavily modified MCP servers. All 43 orchestrator API integration tests passed. The SmolVLA model was compressed 443-fold in parameter count while retaining over 90% accuracy (MSE +9.1%, R² −1.8%) with a 25× inference speed-up (450 ms → 18 ms on RTX 4090).

---
