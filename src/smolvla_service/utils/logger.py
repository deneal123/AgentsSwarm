"""Logging utilities for SmolVLA optimization framework."""

import logging
import os
import sys
from datetime import datetime


def setup_logger(name='smolvla', log_file=None, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class TrainingLogger:
    def __init__(self, logger, log_every=10):
        self.logger = logger
        self.log_every = log_every
        self.epoch_metrics = []
    
    def log_epoch(self, epoch, total_epochs, metrics):
        msg = f"Epoch {epoch}/{total_epochs}"
        for key, value in metrics.items():
            if isinstance(value, float):
                msg += f" | {key}: {value:.4f}"
            else:
                msg += f" | {key}: {value}"
        self.logger.info(msg)
        self.epoch_metrics.append(metrics)
    
    def log_batch(self, epoch, batch, total_batches, loss):
        if batch % self.log_every == 0:
            self.logger.debug(f"Epoch {epoch} | Batch {batch}/{total_batches} | Loss: {loss:.4f}")

