import React from 'react';
import {
  Button,
  HStack,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
} from '@chakra-ui/react';
import { FiChevronDown } from 'react-icons/fi';
import { CHAT_FONT_FAMILY, CHAT_THEME } from '../constants/theme';

function ModelSelector({ selectedModel, availableModels, onChange }) {
  const isAuto = !selectedModel;
  const label = isAuto ? 'Автоматический режим (Auto)' : selectedModel;

  return (
    <Menu matchWidth>
      <MenuButton
        as={Button}
        rightIcon={<FiChevronDown />}
        w="280px"
        size="sm"
        justifyContent="space-between"
        borderRadius="12px"
        borderWidth="1px"
        borderColor={isAuto ? CHAT_THEME.panelBorderStrong : 'rgba(239,68,68,0.45)'}
        bg={isAuto ? CHAT_THEME.panelHover : CHAT_THEME.accentSoft}
        color={isAuto ? CHAT_THEME.textPrimary : '#fca5a5'}
        fontFamily={CHAT_FONT_FAMILY}
        fontSize="13px"
        fontWeight="600"
        px={3}
        _hover={{ bg: isAuto ? CHAT_THEME.panelActive : 'rgba(239,68,68,0.22)' }}
        _active={{ bg: isAuto ? CHAT_THEME.panelActive : 'rgba(239,68,68,0.22)' }}
      >
        <HStack flex="1" justify="space-between" minW={0}>
          <Text noOfLines={1}>{label}</Text>
        </HStack>
      </MenuButton>
      <MenuList
        bg={CHAT_THEME.panelBg}
        border="1px solid"
        borderColor={CHAT_THEME.panelBorderStrong}
        borderRadius="12px"
        py={1}
        maxH="320px"
        overflowY="auto"
        sx={{
          '&::-webkit-scrollbar': { width: '8px' },
          '&::-webkit-scrollbar-thumb': { background: 'rgba(255,255,255,0.2)', borderRadius: '999px' },
        }}
      >
        <MenuItem onClick={() => onChange('')} bg="transparent" _hover={{ bg: CHAT_THEME.panelHover }}>
          Автоматический режим (Auto)
        </MenuItem>
        {availableModels.map((modelId) => (
          <MenuItem
            key={modelId}
            onClick={() => onChange(modelId)}
            bg={selectedModel === modelId ? CHAT_THEME.panelHover : 'transparent'}
            color={selectedModel === modelId ? '#fca5a5' : CHAT_THEME.textPrimary}
            _hover={{ bg: CHAT_THEME.panelHover }}
          >
            {modelId}
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
}

export default ModelSelector;
