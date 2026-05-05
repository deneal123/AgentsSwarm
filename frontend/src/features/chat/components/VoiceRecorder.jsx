import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Icon,
  Button,
  Progress,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  useDisclosure,
  useToast,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb
} from '@chakra-ui/react';
import {
  FiMic,
  FiSquare,
  FiPlay,
  FiPause,
  FiTrash2,
  FiCheck,
  FiX
} from 'react-icons/fi';
import { MotionBox } from '@ui/motionPrimitives';
import { colors, borderRadius } from '@theme/tokens';

/**
 * VoiceRecorder - Компонент для записи голосовых сообщений
 *
 * Функциональность:
 * - Запись через Web Audio API
 * - Визуализация волны в реальном времени
 * - Управление записью (старт/стоп/пауза)
 * - Таймер с лимитом времени
 * - Playback с контролами
 */
function VoiceRecorder({ onRecordingComplete, maxDuration = 300 }) { // 5 минут max
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [waveformData, setWaveformData] = useState([]);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const analyserRef = useRef(null);
  const animationRef = useRef(null);
  const durationIntervalRef = useRef(null);

  const toast = useToast();

  // Инициализация Web Audio API
  const initAudioContext = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);

      analyserRef.current = analyser;

      return true;
    } catch (error) {
      console.error('Failed to initialize audio:', error);
      toast({
        title: 'Ошибка микрофона',
        description: 'Не удалось получить доступ к микрофону. Проверьте разрешения.',
        status: 'error',
        duration: 5000,
      });
      return false;
    }
  }, [toast]);

  // Визуализация аудио волны
  const visualizeAudio = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      analyser.getByteFrequencyData(dataArray);

      // Преобразуем частоты в waveform data
      const waveform = Array.from(dataArray.slice(0, 32)).map(value =>
        Math.max(0.1, value / 255) // Минимум 0.1 для видимости
      );

      setWaveformData(waveform);
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();
  }, []);

  // Старт записи
  const startRecording = useCallback(async () => {
    const initialized = await initAudioContext();
    if (!initialized) return;

    try {
      const mediaRecorder = new MediaRecorder(streamRef.current, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
      };

      mediaRecorder.start(100); // Записывать chunks каждые 100ms
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);

      // Таймер
      durationIntervalRef.current = setInterval(() => {
        setDuration(prev => {
          const newDuration = prev + 1;
          if (newDuration >= maxDuration) {
            stopRecording();
            return maxDuration;
          }
          return newDuration;
        });
      }, 1000);

      // Визуализация
      visualizeAudio();

      toast({
        title: 'Запись начата',
        description: 'Говорите в микрофон',
        status: 'info',
        duration: 2000,
      });

    } catch (error) {
      console.error('Failed to start recording:', error);
      toast({
        title: 'Ошибка записи',
        description: 'Не удалось начать запись',
        status: 'error',
        duration: 3000,
      });
    }
  }, [initAudioContext, visualizeAudio, maxDuration, toast]);

  // Пауза записи
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      if (isPaused) {
        mediaRecorderRef.current.resume();
        setIsPaused(false);
      } else {
        mediaRecorderRef.current.pause();
        setIsPaused(true);
      }
    }
  }, [isRecording, isPaused]);

  // Стоп записи
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);

      // Очистка
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    }
  }, [isRecording]);

  // Отмена записи
  const cancelRecording = useCallback(() => {
    stopRecording();
    setAudioBlob(null);
    setWaveformData([]);
    setDuration(0);
  }, [stopRecording]);

  // Отправка записи
  const sendRecording = useCallback(() => {
    if (audioBlob && onRecordingComplete) {
      onRecordingComplete(audioBlob, duration);
      setAudioBlob(null);
      setWaveformData([]);
      setDuration(0);
    }
  }, [audioBlob, duration, onRecordingComplete]);

  // Форматирование времени
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Очистка при размонтировании
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const progressPercent = (duration / maxDuration) * 100;
  const canSend = audioBlob && duration > 1; // Минимум 1 секунда

  return (
    <Box
      p={4}
      borderRadius={borderRadius.lg}
      bg="rgba(255,255,255,0.05)"
      border="1px solid rgba(255,255,255,0.1)"
      backdropFilter="blur(10px)"
    >
      <VStack spacing={4}>
        {/* Waveform visualization */}
        {isRecording && (
          <Box w="full" h="60px" position="relative">
            <HStack spacing={0.5} h="full" align="end" justify="center">
              {waveformData.map((amplitude, index) => (
                <MotionBox
                  key={index}
                  w="3px"
                  bg={isPaused ? colors.warning : colors.brand.primary}
                  borderRadius="1px"
                  initial={{ height: '2px' }}
                  animate={{
                    height: isPaused ? '2px' : `${Math.max(2, amplitude * 60)}px`
                  }}
                  transition={{ duration: 0.1 }}
                  opacity={isPaused ? 0.5 : 1}
                />
              ))}
            </HStack>

            {/* Recording indicator */}
            <Box
              position="absolute"
              top={2}
              right={2}
              w={3}
              h={3}
              borderRadius="full"
              bg={isPaused ? colors.warning : colors.error}
              animation={isRecording && !isPaused ? 'pulse 1s infinite' : 'none'}
            />
          </Box>
        )}

        {/* Recording controls */}
        <HStack spacing={3}>
          {!isRecording ? (
            <Button
              leftIcon={<FiMic />}
              colorScheme="red"
              size="sm"
              onClick={startRecording}
              _hover={{ transform: 'scale(1.05)' }}
              transition="all 0.2s"
            >
              Начать запись
            </Button>
          ) : (
            <>
              <Button
                leftIcon={isPaused ? <FiPlay /> : <FiPause />}
                colorScheme="orange"
                variant="outline"
                size="sm"
                onClick={pauseRecording}
              >
                {isPaused ? 'Продолжить' : 'Пауза'}
              </Button>

              <Button
                leftIcon={<FiSquare />}
                colorScheme="red"
                size="sm"
                onClick={stopRecording}
              >
                Стоп
              </Button>

              <Button
                leftIcon={<FiX />}
                variant="ghost"
                size="sm"
                onClick={cancelRecording}
                color={colors.text.secondary}
              >
                Отмена
              </Button>
            </>
          )}
        </HStack>

        {/* Recording info */}
        {isRecording && (
          <VStack spacing={2}>
            <HStack spacing={4}>
              <Text fontSize="sm" color={colors.text.secondary}>
                {formatTime(duration)}
              </Text>
              <Text fontSize="sm" color={colors.text.tertiary}>
                макс {formatTime(maxDuration)}
              </Text>
            </HStack>

            <Progress
              value={progressPercent}
              size="sm"
              colorScheme={progressPercent > 90 ? 'red' : 'blue'}
              w="full"
              maxW="200px"
              borderRadius="full"
              bg="rgba(255,255,255,0.1)"
            />
          </VStack>
        )}

        {/* Recorded audio preview */}
        {audioBlob && !isRecording && (
          <VStack spacing={3}>
            <HStack spacing={2}>
              <Icon as={FiMic} color={colors.success} />
              <Text fontSize="sm" color={colors.success}>
                Запись готова ({formatTime(duration)})
              </Text>
            </HStack>

            <HStack spacing={2}>
              <Button
                leftIcon={<FiCheck />}
                colorScheme="green"
                size="sm"
                onClick={sendRecording}
                isDisabled={!canSend}
              >
                Отправить
              </Button>

              <Button
                leftIcon={<FiTrash2 />}
                variant="ghost"
                size="sm"
                onClick={cancelRecording}
                color={colors.text.secondary}
              >
                Удалить
              </Button>
            </HStack>
          </VStack>
        )}
      </VStack>
    </Box>
  );
}

// Hook для использования VoiceRecorder в модальном окне
export function useVoiceRecorder(onRecordingComplete) {
  const { isOpen, onOpen, onClose } = useDisclosure();

  const handleRecordingComplete = (blob, duration) => {
    onRecordingComplete(blob, duration);
    onClose();
  };

  return {
    isOpen,
    onOpen,
    onClose,
    VoiceRecorderModal: (
      <Modal isOpen={isOpen} onClose={onClose} size="md" isCentered>
        <ModalOverlay backdropFilter="blur(8px)" />
        <ModalContent
          bg="rgba(5,5,5,0.95)"
          backdropFilter="blur(20px)"
          border="1px solid rgba(255,255,255,0.1)"
          borderRadius="xl"
        >
          <ModalBody p={6}>
            <VoiceRecorder
              onRecordingComplete={handleRecordingComplete}
            />
          </ModalBody>
        </ModalContent>
      </Modal>
    )
  };
}

export default VoiceRecorder;
