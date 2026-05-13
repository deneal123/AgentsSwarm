import React from 'react';
import { Box, HStack, Icon, Text, useToast } from '@chakra-ui/react';
import { FiAlertCircle, FiAlertTriangle, FiCheckCircle, FiInfo, FiX } from 'react-icons/fi';

const STATUS_CONFIG = {
  success: {
    icon: FiCheckCircle,
    color: '#4ade80',
    border: 'rgba(74,222,128,0.3)',
    bg: 'rgba(74,222,128,0.08)',
  },
  error: {
    icon: FiAlertCircle,
    color: '#f87171',
    border: 'rgba(239,68,68,0.35)',
    bg: 'rgba(239,68,68,0.08)',
  },
  warning: {
    icon: FiAlertTriangle,
    color: '#fbbf24',
    border: 'rgba(251,191,36,0.3)',
    bg: 'rgba(251,191,36,0.07)',
  },
  info: {
    icon: FiInfo,
    color: '#60a5fa',
    border: 'rgba(96,165,250,0.3)',
    bg: 'rgba(96,165,250,0.07)',
  },
};

function AppToast({ title, description, status = 'info', onClose }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.info;
  return (
    <Box
      display="flex"
      alignItems="flex-start"
      gap={3}
      px={4}
      py={3}
      borderRadius="14px"
      bg="rgba(10,10,10,0.97)"
      border="1px solid"
      borderColor={cfg.border}
      boxShadow={`0 8px 32px rgba(0,0,0,0.55), 0 0 0 1px ${cfg.border}`}
      backdropFilter="blur(16px)"
      minW="280px"
      maxW="360px"
      position="relative"
      sx={{ background: `linear-gradient(135deg, rgba(10,10,10,0.97) 0%, ${cfg.bg} 100%)` }}
    >
      <Box pt="1px" flexShrink={0}>
        <Icon as={cfg.icon} boxSize="16px" color={cfg.color} />
      </Box>
      <Box flex="1" minW={0}>
        {title && (
          <Text fontSize="13px" fontWeight="600" color="rgba(255,255,255,0.92)" lineHeight="1.4">
            {title}
          </Text>
        )}
        {description && (
          <Text fontSize="12px" color="rgba(255,255,255,0.55)" mt={title ? 0.5 : 0} lineHeight="1.5">
            {description}
          </Text>
        )}
      </Box>
      {onClose && (
        <Box
          as="button"
          onClick={onClose}
          flexShrink={0}
          color="rgba(255,255,255,0.35)"
          _hover={{ color: 'rgba(255,255,255,0.7)' }}
          pt="2px"
          cursor="pointer"
        >
          <Icon as={FiX} boxSize="13px" />
        </Box>
      )}
    </Box>
  );
}

export function useAppToast() {
  const toast = useToast();

  return React.useCallback((options = {}) => {
    const { title, description, status = 'info', duration = 3500, isClosable = true, ...rest } = options;
    toast({
      duration,
      isClosable,
      position: 'bottom-right',
      ...rest,
      render: ({ onClose }) => (
        <AppToast
          title={title}
          description={description}
          status={status}
          onClose={isClosable ? onClose : undefined}
        />
      ),
    });
  }, [toast]);
}
