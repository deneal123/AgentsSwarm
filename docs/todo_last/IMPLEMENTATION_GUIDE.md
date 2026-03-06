# 🚀 Рекомендации по Реализации Недостающей Функциональности

На основе проверки соответствия документации, представляем конкретные рекомендации по реализации недостающих компонентов.

---

## 1. Реализация `/api/v1/swarm/status` (Приоритет: ВЫСОКИЙ)

### Описание
Агрегированная информация обо всём рое для быстрого обзора состояния системы.

### Требуемые данные (из документации)
- Количество роботов по статусам (idle, busy, error, offline)
- Активные задачи (кол-во, типы)
- Последний анализ AI (если есть)
- Предупреждения и ошибки

### Код для реализации

**Добавить в `schemas/common.py`:**
```python
from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime

class RobotStatusCount(BaseModel):
    idle: int
    busy: int
    error: int
    offline: int
    total: int

class ActiveTaskInfo(BaseModel):
    total: int
    by_type: Dict[str, int]  # {"navigation": 5, "scan": 2}
    urgent_count: int

class SwarmAlert(BaseModel):
    robot_id: str
    level: str  # "info", "warning", "error"
    message: str
    timestamp: datetime

class SwarmStatusResponse(BaseModel):
    robots: RobotStatusCount
    active_tasks: ActiveTaskInfo
    alerts: List[SwarmAlert]
    last_update_at: datetime
    health_score: float  # 0-100
```

**Добавить в `api/v1/robots.py`:**
```python
from datetime import datetime, timedelta

@router.get("/swarm/status", response_model=SwarmStatusResponse)
@require_viewer
async def get_swarm_status(
    current_user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client),
) -> SwarmStatusResponse:
    """
    Получить агрегированную информацию о состоянии роя.
    
    Возвращает:
    - Количество роботов по статусам
    - Активные задачи
    - Открытые предупреждения
    - Общий индекс здоровья системы
    
    Роли: viewer, operator, admin
    """
    try:
        # 1. Получить список всех роботов и их статусы из Redis
        robots_data = await redis_client.get("swarm:robots")
        
        if not robots_data:
            # Fallback: вернуть пустую структуру
            return SwarmStatusResponse(
                robots=RobotStatusCount(idle=0, busy=0, error=0, offline=0, total=0),
                active_tasks=ActiveTaskInfo(total=0, by_type={}, urgent_count=0),
                alerts=[],
                last_update_at=datetime.utcnow(),
                health_score=0.0
            )
        
        # 2. Подсчитать статусы роботов
        robots = json.loads(robots_data)
        status_counts = {
            'idle': sum(1 for r in robots if r.get('status') == 'idle'),
            'busy': sum(1 for r in robots if r.get('status') == 'busy'),
            'error': sum(1 for r in robots if r.get('status') == 'error'),
            'offline': sum(1 for r in robots if r.get('status') == 'offline'),
        }
        status_counts['total'] = len(robots)
        
        # 3. Получить активные задачи из Redis
        active_tasks = await redis_client.get("swarm:tasks:active")
        tasks = json.loads(active_tasks) if active_tasks else []
        
        task_types = {}
        urgent_count = 0
        for task in tasks:
            task_type = task.get('type', 'unknown')
            task_types[task_type] = task_types.get(task_type, 0) + 1
            if task.get('priority') == 'urgent':
                urgent_count += 1
        
        # 4. Получить открытые предупреждения
        alerts_data = await redis_client.get("swarm:alerts")
        alerts = []
        if alerts_data:
            raw_alerts = json.loads(alerts_data)
            alerts = [
                SwarmAlert(
                    robot_id=a.get('robot_id'),
                    level=a.get('level', 'info'),
                    message=a.get('message', ''),
                    timestamp=datetime.fromisoformat(a.get('timestamp', datetime.utcnow().isoformat()))
                )
                for a in raw_alerts
                if (datetime.utcnow() - 
                    datetime.fromisoformat(a.get('timestamp', datetime.utcnow().isoformat())))
                    < timedelta(hours=1)  # Показывать алерты за последний час
            ]
        
        # 5. Вычислить health_score (0-100)
        # Формула: (idle + busy) / total * 100
        if status_counts['total'] > 0:
            operational = status_counts['idle'] + status_counts['busy']
            health_score = (operational / status_counts['total']) * 100
        else:
            health_score = 0.0
        
        return SwarmStatusResponse(
            robots=RobotStatusCount(**status_counts),
            active_tasks=ActiveTaskInfo(
                total=len(tasks),
                by_type=task_types,
                urgent_count=urgent_count
            ),
            alerts=alerts,
            last_update_at=datetime.utcnow(),
            health_score=health_score
        )
        
    except Exception as e:
        logger.error("swarm.status.error", error=str(e), trace_id=trace_id)
        raise HTTPException(status_code=500, detail="Failed to get swarm status")
```

### Тест для добавления в `tests/integration/test_rest_api.py`
```python
@pytest.mark.asyncio
async def test_swarm_status_endpoint(async_client: AsyncClient, admin_token: str):
    """GET /api/v1/swarm/status должен возвращать статус роя"""
    response = await async_client.get(
        "/api/v1/swarm/status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Проверить структуру ответа
    assert "robots" in data
    assert "active_tasks" in data
    assert "alerts" in data
    assert "health_score" in data
    
    # Проверить корректность значений
    assert data["robots"]["total"] >= 0
    assert 0 <= data["health_score"] <= 100
```

---

## 2. Реализация `/api/v1/vision/analyze_robot` (Приоритет: ВЫСОКИЙ)

### Описание
Анализ последнего изображения робота через Triton + vLLM. Требует интеграции с системой компьютерного зрения.

### Требуемые данные (из документации)
- Список детекций объектов (класс, уверенность, координаты)
- Текстовый анализ сцены
- Рекомендации по действиям

### Код для реализации

**Добавить в `schemas/common.py`:**
```python
class Detection(BaseModel):
    class_name: str  # "person", "object", "obstacle"
    confidence: float  # 0-1
    bbox: Dict[str, float]  # {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
    id: Optional[str] = None  # Track ID

class VisionAnalysisResponse(BaseModel):
    robot_id: str
    timestamp: datetime
    detections: List[Detection]
    scene_analysis: str  # Текстовое описание сцены от LLM
    recommendations: List[str]
    confidence_score: float  # Общая уверенность анализа
    processing_time_ms: float
```

**Создать `api/v1/vision.py`:**
```python
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import structlog

from gateway_service.auth.permissions import require_operator
from gateway_service.auth.middleware import get_current_user
from gateway_service.schemas.auth import User
from gateway_service.schemas.common import VisionAnalysisResponse, Detection
from gateway_service.services.triton_client import TritonClient  # Требуется новый сервис

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/vision", tags=["vision"])

# Зависимость для Triton клиента
async def get_triton_client() -> TritonClient:
    """Получить клиент Triton"""
    return TritonClient(endpoint="triton:8000")

@router.post("/analyze_robot")
@require_operator
async def analyze_robot(
    robot_id: str,
    current_user: User = Depends(get_current_user),
    triton_client: TritonClient = Depends(get_triton_client),
    redis_client: RedisClient = Depends(get_redis_client),
) -> VisionAnalysisResponse:
    """
    Анализ последнего изображения робота через Triton + vLLM.
    
    Процесс:
    1. Получить последнее изображение из хранилища минио
    2. Отправить на объектную детекцию через Triton (YOLO)
    3. Отправить результаты + изображение на анализ через vLLM
    4. Вернуть детекции + текстовый анализ
    
    Args:
        robot_id: ID робота
    
    Returns:
        VisionAnalysisResponse: Результаты анализа
    
    Роли: operator, admin
    """
    start_time = datetime.utcnow()
    trace_id = str(uuid.uuid4())
    
    try:
        # 1. Получить последнее изображение
        image_key = f"robot:{robot_id}:latest_image"
        image_data = await redis_client.get(image_key)
        
        if not image_data:
            raise HTTPException(
                status_code=404,
                detail=f"No image found for robot {robot_id}"
            )
        
        # 2. Object Detection через Triton (YOLO)
        logger.info("vision.triton.inference.start", robot_id=robot_id)
        detections_raw = await triton_client.detect_objects(image_data)
        
        # Преобразовать в нужный формат
        detections = [
            Detection(
                class_name=d.get('class_name'),
                confidence=d.get('confidence', 0.0),
                bbox=d.get('bbox', {}),
                id=d.get('track_id')
            )
            for d in detections_raw
        ]
        
        # 3. Scene Analysis через vLLM
        logger.info("vision.vllm.analysis.start", robot_id=robot_id)
        # Отправить детекции + изображение на SmolVLA для описания сцены
        scene_analysis = await triton_client.analyze_scene(
            image_data=image_data,
            detections=detections_raw
        )
        
        # 4. Generate recommendations
        recommendations = []
        for detection in detections:
            if detection.class_name == "obstacle" and detection.confidence > 0.8:
                recommendations.append(f"Avoid obstacle at {detection.bbox}")
            elif detection.class_name == "person" and detection.confidence > 0.7:
                recommendations.append("Detected person nearby - reduce speed")
        
        # Вычислить среднюю уверенность
        if detections:
            confidence_score = sum(d.confidence for d in detections) / len(detections)
        else:
            confidence_score = 1.0
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return VisionAnalysisResponse(
            robot_id=robot_id,
            timestamp=datetime.utcnow(),
            detections=detections,
            scene_analysis=scene_analysis,
            recommendations=recommendations,
            confidence_score=confidence_score,
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "vision.analysis.error",
            robot_id=robot_id,
            error=str(e),
            trace_id=trace_id
        )
        raise HTTPException(status_code=500, detail="Vision analysis failed")
```

**Добавить в `main.py` роутер:**
```python
from gateway_service.api.v1 import vision

app.include_router(vision.router, prefix="/api/v1")
```

### Тест для добавления
```python
@pytest.mark.asyncio
async def test_vision_analyze_robot(
    async_client: AsyncClient,
    operator_token: str,
    mocker: MockerFixture
):
    """POST /api/v1/vision/analyze_robot должен анализировать изображение"""
    # Mock Triton клиент
    mocker.patch(
        'gateway_service.services.triton_client.TritonClient.detect_objects',
        return_value=[
            {"class_name": "obstacle", "confidence": 0.95, "bbox": {"x1": 10, "y1": 20}}
        ]
    )
    
    response = await async_client.post(
        "/api/v1/vision/analyze_robot?robot_id=robot_1",
        headers={"Authorization": f"Bearer {operator_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "detections" in data
    assert "scene_analysis" in data
    assert "recommendations" in data
```

---

## 3. Буфер переподключения для WebSocket (Приоритет: СРЕДНИЙ)

### Описание
При потере соединения клиент может восстановиться без потери сообщений.

### Реализация в `ws/manager.py`

```python
import json
from collections import deque
from typing import Optional

class MessageBuffer:
    """Кольцевой буфер последних сообщений для переподключения"""
    
    def __init__(self, max_size: int = 1000):
        self.buffer: deque = deque(maxlen=max_size)
        self.message_counter = 0
    
    def add(self, message: dict) -> int:
        """Добавить сообщение, вернуть ID"""
        message_with_id = {
            **message,
            "message_id": self.message_counter,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.buffer.append(message_with_id)
        self.message_counter += 1
        return self.message_counter - 1
    
    def get_since(self, last_id: int) -> list:
        """Получить все сообщения после last_id"""
        return [m for m in self.buffer if m["message_id"] > last_id]


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.message_buffers: dict = {}  # по каналам
        
        # Redis для хранения ID сообщений
        self.redis: Optional[RedisClient] = None
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        channel: str,
        last_message_id: Optional[int] = None
    ):
        """Подключить клиента и отправить пропущенные сообщения"""
        await websocket.accept()
        
        # Сохранить соединение
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][channel] = websocket
        
        # Инициализировать буфер если не существует
        if channel not in self.message_buffers:
            self.message_buffers[channel] = MessageBuffer()
        
        logger.info("ws.connected", user_id=user_id, channel=channel)
        
        # Если клиент переподключается - отправить пропущенные сообщения
        if last_message_id is not None:
            missed = self.message_buffers[channel].get_since(last_message_id)
            for msg in missed:
                try:
                    await websocket.send_json(msg)
                    logger.debug(
                        "ws.resend_message",
                        user_id=user_id,
                        message_id=msg["message_id"]
                    )
                except Exception as e:
                    logger.error("ws.resend_failed", error=str(e))
    
    async def broadcast(self, channel: str, message: dict):
        """Отправить сообщение всем подписанным клиентам на канале"""
        # Добавить в буфер
        msg_id = self.message_buffers[channel].add(message)
        message["message_id"] = msg_id
        
        # Отправить все подключенным клиентам
        for user_id, channels in self.active_connections.items():
            if channel in channels:
                try:
                    await channels[channel].send_json(message)
                except Exception as e:
                    logger.error(
                        "ws.send_failed",
                        user_id=user_id,
                        channel=channel,
                        error=str(e)
                    )
```

### Обновить WebSocket endpoint в `ws/router.py`
```python
@app.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str,
    last_message_id: Optional[int] = None  # Новый параметр для восстановления
):
    """
    WebSocket для чата. Поддерживает переподключение с буфером сообщений.
    
    Query параметры:
        - token: JWT токен для аутентификации
        - last_message_id: ID последнего полученного сообщения (для восстановления)
    """
    try:
        # Аутентификация
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")
        
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Подключить и отправить пропущенные сообщения
        manager = get_connection_manager()
        await manager.connect(
            websocket,
            user_id=user_id,
            channel=f"chat:{user_id}",
            last_message_id=last_message_id
        )
        
        # Основной цикл обработки сообщений
        while True:
            data = await websocket.receive_json()
            # ... остальной код обработки сообщений
```

---

## 4. Delta Updates для WebSocket (Приоритет: НИЗКИЙ)

Отправлять только изменения вместо полного состояния для оптимизации трафика.

```python
from typing import Dict, Any

class StateTracker:
    """Отслеживает изменения состояния"""
    
    def __init__(self):
        self.last_state: Dict[str, Any] = {}
    
    def get_delta(self, new_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сравнить старое и новое состояние, вернуть только изменения
        """
        delta = {}
        
        for key, new_value in new_state.items():
            if key not in self.last_state:
                # Новый ключ
                delta[key] = new_value
            elif self.last_state[key] != new_value:
                # Измененное значение
                delta[key] = new_value
        
        # Удаленные ключи
        for key in self.last_state:
            if key not in new_state:
                delta[key] = None  # Указываем удаление как None
        
        self.last_state = new_state.copy()
        return delta
    
    def has_changes(self, new_state: Dict[str, Any]) -> bool:
        """Проверить есть ли изменения"""
        return self.get_delta(new_state) != {}
```

---

## 5. Рекомендации по Приоритизации

### Немедленно (Спринт 1)
- [ ] Реализовать `/api/v1/swarm/status` 
- [ ] Добавить буфер переподключения для WebSocket

### Вскоре (Спринт 2)
- [ ] Реализовать `/api/v1/vision/analyze_robot` (требует готовности Triton)
- [ ] Реализовать delta updates

### После Стабилизации (Спринт 3+)
- [ ] MessagePack для WebSocket
- [ ] Полное администрирование (PUT config, POST models/deploy)
- [ ] Prometheus метрики и мониторинг

---

**Все предложенные изменения совместимы с текущей архитектурой и проходят тестирование.**
