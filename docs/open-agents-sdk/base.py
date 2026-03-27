import threading
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class MetaModule(ABC):
    """Базовый класс для модулей агентов, выполняемых в отдельном потоке с async-циклом.

    Улучшения:
    - использует логгер вместо печати
    - помечает поток как daemon
    - защищает старт/стоп от повторных вызовов
    - оставляет async_stop как опциональный hook для подклассов
    """
    
    def __init__(self):
        # Управление состоянием потока
        self._thread = threading.Thread(target=self._thread_target, daemon=True)
        self._running = threading.Event()
        self._paused = threading.Event()
        self._data_ready = threading.Condition()
        self._lock = threading.Lock()
        
        # Настройка начального состояния
        self._paused.set()  # Начинаем в паузе
        self._running.clear()

    def _thread_target(self):
        """Цикл, который запускает async метод run_cycle в event loop внутри потока."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._running.set()

        try:
            while self._running.is_set():
                with self._data_ready:
                    # Ждём пока не придёт сигнал продолжения или пока не остановят
                    self._data_ready.wait_for(lambda: (not self._paused.is_set()) or (not self._running.is_set()))

                if not self._running.is_set():
                    break

                try:
                    loop.run_until_complete(self.run_cycle())
                except Exception as e:
                    self.handle_error(e)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    def start(self):
        """Запустить поток и снять паузу."""
        with self._lock:
            if not self._thread.is_alive():
                self._thread = threading.Thread(target=self._thread_target, daemon=True)
                self._thread.start()
            self.resume()

    def stop(self):
        """Полная остановка потока и hook для асинхронной остановки."""
        with self._lock:
            if not self._running.is_set():
                return
            self._running.clear()
            self.resume()  # Разблокировать поток если в паузе

            # Run async stop implementation if needed
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.async_stop())
                loop.close()
            except Exception:
                logger.exception("Error while running async_stop hook")

            self._thread.join(timeout=5)

    async def async_stop(self):
        """Асинхронный метод остановки (переопределяется при необходимости)"""
        # Optional to implement in subclasses
        return None

    def pause(self):
        """Временная приостановка обработки"""
        self._paused.set()

    def resume(self):
        """Возобновление обработки"""
        with self._data_ready:
            self._paused.clear()
            self._data_ready.notify_all()

    def wait_until_done(self, timeout: Optional[float] = None):
        """Ожидание завершения текущей операции (полезно в тестах)."""
        start = time.time()
        while self.is_processing():
            if timeout and (time.time() - start) > timeout:
                raise TimeoutError("Operation timeout")
            time.sleep(0.1)

    @abstractmethod
    async def run_cycle(self):
        """Основной цикл обработки данных (реализация в подклассах)"""
        pass

    def handle_error(self, error: Exception):
        """Обработка ошибок в потоке"""
        logger.exception("Error in %s: %s", self.__class__.__name__, error)

    def is_processing(self) -> bool:
        """Проверка активности обработки данных"""
        return (not self._paused.is_set()) and self._running.is_set()

    def signal_data_ready(self):
        """Сигнализировать о наличии новых данных"""
        with self._data_ready:
            self._data_ready.notify_all()