import React from "react";
import {
  Button,
  HStack,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Text,
  VStack,
} from "@chakra-ui/react";
import { FiCheck, FiChevronDown } from "react-icons/fi";
import { colors, borderRadius, typography } from "@theme/tokens";
import { useResponsive } from "@hooks/useResponsive";
import { CHAT_THEME } from "../constants/theme";
import { AUTO_MODE_LABEL, normalizeModelList, resolveModelTriggerLabel } from "../utils/modelSelector";

function ModelSelector({ selectedModel, availableModels, onChange }) {
  const { isMobile } = useResponsive();
  const isAuto = !selectedModel;
  const label = resolveModelTriggerLabel(selectedModel);
  const models = normalizeModelList(availableModels);

  return (
    <Menu matchWidth>
      <MenuButton
        as={Button}
        rightIcon={<FiChevronDown />}
        w={isMobile ? "100%" : "320px"}
        minW={0}
        size="sm"
        justifyContent="space-between"
        borderRadius={borderRadius.md}
        borderWidth="1px"
        borderColor={isAuto ? CHAT_THEME.panelBorderStrong : CHAT_THEME.inputBorderFocus}
        bg={isAuto ? CHAT_THEME.panelHover : CHAT_THEME.accentSoft}
        color={isAuto ? colors.text.primary : "#fecaca"}
        fontFamily={typography.fontFamily.primary}
        fontSize="13px"
        fontWeight="600"
        px={3}
        _hover={{ bg: isAuto ? CHAT_THEME.panelActive : "rgba(239,68,68,0.22)" }}
        _active={{ bg: isAuto ? CHAT_THEME.panelActive : "rgba(239,68,68,0.22)" }}
      >
        <HStack flex="1" justify="space-between" minW={0}>
          <Text noOfLines={1}>{label}</Text>
        </HStack>
      </MenuButton>
      <MenuList
        bg={CHAT_THEME.panelBg}
        border="1px solid"
        borderColor={CHAT_THEME.panelBorderStrong}
        borderRadius={borderRadius.md}
        py={1}
        maxH="320px"
        overflowY="auto"
      >
        <MenuItem onClick={() => onChange("")} bg="transparent" _hover={{ bg: CHAT_THEME.panelHover }}>
          <HStack justify="space-between" w="100%">
            <Text>{AUTO_MODE_LABEL}</Text>
            {isAuto && <FiCheck />}
          </HStack>
        </MenuItem>
        {models.map((modelId) => (
          <MenuItem
            key={modelId}
            onClick={() => onChange(modelId)}
            bg={selectedModel === modelId ? CHAT_THEME.panelHover : "transparent"}
            color={selectedModel === modelId ? "#fecaca" : colors.text.primary}
            _hover={{ bg: CHAT_THEME.panelHover }}
          >
            <VStack align="stretch" spacing={0} w="100%">
              <HStack justify="space-between" w="100%">
                <Text>{modelId}</Text>
                {selectedModel === modelId && <FiCheck />}
              </HStack>
            </VStack>
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
}

export default ModelSelector;
